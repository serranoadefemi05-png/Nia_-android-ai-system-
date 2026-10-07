"""
NIA Backend — Core Configuration
All secrets are read from environment variables. Never hardcode secrets.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "NIA Backend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str  # Required — set in .env
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "sqlite:///./nia.db"

    # AI / LLM
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None  # OpenRouter — routes to 200+ OSS models
    LLM_PROVIDER: str = "openai"   # "openai" | "anthropic" | "openrouter" | "local"
    LLM_MODEL: str = "gpt-4o"      # for openrouter: e.g. "mistralai/mistral-7b-instruct:free"
    LLM_BASE_URL: str = "https://api.openai.com/v1"  # override for local servers
    LLM_BASE_URL_API_KEY: Optional[str] = None       # API key for local server
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_TOKENS: int = 512

    # Web Agent (BrowserAgentProvider)
    SERP_API_KEY: Optional[str] = None
    WEB_AGENT_PROVIDER: str = "basic"  # "basic" | "dejevu" (stub)
    DEJEVU_CDP_URL: Optional[str] = None  # future: Chrome CDP endpoint for DejevuProvider
    DEJEVU_MAX_ACTIONS: int = 40
    DEJEVU_MAX_REQUESTS: int = 80

    # Arc (future — all optional; Arc features degrade gracefully if unset)
    ARC_RPC_URL: Optional[str] = None
    ARC_CHAIN_ID: Optional[int] = None
    ARC_WALLET_ADDRESS: Optional[str] = None  # Nia's Arc wallet; NEVER in the Android APK

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # SSRF Protection
    ALLOWED_WEB_HOSTS: Optional[str] = None  # comma-separated whitelist; None = all allowed (dev only)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
