import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.scraper.client import PCGamingWiki
from app.scraper.game import Game


@pytest.fixture(autouse=True)
def mock_rate_limiter():
    with patch("app.scraper.client.limiter") as mock:
        mock.has_capacity.return_value = True
        mock.__aenter__ = AsyncMock(return_value=None)
        mock.__aexit__ = AsyncMock(return_value=None)
        yield mock


@pytest.fixture
def mock_httpx_client():
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()
    return client


@pytest.fixture
def pcgw_client(mock_httpx_client):
    return PCGamingWiki(client=mock_httpx_client)


def create_response(
    status_code: int = 200, json_data: dict | None = None
) -> httpx.Response:
    # Creates real httpx.Response instances instead of mock objects.
    return httpx.Response(
        status_code=status_code,
        json=json_data or {},
        request=httpx.Request("GET", PCGamingWiki.API),
    )


def test_get_game_returns_game_instance(pcgw_client, mock_httpx_client):
    game = pcgw_client.get_game(1091500)
    assert isinstance(game, Game)
    assert game.pid == 1091500
    assert game.session == mock_httpx_client


@pytest.mark.asyncio
async def test_search_game_success(pcgw_client, mock_httpx_client):
    cargo_data = {
        "cargoquery": [
            {"title": {"name": "Cyberpunk 2077", "page_id": "1091500"}},
            {
                "title": {
                    "name": "Cyberpunk 2077: Phantom Liberty",
                    "page_id": "2104523",
                }
            },
        ]
    }
    mock_httpx_client.get.return_value = create_response(200, cargo_data)

    result = await pcgw_client.search_game("Cyberpunk")

    assert result == {
        "result": [
            {"name": "Cyberpunk 2077", "page_id": "1091500"},
            {"name": "Cyberpunk 2077: Phantom Liberty", "page_id": "2104523"},
        ]
    }
    mock_httpx_client.get.assert_called_once_with(
        PCGamingWiki.API,
        params={
            "action": "cargoquery",
            "format": "json",
            "tables": "Infobox_game",
            "fields": "_pageName=name,_pageID=page_id",
            "where": "_pageName LIKE '%Cyberpunk%'",
            "limit": "max",
        },
    )


@pytest.mark.asyncio
async def test_search_game_escapes_single_quotes(pcgw_client, mock_httpx_client):
    mock_httpx_client.get.return_value = create_response(200, {"cargoquery": []})

    result = await pcgw_client.search_game("Assassin's Creed")

    assert result == {"result": []}
    _, kwargs = mock_httpx_client.get.call_args
    assert kwargs["params"]["where"] == "_pageName LIKE '%Assassin\\'s Creed%'"


@pytest.mark.asyncio
async def test_search_game_empty_response(pcgw_client, mock_httpx_client):
    mock_httpx_client.get.return_value = create_response(200, {})

    result = await pcgw_client.search_game("NonexistentGame")

    assert result == {"result": []}


@pytest.mark.asyncio
async def test_search_game_retry_on_transient_error(pcgw_client, mock_httpx_client):
    error_response = create_response(503)
    success_response = create_response(200, {"cargoquery": []})

    http_error = httpx.HTTPStatusError(
        "Service Unavailable", request=error_response.request, response=error_response
    )

    mock_httpx_client.get.side_effect = [http_error, success_response]

    result = await pcgw_client.search_game("Test")

    assert result == {"result": []}
    assert mock_httpx_client.get.call_count == 2


@pytest.mark.asyncio
async def test_search_game_no_retry_on_client_error(pcgw_client, mock_httpx_client):
    error_response = create_response(404)
    http_error = httpx.HTTPStatusError(
        "Not Found", request=error_response.request, response=error_response
    )
    mock_httpx_client.get.side_effect = http_error

    with pytest.raises(httpx.HTTPStatusError):
        await pcgw_client.search_game("Test")

    # 404 status error is not transient; it must fail immediately without retry
    assert mock_httpx_client.get.call_count == 1
