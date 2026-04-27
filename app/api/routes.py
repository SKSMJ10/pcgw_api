import logging
import httpx
from fastapi import APIRouter, Request, Depends, HTTPException
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
    
    if cached_game and (
        datetime.now(timezone.utc) - cached_game.updated_at <= timedelta(days=7)
    ):
        logger.info(f"Fetched {page_id}'s gamedata from DB")
        validated_game = cached_game
    else:
        logger.info(
            f"{page_id}'s gamedata not found or the gamedata is too old. Getting fresh gamedata..."
        )
        try:
            game = pcgw.get_game(pid=page_id)
            all_data = await game.get_all()
            validated_game = GameDocument(**all_data)
        except ValueError:
            logger.warning(f"Game ID {page_id} not found on PCGW.")
            raise HTTPException(status_code=404, detail="Game not found")
        except httpx.TimeoutException:
            logger.error(f"Timeout connecting to PCGW for game {page_id}.")
            raise HTTPException(status_code=504, detail="PCGamingWiki API timeout")
        except httpx.HTTPError as exc:
            logger.error(f"Error while connecting to PCGW for game {page_id}: {exc}")
            raise HTTPException(status_code=502, detail="Bad Gateway: PCGamingWiki error")

        if cached_game:
            await validated_game.replace()
        else:
            await validated_game.insert()

    return validated_game.model_dump(by_alias=True)


@router.get(path="/search", response_model=SearchResponse)
async def search(query: str, pcgw: PCGamingWiki = Depends(get_pcgw)):
    query_id = query.lower()
    cached_search = await SearchDocument.get(query_id)

    if cached_search and (
        datetime.now(timezone.utc) - cached_search.updated_at <= timedelta(days=1)
    ):
        logger.info(f"Fetched search '{query}' from DB")
        data = {"result": cached_search.result}
    else:
        logger.info(
            f"No results found for {query} or the searchdata is too old. Getting fresh data..."
        )
        try:
            data = await pcgw.search_game(query)
        except httpx.TimeoutException:
            logger.error(f"Timeout while searching PCGW for '{query}'.")
            raise HTTPException(status_code=504, detail="PCGamingWiki API timeout")
        except httpx.HTTPError as exc:
            logger.error(f"Error while searching PCGW for '{query}': {exc}")
            raise HTTPException(status_code=502, detail="Bad Gateway: PCGamingWiki error")

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
