from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_MODEL_NAME: str = "gpt-4o"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()  # type: ignore
