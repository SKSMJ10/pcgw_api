import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app
from app.core.config import settings
from app.api.routes import get_pcgw

# Sample data
SAMPLE_GAME_DATA = {
    "_id": 123,
    "name": "Test Game",
    "game_data": {"config": [("Windows", "Path/to/whatever")]},
    "video": {},
    "audio": {},
    "api": {},
    "executable": {},
    "middleware": {},
    "info": {
        "name": "Test Game",
        "developers": ["Test Dev"],
        "released": {"Windows": "2026-01-01"},
        "taxonomy": {"Genre": ["Action"]},
    },
}

SAMPLE_SEARCH_DATA = {"result": [{"name": "Test Game", "page_id": 123}]}


def fake_get_pcgw():
    mock_pcgw = MagicMock()
    mock_pcgw.search_game = AsyncMock(return_value=SAMPLE_SEARCH_DATA)

    mock_game = MagicMock()
    mock_game.get_all = AsyncMock(return_value=SAMPLE_GAME_DATA)
    mock_pcgw.get_game.return_value = mock_game
    return mock_pcgw


app.dependency_overrides[get_pcgw] = fake_get_pcgw


@pytest.fixture(autouse=True)
def mock_database_documents():
    with (
        patch("app.api.routes.SearchDocument") as mock_search,
        patch("app.api.routes.GameDocument") as mock_game,
    ):
        # Fake SearchDocument
        mock_search.get = AsyncMock(return_value=None)
        mock_search_instance = MagicMock()
        mock_search_instance.insert = AsyncMock()
        mock_search_instance.replace = AsyncMock()
        mock_search.return_value = mock_search_instance

        # Fake GameDocument
        mock_game.get = AsyncMock(return_value=None)
        mock_game_instance = MagicMock()
        mock_game_instance.insert = AsyncMock()
        mock_game_instance.replace = AsyncMock()
        mock_game_instance.delete = AsyncMock()
        mock_game_instance.model_dump.return_value = SAMPLE_GAME_DATA
        mock_game.return_value = mock_game_instance

        yield mock_search, mock_game


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_headers():
    return {"X-API-Key": settings.api_key}


@pytest.mark.asyncio
async def test_search_unauthorized(async_client):
    response = await async_client.get("/api/search?query=test")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_search_authorized(async_client, auth_headers):
    response = await async_client.get("/api/search?query=test", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["result"][0]["name"] == "Test Game"
    assert data["result"][0]["page_id"] == 123


@pytest.mark.asyncio
async def test_search_invalid_key(async_client):
    response = await async_client.get(
        "/api/search?query=test", headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key. Access denied."


@pytest.mark.asyncio
async def test_search_empty_no_cache(
    async_client, auth_headers, mock_database_documents
):
    mock_search, _ = mock_database_documents
    fake_empty_pcgw = MagicMock()
    fake_empty_pcgw.search_game = AsyncMock(return_value={"result": []})
    app.dependency_overrides[get_pcgw] = lambda: fake_empty_pcgw

    response = await async_client.get("/api/search?query=blah", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "limit": 10,
        "offset": 0,
        "result": [],
    }

    mock_search.return_value.insert.assert_not_called()
    mock_search.return_value.replace.assert_not_called()

    app.dependency_overrides[get_pcgw] = fake_get_pcgw


@pytest.mark.asyncio
async def test_get_game(async_client, auth_headers):
    response = await async_client.get("/api/game/123", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Game"
    assert data["id"] == 123


@pytest.mark.asyncio
async def test_get_game_data(async_client, auth_headers):
    response = await async_client.get("/api/game/123/game-data", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Test Game"
    assert data["config"]["config"] == [["Windows", "Path/to/whatever"]]


@pytest.mark.asyncio
async def test_delete_game(async_client, auth_headers, mock_database_documents):
    _, mock_game = mock_database_documents

    # Simulate an existing game in DB
    mock_game_instance = MagicMock()
    mock_game_instance.delete = AsyncMock()
    mock_game.get = AsyncMock(return_value=mock_game_instance)

    response = await async_client.delete("/api/game/123", headers=auth_headers)
    assert response.status_code == 204
    mock_game_instance.delete.assert_called_once()


@pytest.mark.asyncio
async def test_get_game_force_refresh(
    async_client, auth_headers, mock_database_documents
):
    _, mock_game = mock_database_documents

    # Simulate cached game in DB
    cached_doc = MagicMock()
    cached_doc.updated_at = datetime.now(UTC)
    cached_doc.model_dump.return_value = {
        **SAMPLE_GAME_DATA,
        "name": "Cached Game",
    }
    mock_game.get = AsyncMock(return_value=cached_doc)

    fake_pcgw = fake_get_pcgw()
    app.dependency_overrides[get_pcgw] = lambda: fake_pcgw

    # 1. Normal request returns cached game without calling pcgw
    resp_cached = await async_client.get("/api/game/123", headers=auth_headers)
    assert resp_cached.status_code == 200
    assert resp_cached.json()["name"] == "Cached Game"
    fake_pcgw.get_game.assert_not_called()

    # 2. force_refresh=true bypasses cache and calls pcgw
    resp_fresh = await async_client.get(
        "/api/game/123?force_refresh=true", headers=auth_headers
    )
    assert resp_fresh.status_code == 200
    fake_pcgw.get_game.assert_called_once_with(pid=123)

    app.dependency_overrides[get_pcgw] = fake_get_pcgw


@pytest.mark.asyncio
async def test_search_force_refresh(
    async_client, auth_headers, mock_database_documents
):
    mock_search, _ = mock_database_documents

    cached_search = MagicMock()
    cached_search.updated_at = datetime.now(UTC)
    cached_search.result = [{"name": "Cached Result", "page_id": 999}]
    mock_search.get = AsyncMock(return_value=cached_search)

    fake_pcgw = fake_get_pcgw()
    app.dependency_overrides[get_pcgw] = lambda: fake_pcgw

    # 1. Normal request uses cache
    resp_cached = await async_client.get("/api/search?query=test", headers=auth_headers)
    assert resp_cached.status_code == 200
    assert resp_cached.json()["result"][0]["name"] == "Cached Result"
    fake_pcgw.search_game.assert_not_called()

    # 2. force_refresh=true bypasses cache
    resp_fresh = await async_client.get(
        "/api/search?query=test&force_refresh=true", headers=auth_headers
    )
    assert resp_fresh.status_code == 200
    fake_pcgw.search_game.assert_called_once_with("test")

    app.dependency_overrides[get_pcgw] = fake_get_pcgw
