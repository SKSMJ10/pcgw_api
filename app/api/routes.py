from fastapi import APIRouter, HTTPException
from app.scraper.client import PCGamingWiki
from app.schemas.models import VideoResponse, AudioResponse, ApiMiddlewareResponse, InfoResponse

router = APIRouter(prefix="/api/v1")
pcgw = PCGamingWiki()

@router.get(path="/game/{page-id}/video", response_model=VideoResponse)
def get_video(page_id: int):
    try:
        game = pcgw.get_game(pid=page_id)
        result = game.video()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Failed to get the game's video details. {str(e)}"
        )

@router.get(path="/game/{page_id}/audio", response_model=AudioResponse)
def get_audio(page_id: int):
    try:
        game = pcgw.get_game(pid=page_id)
        result = game.audio()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=404, detail=f"Failed to get the game's audio details. {str(e)}"
        )

@router.get(path="/game/{page_id}/api-mw", response_model=ApiMiddlewareResponse)
def get_api_middleware(page_id: int):
    try:
        game = pcgw.get_game(pid=page_id)
        result = game.api_middleware()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to get the game's API and middleware details. {str(e)}",
        )

@router.get(path="/game/{page_id}/info", response_model=InfoResponse)
def get_info(page_id: int):
    try:
        game = pcgw.get_game(pid=page_id)
        result = game.info()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to get the game's API infobox details. {str(e)}",
        )

