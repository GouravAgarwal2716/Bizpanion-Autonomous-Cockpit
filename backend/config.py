"""
Centralized settings using pydantic-settings.
All values are read from environment variables or .env file.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


import os

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

class Settings(BaseSettings):
    # Featherless.ai
    FEATHERLESS_API_KEY: str = "rc_1bb1719dc5863ec638f3fa42ce3132f6f03c8e4ddb329d0d383364719bf236a7"
    FEATHERLESS_LLM_MODEL: str = "Qwen/Qwen2.5-7B-Instruct"
    FEATHERLESS_EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-8B"
    FEATHERLESS_TTS_MODEL: str = "hexgrad/Kokoro-82M"
    FEATHERLESS_BASE_URL: str = "https://api.featherless.ai/v1"

    # Supabase
    SUPABASE_URL: str = "https://lywdxkhcmqrxlaoexoru.supabase.co"
    SUPABASE_ANON_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx5d2R4a2hjbXFyeGxhb2V4b3J1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1MTAyOTUsImV4cCI6MjEwNDA4NjI5NX0.CReQCGrB76Mmm_89ClC0sDkmjhBNav2dhhCNkd-BdVQ"
    SUPABASE_SERVICE_ROLE_KEY: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx5d2R4a2hjbXFyeGxhb2V4b3J1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4ODUxMDI5NSwiZXhwIjoyMTA0MDg2Mjk1fQ.3_FrYKYR__hxj-TdosdY2se8JOm2b9Nu_aRuQ95nDxg"
    DATABASE_URL: str = ""

    # Pinecone
    PINECONE_API_KEY: str = "pcsk_2VtyXC_Cir9oDmJT7Q63EsNfocuUsv9t2RMZDRsmHFe7ixGFBhCU2FXGrFwS3dRTE8KAEk"
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "bizintel-policies"

    # Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
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
        env_file = ENV_PATH
        extra = "ignore"


settings = Settings()
