import httpx
import logging
from app.scraper.game import Game
from app.scraper.utils import request_with_retries
from app.core.config import settings

logger = logging.getLogger(__name__)


class PCGamingWiki:
    BASE_URL = "https://www.pcgamingwiki.com/"
    API = "https://www.pcgamingwiki.com/w/api.php"

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def login(self):
        if not settings.pcgw_user or not settings.pcgw_pass:
            return

        token_params = {
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json",
        }
        response = await self.client.get(self.API, params=token_params)
        response.raise_for_status()
        login_token = response.json()["query"]["tokens"]["logintoken"]

        login_data = {
            "action": "login",
            "lgname": settings.pcgw_user,
            "lgpassword": settings.pcgw_pass,
            "lgtoken": login_token,
            "format": "json",
        }

        login_res = await self.client.post(self.API, data=login_data)
        login_res.raise_for_status()
        result = login_res.json()["login"]

        if result["result"] == "Success":
            logger.info("Successfully logged in to PCGamingWiki.")
        else:
            reason = result.get("reason", "Unknown error")
            logger.error(f"Login failed: {reason}")
            raise RuntimeError(f"Authentication Failed: {reason}")

    def get_game(self, pid: int):
        return Game(pid, self.client, BASE_URL=self.BASE_URL, API=self.API)

    async def search_game(self, query: str):
        params = {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "list": "search",
            "srsearch": query,
            "srlimit": "max",  # default is 10, just putting it explicitly
            "srnamespace": 0,  # default is 0 i.e. main articles
        }

        response = await request_with_retries(
            self.client, "GET", self.API, params=params
        )

        data = response.json()
        if "error" in data:
            error_info = data["error"].get("info", "Unknown Mediawiki Error.")
            raise RuntimeError(f"PCGW Search failed: {error_info}")

        cleaned_response = {"result": []}
        for item in data.get("query", {}).get("search", []):
            cleaned_response["result"].append(
                {"name": item["title"], "page_id": item["pageid"]}
            )
        return cleaned_response
