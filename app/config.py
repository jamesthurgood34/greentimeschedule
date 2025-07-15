import os
from typing import Optional
from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings."""

    # API settings
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    PROJECT_NAME: str = "Green Time Schedule API"

    # Carbon Intensity API settings
    CARBON_INTENSITY_API_URL: str = "https://api.carbonintensity.org.uk"
    CARBON_INTENSITY_TIMEOUT: int = 10  # seconds

    # Cache settings
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL: int = 1800  # 30 minutes in seconds

    # Scheduling settings
    MAX_JOB_DURATION_MINUTES: int = 1440  # 24 hours
    MIN_JOB_DURATION_MINUTES: int = 30  # 30 minutes
    MAX_FORECAST_DAYS: int = 2  # Carbon Intensity API limitation
    MAX_ALTERNATIVE_SLOTS: int = 3  # Number of alternative slots to return


# Create global settings object
settings = Settings()
