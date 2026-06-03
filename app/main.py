import logging
import logging.config
import httpx
import sentry_sdk
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from app.api.routes import router
from app.database.connection import client
from app.config import settings
from app.schemas.models import GameDocument, SearchDocument, Health
from contextlib import asynccontextmanager
from beanie import init_beanie
from pymongo.errors import PyMongoError


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[31;1m",  # Bold Red
    }
    GRAY = "\033[90m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self._formatters = {}
        for level, color in self.COLORS.items():
            colored_fmt = f"{color}%(levelname_colon)-9s{self.RESET} {self.BLUE}%(asctime)s{self.RESET} - {self.MAGENTA}%(name)s{self.RESET} - %(message)s"
            self._formatters[level] = logging.Formatter(
                fmt=colored_fmt, datefmt=datefmt
            )

        self._fallback = logging.Formatter(
            fmt=f"%(levelname_colon)-7s {self.BLUE}%(asctime)s{self.RESET} - {self.MAGENTA}%(name)s{self.RESET} - %(message)s",
            datefmt=datefmt,
        )

    def format(self, record):
        record.levelname_colon = f"{record.levelname}:"
        formatter = self._formatters.get(record.levelname, self._fallback)
        return formatter.format(record)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "custom": {
            "()": ColorFormatter,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "console": {
            "formatter": "custom",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        "httpx": {"level": "WARNING"},
        "app": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
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


@app.get(path="/health", response_model=Health, include_in_schema=False)
async def health_check():
    try:
        await client.admin.command("ping")
        return Health(status="OK")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503, detail="Database service is not available."
        )


@app.get(path="/sentry-debug", include_in_schema=False)
async def trigger_error():
    1 / 0


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
