from enum import Enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CarbonIndex(str, Enum):
    """Carbon intensity index categories."""

    VERY_LOW = "very low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very high"


class CarbonIntensityPeriod(BaseModel):
    """A single period of carbon intensity data."""

    period: int = Field(..., description="Settlement period (1-48)")
    start_time: datetime = Field(..., description="Start time of the period")
    end_time: datetime = Field(..., description="End time of the period")
    intensity_forecast: int = Field(
        ..., description="Forecast carbon intensity (gCO2/kWh)"
    )
    intensity_actual: Optional[int] = Field(
        None, description="Actual carbon intensity if available"
    )
    intensity_index: CarbonIndex = Field(..., description="Carbon intensity category")


class CarbonForecast(BaseModel):
    """Carbon intensity forecast for a specific date."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    forecast_periods: List[CarbonIntensityPeriod] = Field(
        ..., description="List of carbon intensity periods"
    )
    data_freshness: datetime = Field(
        ..., description="When this forecast data was last updated"
    )


class CarbonIntensityAPIResponse(BaseModel):
    """Model for the external Carbon Intensity API response."""

    from_time: datetime = Field(..., alias="from")
    to: datetime
    intensity: dict = Field(...)

    model_config = {"populate_by_name": True}


class CarbonIntensityError(BaseModel):
    """Error response from Carbon Intensity API."""

    code: str
    message: str
