"""
SKT-AI-LABS Configuration
Centralized settings management
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class SKTSettings(BaseSettings):
    """SKT-AI-LABS global settings"""

    # App
    APP_NAME: str = "SKT-AI-LABS-ADK"
    APP_VERSION: str = "1.0.0"
    APP_MODE: str = "development"  # development, staging, production

    # LLM APIs
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Default LLM
    DEFAULT_MODEL: str = "gemini-2.5-pro"
    DEFAULT_TEMPERATURE: float = 0.3
    DEFAULT_MAX_TOKENS: int = 4096

    # Search
    TAVILY_API_KEY: Optional[str] = None
    BRAVE_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None

    # Database
    DATABASE_URL: Optional[str] = None

    # Vector Store
    VECTOR_STORE_TYPE: str = "chroma"  # chroma, pgvector, faiss, redis
    VECTOR_STORE_PATH: str = "./skt_vector_db"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Browser
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 30000
    BROWSER_ANTI_BOT: bool = True

    # Agent
    AGENT_MAX_ITERATIONS: int = 15
    AGENT_MAX_CONCURRENT: int = 10
    AGENT_MAX_DURATION: int = 300
    AGENT_TOKEN_BUDGET: int = 128000

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = SKTSettings()
