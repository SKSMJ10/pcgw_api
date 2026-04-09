from fastapi import APIRouter, HTTPException
from app.scraper.client import PCGamingWiki
from app.schemas.models import (
    VideoResponse,
    AudioResponse,
    ApiMiddlewareResponse,
    InfoResponse,
)
from app.database.connection import games_info

router = APIRouter(prefix="/api/v1")
pcgw = PCGamingWiki()


def get_game_data(page_id: int) -> dict:
    cached_game = games_info.find_one({"_id": page_id})
    if cached_game:
        return cached_game

    game = pcgw.get_game(pid=page_id)
    all_data = game.get_all()
    games_info.insert_one(all_data)
    return all_data


@router.get(path="/game/{page_id}/video", response_model=VideoResponse)
def get_video(page_id: int):
    try:
        data = get_game_data(page_id)
        return {"name": data["name"], "video": data.get("video", {})}
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Failed to get the game's video details. {str(e)}"
        )


@router.get(path="/game/{page_id}/audio", response_model=AudioResponse)
def get_audio(page_id: int):
    try:
        data = get_game_data(page_id)
        return {"name": data["name"], "audio": data.get("audio", {})}
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Failed to get the game's audio details. {str(e)}"
        )


@router.get(path="/game/{page_id}/api-mw", response_model=ApiMiddlewareResponse)
def get_api_middleware(page_id: int):
    try:
        data = get_game_data(page_id)
        return {
            "name": data["name"],
            "api": data.get("api", {}),
            "executable": data.get("executable", {}),
            "middleware": data.get("middleware", {}),
        }
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to get the game's API and middleware details. {str(e)}",
        )


@router.get(path="/game/{page_id}/info", response_model=InfoResponse)
def get_info(page_id: int):
    try:
        data = get_game_data(page_id)
        return data.get("info", {})
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to get the game's API infobox details. {str(e)}",
        )
