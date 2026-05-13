import logging
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from app.api.routes import router
from app.database.connection import client
from app.config import settings
from app.schemas.models import GameDocument, SearchDocument
from contextlib import asynccontextmanager
from beanie import init_beanie
from pymongo.errors import PyMongoError


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        headers={"User-Agent": f"PCGW-Scraper/{settings.email}"},
        timeout=httpx.Timeout(10.0, connect=5.0),
    )
    logger.info("HTTP client initialized successfully!")
    try:
        await client.admin.command("ping")
        logger.info("You successfully connected to MongoDB!")

        try:
            await init_beanie(
                database=client.pcgw_db, document_models=[GameDocument, SearchDocument]
            )
            logger.info("Beanie initialized successfully!")
        except Exception as e:
            logger.error(f"Failed to initiate Beanie: {e}")
            raise e

    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e

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
    logger.exception(
        f"Database connection error on {request.method} {request.url}: {exc}"
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Database service is currently unavailable."},
    )


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500, content={"detail": "An unexpected error occurred."}
    )


app.include_router(router=router)
