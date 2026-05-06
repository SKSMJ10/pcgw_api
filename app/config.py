from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    email: str = "name@example.com"
    mongo_uri: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
