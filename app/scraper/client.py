import httpx
from app.scraper.game import Game

class PCGamingWiki:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    def get_game(self, pid: int):
        return Game(pid, self.client)