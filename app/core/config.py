from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    email: str = "name@example.com"
    mongo_uri: str
    api_key: str
    sentry_dsn: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
