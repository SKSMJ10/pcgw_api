import httpx
from app.scraper.game import Game


class PCGamingWiki:
    BASE_URL = "https://www.pcgamingwiki.com/"
    API = "https://www.pcgamingwiki.com/w/api.php"

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    def get_game(self, pid: int):
        return Game(pid, self.client, BASE_URL=self.BASE_URL, API=self.API)

    async def search_game(self, query: str):
        params = {
            "action": "cargoquery",
            "format": "json",
            "tables": "Infobox_game",
            "fields": "_pageName=name,_pageID=page_id",
            "where": f"_pageName LIKE '%{query}%'",
        }

        response = await self.client.get(self.API, params=params)
        cleaned_response = {"result": []}
        for data in response.json().get('cargoquery'):
            cleaned_response["result"].append(data["title"])
        return cleaned_response
