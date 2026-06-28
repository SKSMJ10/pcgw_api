from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth import verify_api_key
from app.api.routes import router
from app.schemas.models import GameDocument


class _FakeGameDocument:
    def __init__(self):
        self.deleted = False

    async def delete(self):
        self.deleted = True


def _make_client():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[verify_api_key] = lambda: None
    return TestClient(app)


def test_delete_game_document(monkeypatch):
    fake_game = _FakeGameDocument()

    async def fake_get(page_id: int):
        assert page_id == 123
        return fake_game

    monkeypatch.setattr(GameDocument, "get", fake_get)

    client = _make_client()
    response = client.delete("/api/game/123")

    assert response.status_code == 204
    assert fake_game.deleted is True


def test_delete_game_document_not_found(monkeypatch):
    async def fake_get(page_id: int):
        assert page_id == 404
        return None

    monkeypatch.setattr(GameDocument, "get", fake_get)

    client = _make_client()
    response = client.delete("/api/game/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "Game not found"}
