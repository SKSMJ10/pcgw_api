import logging
import logging.config
import httpx
import sentry_sdk
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from app.core.logging import LOGGING_CONFIG
from app.api.routes import router
from app.database.connection import client
from app.core.config import settings
from app.schemas.models import GameDocument, SearchDocument, Health
from app.scraper.client import PCGamingWiki
from contextlib import asynccontextmanager
from beanie import init_beanie
from pymongo.errors import PyMongoError

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Sentry setup
sentry_sdk.init(
    dsn=settings.sentry_dsn,
    send_default_pii=True,
    enable_logs=True,
    traces_sample_rate=1.0,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        headers={"User-Agent": f"PCGW-Scraper/{settings.email}"},
        timeout=httpx.Timeout(10.0, connect=5.0),
    )
    logger.info("HTTP client initialized successfully!")

    # Initialize PCGW Client
    if settings.pcgw_user and settings.pcgw_pass:
        app.state.pcgw = PCGamingWiki(client=app.state.http_client)
        try:
            await app.state.pcgw.login()
        except Exception as e:
            logger.error(f"Failed to log in to PCGW: {e}")
            raise

    try:
        await client.admin.command("ping")
        logger.info("Connected to MongoDB successfully!")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise

    # Initialize Beanie
    try:
        await init_beanie(
            database=client.pcgw_db,
            document_models=[GameDocument, SearchDocument],
        )
        logger.info("Beanie initialized successfully!")
    except Exception as e:
        logger.error(f"Beanie initialization failed: {e}")
        raise

    yield
    if hasattr(app.state, "http_client"):
        await app.state.http_client.aclose()
    await client.close()


app = FastAPI(
    title="PCGamingWiki API",
    version="0.1",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)


@app.get(path="/health", response_model=Health, include_in_schema=False)
async def health_check():
    try:
        await client.admin.command("ping")
        return Health(status="OK")
    except PyMongoError as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503, detail="Database service is not available."
        ) from e


@app.get(path="/docs", include_in_schema=False)
async def serve_elements_html():
    return HTMLResponse("""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>PCGW API Docs</title>
    <!-- Embed elements Elements via Web Component -->
    <script src="https://unpkg.com/@stoplight/elements/web-components.min.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/@stoplight/elements/styles.min.css">
  </head>
  <body>

    <elements-api
      apiDescriptionUrl="/openapi.json"
      router="hash"
      layout="sidebar"
    />

  </body>
</html>""")


@app.exception_handler(PyMongoError)
async def mongodb_error_handler(request: Request, exc: PyMongoError):
    logger.error(f"Database connection error on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database service is currently unavailable."},
    )


app.include_router(router=router)
