import logging
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.routes import router
from app.database.connection import client
from app.schemas.models import GameDocument, SearchDocument
from contextlib import asynccontextmanager
from beanie import init_beanie

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s: %(asctime)s - %(name)s - %(message)s",
    datefmt= "%Y-%m-%d %H:%M:%S"
)
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await client.admin.command("ping")
        logger.info("You successfully connected to MongoDB!")

        await init_beanie(
            database=client.pcgw_db, document_models=[GameDocument, SearchDocument]
        )
        logger.info("Beanie initialized successfully!")

        app.state.http_client = httpx.AsyncClient()
        logger.info("HTTP client initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
    yield
    if hasattr(app.state, "http_client"):
        await app.state.http_client.aclose()
    await client.close()


app = FastAPI(title="PCGamingWiki API", version="1.0", lifespan=lifespan)


@app.middleware("http")
async def global_exception_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception(f"Unhandled error on {request.method} {request.url}")
        return JSONResponse(
            status_code=500, content={"detail": f"Internal Server Error: {str(exc)}"}
        )


app.include_router(router=router)
