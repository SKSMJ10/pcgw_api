from typing import ClassVar
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime, UTC
from beanie import Document
from pymongo import ASCENDING, IndexModel

TTL_7_DAYS = 604800

type ConfigSaveData = list[tuple[str, str]] | None


class Health(BaseModel):
    status: str


class Feature(BaseModel):
    name: str
    state: str
    notes: str | None


class VideoResponse(BaseModel):
    name: str
    video: dict[str, Feature]


class AudioResponse(BaseModel):
    name: str
    audio: dict[str, Feature]


class GameDataResponse(BaseModel):
    name: str
    config: dict[str, ConfigSaveData]


class ApiData(BaseModel):
    name: str
    support: float | str
    notes: str | None


class ExecutableData(BaseModel):
    name: str
    version: list[str] | str
    notes: str | None


class MiddlewareData(BaseModel):
    type_: str = Field(alias="type")
    middleware: str = Field(
        title="Game's middlewares",
        description="A markdown link with the middleware's name and it's respective PCGW's wiki",
        examples=["[SpeedTree](https://www.pcgamingwiki.com/wiki/SpeedTree)"],
    )
    notes: str | None


class ApiMiddlewareResponse(BaseModel):
    name: str
    api: dict[str, ApiData]
    executable: dict[str, ExecutableData]
    middleware: dict[str, MiddlewareData]


class InfoResponse(BaseModel):
    name: str
    developers: list[str]
    engines: list[str] | None = None
    released: dict[str, date | str]
    publishers: list[str] | None = None
    taxonomy: dict[str, list[str]]


class SearchResult(BaseModel):
    name: str
    page_id: int


class SearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    result: list[SearchResult]


class GameResponse(BaseModel):
    id: int = Field(validation_alias="_id")
    name: str
    game_data: dict[str, ConfigSaveData]
    video: dict[str, Feature]
    audio: dict[str, Feature]
    info: InfoResponse
    api: dict[str, ApiData]
    executable: dict[str, ExecutableData]
    middleware: dict[str, MiddlewareData] | None = None

    model_config = ConfigDict(populate_by_name=True)


class GameDocument(Document):
    id: int = Field(alias="_id")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    name: str
    game_data: dict[str, ConfigSaveData]
    video: dict[str, Feature]
    audio: dict[str, Feature]
    info: InfoResponse
    api: dict[str, ApiData]
    executable: dict[str, ExecutableData]
    middleware: dict[str, MiddlewareData] | None = None

    class Settings:
        name = "games"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("updated_at", ASCENDING)],
                expireAfterSeconds=TTL_7_DAYS,
                name="ttl_game_updated_at_7d",
            )
        ]


class SearchDocument(Document):
    id: str = Field(alias="_id")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    result: list[SearchResult]

    class Settings:
        name = "searches"
        indexes: ClassVar[list[IndexModel]] = [
            IndexModel(
                [("updated_at", ASCENDING)],
                expireAfterSeconds=TTL_7_DAYS,
                name="ttl_search_updated_at_7d",
            )
        ]
