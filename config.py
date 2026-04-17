from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # CHROMADB
    CHROMA_HOST: str
    CHROMA_PORT: int

    # OPENROUTER
    OPEN_ROUTER_API_KEY: str
    OPENAI_API_KEY: str
    OPEN_ROUTER_DEFAULT_MODEL: str = "google/gemini-2.5-flash-lite"
    CHAT_COMPLETIONS_URL: str = "https://openrouter.ai/api/v1/chat/completions"


settings = Settings()
