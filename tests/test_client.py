import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.scraper.client import PCGamingWiki
from app.scraper.game import Game


@pytest.fixture(autouse=True)
def mock_rate_limiter():
    mock = AsyncMock()
    with patch("app.scraper.utils.limiter", mock):
        yield mock


@pytest.fixture
def mock_httpx_client():
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()
    client.post = AsyncMock()

    async def fake_request(method, url, **kwargs):
        if method.upper() == "GET":
            return await client.get(url, **kwargs)
        elif method.upper() == "POST":
            return await client.post(url, **kwargs)
        raise NotImplementedError

    client.request = AsyncMock(side_effect=fake_request)
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
    search_data = {
        "query": {
            "search": [
                {"title": "Cyberpunk 2077", "pageid": 1091500},
                {
                    "title": "Cyberpunk 2077: Phantom Liberty",
                    "pageid": 2104523,
                },  # PCGW page of this does not exist as its a dlc, this is just to populate the test data
            ],
        }
    }
    mock_httpx_client.get.return_value = create_response(200, search_data)

    result = await pcgw_client.search_game("Cyberpunk 2077")

    assert result == {
        "result": [
            {"name": "Cyberpunk 2077", "page_id": 1091500},
            {"name": "Cyberpunk 2077: Phantom Liberty", "page_id": 2104523},
        ]
    }
    mock_httpx_client.get.assert_called_once_with(
        PCGamingWiki.API,
        params={
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "list": "search",
            "srsearch": "Cyberpunk 2077",
            "srlimit": "max",  # default is 10, just putting it explicitly
            "srnamespace": 0,
        },
    )


@pytest.mark.asyncio
async def test_search_game_with_special_characters(pcgw_client, mock_httpx_client):
    mock_httpx_client.get.return_value = create_response(200, {"query": {"search": []}})

    result = await pcgw_client.search_game("Assassin's Creed")

    assert result == {"result": []}
    _, kwargs = mock_httpx_client.get.call_args
    assert kwargs["params"]["srsearch"] == "Assassin's Creed"


@pytest.mark.asyncio
async def test_search_game_empty_response(pcgw_client, mock_httpx_client):
    mock_httpx_client.get.return_value = create_response(200, {})

    result = await pcgw_client.search_game("NonexistentGame")

    assert result == {"result": []}


@pytest.mark.asyncio
async def test_search_game_retry_on_transient_error(pcgw_client, mock_httpx_client):
    error_response = create_response(503)
    success_response = create_response(200, {"query": {"search": []}})

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


@pytest.mark.asyncio
async def test_login_failure_raises_clean_error(pcgw_client, mock_httpx_client):
    token_resp = create_response(200, {"query": {"tokens": {"logintoken": "token123"}}})
    login_fail_resp = create_response(
        200, {"login": {"result": "Failed", "reason": "Incorrect password"}}
    )

    mock_httpx_client.get.return_value = token_resp
    mock_httpx_client.post.return_value = login_fail_resp

    with pytest.raises(Exception) as exc_info:
        await pcgw_client.login()

    assert "Incorrect password" in str(exc_info.value)


@pytest.mark.asyncio
async def test_search_game_upstream_error_raises_runtime_error(
    pcgw_client, mock_httpx_client
):
    error_payload = {
        "error": {
            "code": "missingparam",
            "info": 'The "srsearch" parameter must be set.',
        }
    }
    mock_httpx_client.get.return_value = create_response(200, error_payload)

    with pytest.raises(RuntimeError) as exc_info:
        await pcgw_client.search_game("Cyberpunk")

    assert 'The "srsearch" parameter must be set.' in str(exc_info.value)
