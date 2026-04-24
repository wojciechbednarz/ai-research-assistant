from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # CHROMADB
    CHROMA_HOST: str
    CHROMA_PORT: int

    # OPENROUTER
    OPEN_ROUTER_API_KEY: str
    OPENAI_API_KEY: str | None = None
    OPENROUTER_LLM_DEFAULT_MODEL: str = "google/gemini-2.5-flash-lite"
    OPENROUTER_LLM_FALLBACK_MODEL: str = "google/gemini-2.5-flash"
    CHAT_COMPLETIONS_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    LLM_ANALYZE_TEMPERATURE: float = 0.2
    LLM_RESPOND_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 3000
    FIRECRAWL_API_KEY: str | None = None

    # LANGFUSE
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_PUBLIC_KEY: str

    # HTTP / cache
    HTTP_TIMEOUT: int = 60
    CACHE_TTL: int = 3600
    CACHE_MAX_SIZE: int = 256

    # Graph
    MAX_TOOL_ITERATIONS: int = 5

    # Retrieval
    HYBRID_SEARCH_ALPHA: float = 0.7


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
