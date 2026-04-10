import httpx
from fastapi import FastAPI
from app.api.routes import router
from app.database.connection import client
from app.schemas.models import GameDocument
from contextlib import asynccontextmanager
from beanie import init_beanie


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await client.admin.command("ping")
        print("You successfully connected to MongoDB!")

        await init_beanie(database=client.pcgw_db, document_models=[GameDocument])
        print("Beanie initialized successfully!")

        app.state.http_client = httpx.AsyncClient()
        print("HTTP client initialized successfully!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
    yield
    if hasattr(app.state, "http_client"):
        await app.state.http_client.aclose()
    await client.close()


app = FastAPI(title="PCGamingWiki API", version="1.0", lifespan=lifespan)
app.include_router(router=router)
