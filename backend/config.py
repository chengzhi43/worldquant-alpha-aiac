"""
AIAC 2.0 Configuration
Centralized settings management using Pydantic
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Project Info
    PROJECT_NAME: str = "AIAC 2.0 - Alpha-GPT Mining System"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "alpha_gpt")
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis (for Celery and SSE)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
    
    # Brain Platform Credentials
    BRAIN_EMAIL: str = os.getenv("BRAIN_EMAIL", "")
    BRAIN_PASSWORD: str = os.getenv("BRAIN_PASSWORD", "")
    
    # LLM Configuration (OpenAI Compatible)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # Mining Configuration
    DEFAULT_REGION: str = "USA"
    DEFAULT_UNIVERSE: str = "TOP3000"
    DEFAULT_DAILY_GOAL: int = 4
    
    # Quality Thresholds (Traditional)
    SHARPE_MIN: float = 1.5
    TURNOVER_MAX: float = 0.7
    FITNESS_MIN: float = 0.6
    MAX_CORRELATION: float = 0.7
    
    # Multi-Objective Scoring Thresholds
    SCORE_PASS_THRESHOLD: float = 0.8      # Composite score to pass
    SCORE_OPTIMIZE_THRESHOLD: float = 0.3  # Score threshold for optimization queue
    
    # Evolution Strategy Defaults
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_EXPLORATION_WEIGHT: float = 0.5
    MAX_EVOLUTION_ITERATIONS: int = 10
    ALPHAS_PER_ROUND: int = 4
    
    # Optimization Chain Settings
    MAX_OPTIMIZATION_VARIANTS: int = 10
    MAX_SETTINGS_VARIANTS: int = 5
    OPTIMIZATION_BUDGET_PER_ALPHA: int = 20  # Max simulations per optimization target
    
    # Field Screening Settings
    FIELD_SCREENING_ENABLED: bool = True
    FIELD_SCREENING_TOP_K: int = 20
    FIELD_SCREENING_TEMPLATES: int = 4  # Number of templates to test per field
    
    # Rate Limiting
    MAX_SIMULATIONS_PER_DAY: int = 100
    MAX_TOKENS_PER_DAY: int = 500000
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


settings = Settings()
