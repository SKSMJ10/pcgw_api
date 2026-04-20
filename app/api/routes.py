import logging
from fastapi import APIRouter, Request, Depends
from datetime import datetime, timezone, timedelta
from app.scraper.client import PCGamingWiki
from app.schemas.models import (
    VideoResponse,
    AudioResponse,
    ApiMiddlewareResponse,
    InfoResponse,
    SearchResponse,
    GameDocument,
    SearchDocument,
)

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)


def get_pcgw(request: Request) -> PCGamingWiki:
    return PCGamingWiki(client=request.app.state.http_client)


async def get_game_data(page_id: int, pcgw: PCGamingWiki = Depends(get_pcgw)) -> dict:
    # beanie can query with the data model itself, neat stuff
    cached_game = await GameDocument.get(page_id)
    fresh_data = datetime.now(timezone.utc) - cached_game.updated_at <= timedelta(
        days=7
    )

    if cached_game and fresh_data:
        logger.info(f"Fetched {page_id}'s gamedata from DB")
        validated_game = cached_game
    else:
        logger.info(
            f"{page_id}'s gamedata not found or the gamedata is too old. Scraping fresh gamedata..."
        )
        game = pcgw.get_game(pid=page_id)
        validated_game = GameDocument(**(await game.get_all()))

        if cached_game:
            await validated_game.replace()
        else:
            await validated_game.insert()

    return validated_game.model_dump(by_alias=True)


@router.get(path="/search", response_model=SearchResponse)
async def search(query: str, pcgw: PCGamingWiki = Depends(get_pcgw)):
    query_id = query.lower()
    cached_search = await SearchDocument.get(query_id)
    fresh_data = datetime.now(timezone.utc) - cached_search.updated_at <= timedelta(
        days=1
    )

    if cached_search and fresh_data:
        logger.info(f"Fetched search '{query}' from DB")
        data = {"result": cached_search.result}
    else:
        logger.info(
            f"No results found for {query} or the searchdata is too old. Scraping fresh data..."
        )
        data = await pcgw.search_game(query)
        search_doc = SearchDocument(id=query_id, result=data.get("result", []))

        if cached_search:
            await search_doc.replace()
        else:
            await search_doc.insert()

    return data


@router.get(path="/game/{page_id}/video", response_model=VideoResponse)
async def get_video(data: dict = Depends(get_game_data)):
    return {"name": data["name"], "video": data.get("video", {})}


@router.get(path="/game/{page_id}/audio", response_model=AudioResponse)
async def get_audio(data: dict = Depends(get_game_data)):
    return {"name": data["name"], "audio": data.get("audio", {})}


@router.get(path="/game/{page_id}/api-mw", response_model=ApiMiddlewareResponse)
async def get_api_middleware(data: dict = Depends(get_game_data)):
    return {
        "name": data["name"],
        "api": data.get("api", {}),
        "executable": data.get("executable", {}),
        "middleware": data.get("middleware", {}),
    }


@router.get(path="/game/{page_id}/info", response_model=InfoResponse)
async def get_info(data: dict = Depends(get_game_data)):
    return data.get("info", {})
