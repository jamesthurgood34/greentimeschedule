from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from app.models.carbon import CarbonIndex


class Priority(str, Enum):
    """Job priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class JobScheduleRequest(BaseModel):
    """Request model for scheduling a job."""
    job_duration_minutes: int = Field(
        ..., 
        ge=30, 
        le=1440,
        description="Duration of the job in minutes (30 min to 24 hours)"
    )
    deadline_utc: datetime = Field(
        ...,
        description="Deadline by which the job must be completed (UTC)"
    )
    job_name: Optional[str] = Field(
        None,
        description="Optional name/identifier for the job"
    )
    priority: Priority = Field(
        Priority.LOW,
        description="Priority level of the job"
    )


class TimeSlot(BaseModel):
    """A time slot with carbon intensity information."""
    start_time: datetime = Field(..., description="Start time of the slot (UTC)")
    end_time: datetime = Field(..., description="End time of the slot (UTC)")
    carbon_intensity: int = Field(..., description="Average carbon intensity for the slot (gCO2/kWh)")
    carbon_index: CarbonIndex = Field(..., description="Carbon intensity category")


class SchedulingMetadata(BaseModel):
    """Metadata about the scheduling process."""
    periods_analyzed: int = Field(..., description="Number of time periods analyzed")
    forecast_confidence: str = Field(..., description="Confidence level in the forecast")
    cached_data_age_minutes: int = Field(..., description="Age of the cached data in minutes")


class JobScheduleResponse(BaseModel):
    """Response model for job scheduling."""
    optimal_start_time: datetime = Field(..., description="Optimal start time for the job (UTC)")
    optimal_end_time: datetime = Field(..., description="Optimal end time for the job (UTC)")
    carbon_intensity: int = Field(..., description="Average carbon intensity for the optimal slot (gCO2/kWh)")
    carbon_index: CarbonIndex = Field(..., description="Carbon intensity category")
    alternative_slots: List[TimeSlot] = Field(
        ..., 
        description="Alternative time slots sorted by carbon intensity"
    )
    scheduling_metadata: SchedulingMetadata = Field(
        ...,
        description="Metadata about the scheduling process"
    )