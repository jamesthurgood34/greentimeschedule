"""Service for scheduling batch jobs during periods of low carbon intensity."""

import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional

from app.config import settings
from app.models.scheduling import (
    JobScheduleRequest, 
    JobScheduleResponse,
    TimeSlot,
    SchedulingMetadata,
)
from app.models.carbon import CarbonIndex
from app.services.carbon_service import carbon_service
from app.utils.exceptions import (
    InvalidScheduleRequestError,
    NoViableTimeSlotError,
)
from app.utils.time_utils import (
    get_date_periods_between,
    generate_time_windows,
)

logger = logging.getLogger(__name__)


class ScheduleService:
    """Service for scheduling batch jobs during periods of low carbon intensity."""
    
    async def schedule_job(self, request: JobScheduleRequest) -> JobScheduleResponse:
        """
        Schedule a job to run during periods of low carbon intensity.
        
        Args:
            request: The job scheduling request
            
        Returns:
            JobScheduleResponse with optimal time slot and alternatives
            
        Raises:
            InvalidScheduleRequestError: If the request is invalid
            NoViableTimeSlotError: If no viable time slot can be found
        """
        # Validate the request
        self._validate_request(request)
        
        # Calculate the earliest start time (now) and latest end time (deadline)
        now = datetime.utcnow()
        deadline = request.deadline_utc
        job_duration = timedelta(minutes=request.job_duration_minutes)
        
        # Ensure the job can fit before the deadline
        if now + job_duration > deadline:
            raise InvalidScheduleRequestError(
                f"Job duration ({request.job_duration_minutes} minutes) exceeds available time before deadline"
            )
        
        # Generate all possible time windows for the job
        time_windows = generate_time_windows(
            start_dt=now,
            end_dt=deadline,
            window_minutes=request.job_duration_minutes
        )
        
        if not time_windows:
            raise NoViableTimeSlotError("No viable time slots found for the job")
        
        # Get carbon intensity data for all relevant periods
        carbon_data = await self._get_carbon_data_for_windows(time_windows)
        
        # Calculate average carbon intensity for each window
        window_intensities = []
        for start_time, end_time in time_windows:
            avg_intensity = self._calculate_window_intensity(start_time, end_time, carbon_data)
            window_intensities.append((start_time, end_time, avg_intensity))
        
        # Sort windows by carbon intensity (lowest first)
        window_intensities.sort(key=lambda x: x[2])
        
        # Select optimal and alternative slots
        optimal_window = window_intensities[0]
        alternative_windows = window_intensities[1:settings.MAX_ALTERNATIVE_SLOTS+1]
        
        # Calculate metadata
        periods_analyzed = sum(len(periods) for periods in carbon_data.values())
        cached_data_age = self._calculate_cached_data_age(carbon_data)
        
        # Prepare the response
        return JobScheduleResponse(
            optimal_start_time=optimal_window[0],
            optimal_end_time=optimal_window[1],
            carbon_intensity=optimal_window[2],
            carbon_index=self._get_carbon_index(optimal_window[2]),
            alternative_slots=[
                TimeSlot(
                    start_time=start,
                    end_time=end,
                    carbon_intensity=intensity,
                    carbon_index=self._get_carbon_index(intensity)
                )
                for start, end, intensity in alternative_windows
            ],
            scheduling_metadata=SchedulingMetadata(
                periods_analyzed=periods_analyzed,
                forecast_confidence=self._get_forecast_confidence(optimal_window[0]),
                cached_data_age_minutes=cached_data_age
            )
        )
    
    def _validate_request(self, request: JobScheduleRequest) -> None:
        """
        Validate a job scheduling request.
        
        Args:
            request: The job scheduling request
            
        Raises:
            InvalidScheduleRequestError: If the request is invalid
        """
        # Check job duration
        if request.job_duration_minutes < settings.MIN_JOB_DURATION_MINUTES:
            raise InvalidScheduleRequestError(
                f"Job duration must be at least {settings.MIN_JOB_DURATION_MINUTES} minutes"
            )
        
        if request.job_duration_minutes > settings.MAX_JOB_DURATION_MINUTES:
            raise InvalidScheduleRequestError(
                f"Job duration cannot exceed {settings.MAX_JOB_DURATION_MINUTES} minutes"
            )
        
        # Check deadline
        if request.deadline_utc <= datetime.utcnow():
            raise InvalidScheduleRequestError("Deadline must be in the future")
    
    async def _get_carbon_data_for_windows(
        self, 
        windows: List[Tuple[datetime, datetime]]
    ) -> Dict[str, List[Dict]]:
        """
        Get carbon intensity data for all time windows.
        
        Args:
            windows: List of (start_time, end_time) tuples
            
        Returns:
            Dictionary mapping date strings to lists of carbon intensity data
        """
        # Find the earliest start and latest end dates
        start_date = min(window[0] for window in windows).date()
        end_date = max(window[1] for window in windows).date()
        
        # Convert to string format
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # Get forecasts for the date range
        forecasts = await carbon_service.get_intensity_for_date_range(
            start_date_str, 
            end_date_str
        )
        
        # Organize by date for easier lookup
        result = {}
        for date_str, forecast in forecasts.items():
            result[date_str] = [
                {
                    "period": p.period,
                    "start_time": p.start_time,
                    "end_time": p.end_time,
                    "intensity": p.intensity_forecast,
                    "index": p.intensity_index
                }
                for p in forecast.forecast_periods
            ]
        
        return result
    
    def _calculate_window_intensity(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        carbon_data: Dict[str, List[Dict]]
    ) -> int:
        """
        Calculate the average carbon intensity for a time window.
        
        Args:
            start_time: Start time of the window
            end_time: End time of the window
            carbon_data: Dictionary of carbon intensity data
            
        Returns:
            Average carbon intensity for the window (gCO2/kWh)
        """
        # Get all periods that overlap with the window
        date_periods = get_date_periods_between(start_time, end_time)
        
        total_intensity = 0
        period_count = 0
        
        for date_str, periods in date_periods.items():
            if date_str not in carbon_data:
                continue
            
            date_carbon_data = carbon_data[date_str]
            
            # Map periods to their data for easy lookup
            period_map = {p["period"]: p for p in date_carbon_data}
            
            for period in periods:
                if period in period_map:
                    total_intensity += period_map[period]["intensity"]
                    period_count += 1
        
        if period_count == 0:
            raise NoViableTimeSlotError()
        
        return total_intensity // period_count
    
    def _get_carbon_index(self, intensity: int) -> CarbonIndex:
        """
        Convert a carbon intensity value to a category index.
        
        Args:
            intensity: Carbon intensity in gCO2/kWh
            
        Returns:
            CarbonIndex category
        """
        if intensity <= 100:
            return CarbonIndex.VERY_LOW
        elif intensity <= 150:
            return CarbonIndex.LOW
        elif intensity <= 250:
            return CarbonIndex.MODERATE
        elif intensity <= 350:
            return CarbonIndex.HIGH
        else:
            return CarbonIndex.VERY_HIGH
    
    def _get_forecast_confidence(self, start_time: datetime) -> str:
        """
        Determine confidence level in the forecast based on how far in the future it is.
        
        Args:
            start_time: Start time of the job
            
        Returns:
            Confidence level string (high, medium, low)
        """
        hours_in_future = (start_time - datetime.utcnow()).total_seconds() / 3600
        
        if hours_in_future <= 12:
            return "high"
        elif hours_in_future <= 24:
            return "medium"
        else:
            return "low"
    
    def _calculate_cached_data_age(self, carbon_data: Dict[str, List[Dict]]) -> int:
        """
        Calculate the age of the cached carbon data in minutes.
        
        Args:
            carbon_data: Dictionary of carbon intensity data
            
        Returns:
            Age of the data in minutes
        """
        # For now, we'll just return a default value
        # In a real implementation, we would track when the data was fetched
        return 15


# Create a global instance of the schedule service
schedule_service = ScheduleService()