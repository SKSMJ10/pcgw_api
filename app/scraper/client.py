import httpx
import logging
from app.scraper.game import Game
from app.scraper.utils import limiter, is_transient
from app.core.config import settings
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

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
            raise httpx.HTTPStatusError(
                message=f"Authentication Failed: {result['message']}",
                request=login_res.request,
                response=login_res,
            )

    def get_game(self, pid: int):
        return Game(pid, self.client, BASE_URL=self.BASE_URL, API=self.API)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(1, min=2, max=10),
        retry=retry_if_exception(is_transient),
        reraise=True,
    )
    async def search_game(self, query: str):
        final_query = query.replace("'", "\\'")

        params = {
            "action": "cargoquery",
            "format": "json",
            "tables": "Game",
            "fields": "Game._pageName=name,Game._pageID=page_id",
            "where": f"Game._pageName LIKE '%{final_query}%'",
            "limit": "max",
        }

        if not limiter.has_capacity():
            logger.warning(
                f"Rate limit reached. Pausing search request for '{query}'..."
            )
        async with limiter:
            response = await self.client.get(self.API, params=params)
            response.raise_for_status()

        cleaned_response = {"result": []}
        for data in response.json().get("cargoquery", []):
            cleaned_response["result"].append(data["title"])
        return cleaned_response
