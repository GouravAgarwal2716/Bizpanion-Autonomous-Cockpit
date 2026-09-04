"""
Centralized settings using pydantic-settings.
All values are read from environment variables or .env file.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Featherless.ai
    FEATHERLESS_API_KEY: str = ""
    FEATHERLESS_LLM_MODEL: str = "meta-llama/Llama-3.1-70B-Instruct"
    FEATHERLESS_EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-8B"
    FEATHERLESS_TTS_MODEL: str = "hexgrad/Kokoro-82M"
    FEATHERLESS_BASE_URL: str = "https://api.featherless.ai/v1"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_URL: str = ""

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "bizpanion-schemes"

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"

    # App
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    JWT_SECRET_KEY: str = "change-me-in-production-min-32-chars"
    AUDIO_CACHE_DIR: str = "./audio_cache"
    MODEL_WEIGHTS_PATH: str = "./models/forecast_model.pt"

    # Anomaly thresholds (configurable per business)
    UNDERPRICING_THRESHOLD_PCT: float = 15.0   # flag if >15% below market
    STOCK_DEPLETION_DAYS_AHEAD: int = 7         # forecast 7 days out
    SCHEME_DEADLINE_DAYS: int = 7               # flag if deadline within 7 days
    SALES_ZSCORE_THRESHOLD: float = 2.0         # flag if z-score > 2

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
