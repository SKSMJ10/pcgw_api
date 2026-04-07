import requests
from app.scraper.game import Game

class PCGamingWiki:
    def __init__(self):
        self.session = requests.Session()

    def get_game(self, pid: int):
        return Game(pid, self.session)