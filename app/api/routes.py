import logging
from fastapi import APIRouter, Request, Depends
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


async def get_game_data(page_id: int, pcgw: PCGamingWiki) -> dict:
    # beanie can query with the data model itself, neat stuff
    cached_game = await GameDocument.get(page_id)
    if cached_game:
        logger.info('Fetched from DB')
        return cached_game.model_dump(by_alias=True)

    game = pcgw.get_game(pid=page_id)
    all_data = await game.get_all()

    validated_game = GameDocument(**all_data)
    await validated_game.insert()
    return validated_game.model_dump(by_alias=True)


@router.get(path="/search", response_model=SearchResponse)
async def search(query: str, pcgw: PCGamingWiki = Depends(get_pcgw)):
    query_id = query.lower()
    cached_search = await SearchDocument.get(query_id)
    if cached_search:
        logger.info(f"Fetched search '{query}' from DB")
        return {"result": cached_search.result}

    data = await pcgw.search_game(query)
    search_doc = SearchDocument(id=query_id, result=data.get("result", []))
    await search_doc.insert()
    return data


@router.get(path="/game/{page_id}/video", response_model=VideoResponse)
async def get_video(page_id: int, pcgw: PCGamingWiki = Depends(get_pcgw)):
    data = await get_game_data(page_id, pcgw)
    return {"name": data["name"], "video": data.get("video", {})}


@router.get(path="/game/{page_id}/audio", response_model=AudioResponse)
async def get_audio(page_id: int, pcgw: PCGamingWiki = Depends(get_pcgw)):
    data = await get_game_data(page_id, pcgw)
    return {"name": data["name"], "audio": data.get("audio", {})}


@router.get(path="/game/{page_id}/api-mw", response_model=ApiMiddlewareResponse)
async def get_api_middleware(page_id: int, pcgw: PCGamingWiki = Depends(get_pcgw)):
    data = await get_game_data(page_id, pcgw)
    return {
        "name": data["name"],
        "api": data.get("api", {}),
        "executable": data.get("executable", {}),
        "middleware": data.get("middleware", {}),
    }


@router.get(path="/game/{page_id}/info", response_model=InfoResponse)
async def get_info(page_id: int, pcgw: PCGamingWiki = Depends(get_pcgw)):
    data = await get_game_data(page_id, pcgw)
    return data.get("info", {})
