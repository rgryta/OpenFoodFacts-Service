"""
Configuration management for OpenFoodFacts API service
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database configuration
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://offuser:password@off-db:5432/openfoodfacts"
    )

    # API Keys (comma-separated list)
    api_keys: str = os.getenv("API_KEYS", "")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Service metadata
    service_name: str = "OpenFoodFacts API"
    version: str = "1.0.0"

    @property
    def api_keys_list(self) -> List[str]:
        """Parse comma-separated API keys into list"""
        if not self.api_keys:
            return []
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
