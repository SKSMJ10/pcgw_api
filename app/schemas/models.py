from pydantic import BaseModel, Field, RootModel
from datetime import date


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
    released: dict[str, date]
    publishers: list[str] | None
    taxonomy: TaxonomyData
