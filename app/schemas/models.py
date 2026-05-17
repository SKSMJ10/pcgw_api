from pydantic import BaseModel, Field, RootModel
from datetime import date, datetime, timezone
from beanie import Document


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


class ApiData(BaseModel):
    name: str
    support: float | str
    notes: str | None


class ExecutableData(BaseModel):
    name: str
    version: str
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


class MarkdownLinks(RootModel):
    root: list[str] = Field(
        title="List of markdown links",
        description="A list of markdown links with contextual field's name and it's respective PCGW's wikipage.",
        examples="[SpeedTree](https://www.pcgamingwiki.com/wiki/SpeedTree)",
    )


class TaxonomyData(RootModel):
    root: dict[str, MarkdownLinks]


class InfoResponse(BaseModel):
    name: str
    developers: list[str]
    engines: list[str] | None
    released: dict[str, date | str]
    publishers: list[str] | None
    taxonomy: TaxonomyData


class SearchResult(BaseModel):
    name: str
    page_id: int


class SearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    result: list[SearchResult]


class GameDocument(Document):
    id: int = Field(alias="_id")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    name: str
    video: dict[str, Feature]
    audio: dict[str, Feature]
    info: InfoResponse
    api: dict[str, ApiData]
    executable: dict[str, ExecutableData]
    middleware: dict[str, MiddlewareData]

    class Settings:
        name = "games"


class SearchDocument(Document):
    id: str = Field(alias="_id")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: list[SearchResult]

    class Settings:
        name = "searches"
