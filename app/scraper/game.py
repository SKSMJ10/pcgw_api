import re
import httpx
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
from app.scraper.utils import sluggify


class Game:
    def __init__(self, pid: int, session: httpx.AsyncClient, BASE_URL: str, API: str):
        self.BASE_URL = BASE_URL
        self.API = API
        self.pid = pid
        self.session = session
        self._title = None

        self._soup = None
        self._info_loaded = None
        self._page_loaded = False

    async def download_page(self):
        if self._page_loaded:
            return

        params = {
            "action": "parse",
            "format": "json",
            "pageid": f"{self.pid}",
            "prop": "text",
        }
        response = await self.session.get(self.API, params=params)
        response.raise_for_status()

        response_data = response.json().get("parse", {})
        if not response_data:
            raise ValueError(f"No parse data found for {self.pid}.")

        content, self._title = response_data["text"]["*"], response_data["title"]
        self._soup = BeautifulSoup(content, "html.parser")
        self._page_loaded = True

    @property
    def soup(self) -> BeautifulSoup:
        if not self._page_loaded:
            raise RuntimeError(
                "Page not downloaded. You must 'await download_page()' first."
            )
        return self._soup

    @property
    def title(self) -> str:
        if not self._page_loaded:
            raise RuntimeError(
                "Page not downloaded. You must 'await download_page()' first."
            )
        return self._title

    def _clean_tags(self, td: Tag, sep: str = " ", strip: bool = True) -> str:
        for sup in td.find_all("sup"):
            sup.decompose()

        for a in td.find_all("a"):
            text = a.get_text(strip=True)
            href = a.get("href", "")
            if href[0] == "/":
                full_url = urljoin(self.BASE_URL, href)
            elif href[0] == "#":
                full_url = urljoin(
                    self.BASE_URL, f"{self.title.replace(' ', '_')}{href}"
                )
            else:
                full_url = href

            a.replace_with(f"[{text}]({full_url})")  # Markdown syntax for hyperlink

        cleaned = td.get_text(separator=sep, strip=strip)
        return cleaned

    def game_data(self) -> dict:
        gd_data = {"Name": self.title}
        gd_content = ("Config_File_Location", "Save_Game_File_Location")

        for index, gd_table in enumerate(self.soup.select("#table-gamedata")):
            gd_rows = gd_table.find_all(["th", "td"])
            system = gd_content[index]
            cleaned = [
                self._clean_tags(data) for data in gd_rows[2:]
            ]  # we are starting from index 2 to skip content of first heading row
            gd_data[system] = list(zip(cleaned[::2], cleaned[1::2]))

        return gd_data

    def get_taxonomy(self) -> dict:
        thead = self.soup.find("th", string="Taxonomy")
        taxo_parent_row = thead.find_parent("tr")
        taxo_final_data = {}

        for row in taxo_parent_row.find_next_siblings("tr")[:-1]:
            taxo_row = row.find_all("td")
            cleaned = [self._clean_tags(data) for data in taxo_row]
            taxo_final_data[cleaned[0]] = cleaned[1:]

        return taxo_final_data

    def clean_cargo_query(self, response: dict) -> dict:
        cleaned = response["cargoquery"][0]["title"]
        if not cleaned:
            return {}

        for key, value in cleaned.items():
            if not value or key == "name":
                continue
            cleaned_value = (
                re.sub(r"[^:,]+:", "", value.replace(";", ",")).strip().split(",")
            )
            cleaned[key] = cleaned_value

        platforms = cleaned.get("Available on", [])
        release_dates = cleaned.get("released", [])

        cleaned["released"] = dict(zip(platforms, release_dates))

        del cleaned["released__precision"], cleaned["Available on"]
        return cleaned

    async def info(self) -> dict:
        if self._info_loaded:
            return self._info_loaded

        params = {
            "action": "cargoquery",
            "format": "json",
            "tables": "Infobox_game",
            "fields": "Infobox_game._pageName=name,Infobox_game.Developers=developers,Infobox_game.Engines=engines,Infobox_game.Available_on,Infobox_game.Released=released,Infobox_game.Publishers=publishers",
            "where": f'Infobox_game._pageID="{self.pid}"',
        }

        response = await self.session.get(self.API, params=params)
        result = self.clean_cargo_query(response.json())
        taxonomy = self.get_taxonomy()
        result["taxonomy"] = taxonomy

        self._info_loaded = result
        return self._info_loaded

    def _get_table_rows(self, tag: str, table_name: str = None, head: bool = False):
        if table_name:
            table_id = f"#table-{table_name}-{tag}"
        else:
            table_id = f"#table-{tag}"
        settings = self.soup.select(f"{table_id} > tbody > tr:not(:first-child)")

        def generate():
            for rows in settings:
                for br in rows.find_all("br"):
                    br.replace_with("\n")
                yield rows.find_all(["th", "td"])

        if head:
            headers = [
                header.get_text()
                for header in self.soup.select(f"{table_id} > tbody > tr:first-child")[
                    0
                ].find_all("th")
            ]
            return headers, generate()
        else:
            return generate()

    def _extract_table(self, tag: str, table: str = None):
        result = {"name": self.title, f"{tag}": {}}

        for row_data in self._get_table_rows(tag, table):
            row = []

            for index, data in enumerate(row_data):
                if index == 0:
                    value = data.get_text()
                elif index == 1:
                    value = data.find("div").get("title")
                else:
                    value = self._clean_tags(data, "", False)
                row.append(re.sub(r"\n", " ", value).strip())

            feature, state, notes = row

            result[f"{tag}"][sluggify(feature)] = {
                "name": feature,
                "state": state if state else "Unknown",
                "notes": notes if notes else None,
            }
        return result

    def video(self):
        return self._extract_table("video", "settings")

    def audio(self):
        return self._extract_table("audio", "settings")

    def api_middleware(self):
        api_trs = self._get_table_rows("api")
        exec_headers, api_exec_trs = self._get_table_rows("executable", "api", True)
        middleware_trs = self._get_table_rows("middleware")

        result = {"name": self.title, "api": {}, "executable": {}, "middleware": {}}

        for row_data in api_trs:
            api_row = []

            for index, data in enumerate(row_data):
                value = data.get_text()
                if not value and index == 1:
                    value = data.find("div").get("title")
                api_row.append(value.strip())

            graphics_api, support, api_notes = api_row

            result["api"][sluggify(graphics_api)] = {
                "name": graphics_api,
                "support": (support if not support.isdigit() else float(support))
                if support
                else "Unknown",
                "notes": api_notes if api_notes else None,
            }

        exec_headers = exec_headers[1:-1]
        for exec_data in api_exec_trs:
            platform, e_notes = (
                exec_data[0].get_text(strip=True),
                exec_data[-1].get_text(strip=True),
            )
            for index, data in enumerate(exec_data[1:-1]):
                support_class = data.find("div").get("class")
                if "tickcross-true" in support_class:
                    version = exec_headers[index]
                else:
                    version = None

            result["executable"][sluggify(platform)] = {
                "name": platform,
                "version": version if version else "Unknown",
                "notes": e_notes if e_notes else None,
            }

        if middleware_trs:
            for mw_data in middleware_trs:
                mw_row = []

                for index, data in enumerate(mw_data):
                    if index == 1:
                        value = self._clean_tags(data)
                    else:
                        value = data.get_text(strip=True)
                    mw_row.append(value)

                _type, mw, mw_notes = mw_row

                result["middleware"][sluggify(_type)] = {
                    "type": _type,
                    "middleware": mw,
                    "notes": mw_notes if mw_notes else None,
                }

        return result

    async def get_all(self) -> dict:
        await self.download_page()
        api_mw_data = self.api_middleware()

        return {
            "_id": self.pid,
            "name": self.title,
            "video": self.video().get("video", {}),
            "audio": self.audio().get("audio", {}),
            "info": await self.info(),
            "api": api_mw_data.get("api", {}),
            "executable": api_mw_data.get("executable", {}),
            "middleware": api_mw_data.get("middleware", {}),
        }
