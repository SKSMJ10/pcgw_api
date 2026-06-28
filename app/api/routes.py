import logging
import httpx
import sentry_sdk
from fastapi import APIRouter, Request, Depends, HTTPException, status
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError
from app.api.auth import verify_api_key
from app.scraper.client import PCGamingWiki
from app.schemas.models import (
    VideoResponse,
    AudioResponse,
    ApiMiddlewareResponse,
    InfoResponse,
    SearchResponse,
    GameDataResponse,
    GameDocument,
    SearchDocument,
)

router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])
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

        except ValidationError as exc:
            logger.warning(f"Failed to validate data for {page_id}: {exc}")
            sentry_sdk.capture_exception(exc)
            raise HTTPException(
                status_code=500,
                detail="Data validation error while parsing received response.",
            )

        except ValueError as exc:
            logger.warning(f"Game ID {page_id} not found on PCGW.")
            sentry_sdk.capture_exception(exc)
            raise HTTPException(status_code=404, detail="Game not found")

        except httpx.TimeoutException as exc:
            logger.error(f"Timeout connecting to PCGW for game {page_id}.")
            sentry_sdk.capture_exception(exc)
            raise HTTPException(status_code=504, detail="PCGamingWiki API timeout")

        except httpx.HTTPError as exc:
            logger.error(f"Error while connecting to PCGW for game {page_id}: {exc}")
            sentry_sdk.capture_exception(exc)
            raise HTTPException(
                status_code=502, detail="Bad Gateway: PCGamingWiki error"
            )

        if cached_game:
            await validated_game.replace()
        else:
            await validated_game.insert()

    return validated_game.model_dump(by_alias=True)


@router.get(path="/search", response_model=SearchResponse)
async def search(
    query: str, limit: int = 10, offset: int = 0, pcgw: PCGamingWiki = Depends(get_pcgw)
):
    query_id = query.strip().lower()
    cached_search = await SearchDocument.get(query_id)

    if cached_search and (
        datetime.now(timezone.utc) - cached_search.updated_at <= timedelta(days=7)
    ):
        logger.info(f"Fetched search '{query}' from DB")
        # data = {"result": cached_search.result}
        full_result = cached_search.result
    else:
        logger.info(
            f"No results found for {query} or the searchdata is too old. Getting fresh data..."
        )
        try:
            data = await pcgw.search_game(query)
        except httpx.TimeoutException as exc:
            logger.error(f"Timeout while searching PCGW for '{query}'.")
            sentry_sdk.capture_exception(exc)
            raise HTTPException(status_code=504, detail="PCGamingWiki API timeout")
        except httpx.HTTPError as exc:
            logger.error(f"Error while searching PCGW for '{query}': {exc}")
            sentry_sdk.capture_exception(exc)
            raise HTTPException(
                status_code=502, detail="Bad Gateway: PCGamingWiki error"
            )

        full_result = data.get("result", [])
        search_doc = SearchDocument(id=query_id, result=full_result)

        if cached_search:
            await search_doc.replace()
        else:
            await search_doc.insert()

    total_results = len(full_result)

    if limit == 0:
        paginated = full_result[offset:]
    else:
        paginated = full_result[offset : offset + limit]

    final_data = {
        "total": total_results,
        "limit": limit,
        "offset": offset,
        "result": paginated,
    }

    return final_data


@router.get(path="/game/{page_id}/game-data", response_model=GameDataResponse)
async def game_data_config(data: dict = Depends(get_game_data)):
    return {"name": data["name"], "config": data.get("game_data", {})}


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

@router.delete(path="/game/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(page_id: int):
    cached_game = await GameDocument.get(page_id)
    logger.info(f"Successfully deleted {page_id}'s gamedocument.")

    if cached_game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    await cached_game.delete()
