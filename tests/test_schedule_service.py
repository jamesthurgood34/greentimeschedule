"""Tests for the schedule service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.models.scheduling import JobScheduleRequest, Priority
from app.models.carbon import CarbonIndex
from app.services.schedule_service import ScheduleService
from app.utils.exceptions import InvalidScheduleRequestError, NoViableTimeSlotError


@pytest.fixture
def schedule_service():
    """Fixture for the schedule service."""
    return ScheduleService()


@pytest.fixture
def mock_carbon_data():
    """Fixture for mock carbon intensity data."""
    # Sample carbon data for 2 days with varying intensity levels
    return {
        "2024-06-20": [
            {
                "period": 1,
                "start_time": datetime(2024, 6, 20, 0, 0),
                "end_time": datetime(2024, 6, 20, 0, 30),
                "intensity": 200,
                "index": CarbonIndex.MODERATE
            },
            {
                "period": 2,
                "start_time": datetime(2024, 6, 20, 0, 30),
                "end_time": datetime(2024, 6, 20, 1, 0),
                "intensity": 180,
                "index": CarbonIndex.LOW
            },
            # Add more periods as needed
            {
                "period": 29,
                "start_time": datetime(2024, 6, 20, 14, 0),
                "end_time": datetime(2024, 6, 20, 14, 30),
                "intensity": 120,
                "index": CarbonIndex.LOW
            },
            {
                "period": 30,
                "start_time": datetime(2024, 6, 20, 14, 30),
                "end_time": datetime(2024, 6, 20, 15, 0),
                "intensity": 110,
                "index": CarbonIndex.LOW
            },
            {
                "period": 31,
                "start_time": datetime(2024, 6, 20, 15, 0),
                "end_time": datetime(2024, 6, 20, 15, 30),
                "intensity": 100,
                "index": CarbonIndex.VERY_LOW
            },
            {
                "period": 32,
                "start_time": datetime(2024, 6, 20, 15, 30),
                "end_time": datetime(2024, 6, 20, 16, 0),
                "intensity": 105,
                "index": CarbonIndex.LOW
            },
        ],
        "2024-06-21": [
            {
                "period": 1,
                "start_time": datetime(2024, 6, 21, 0, 0),
                "end_time": datetime(2024, 6, 21, 0, 30),
                "intensity": 150,
                "index": CarbonIndex.LOW
            },
            # Add more periods as needed
        ]
    }


@pytest.mark.asyncio
async def test_schedule_job_success(schedule_service, mock_carbon_data):
    """Test successful job scheduling."""
    # Setup
    now = datetime.utcnow()
    deadline = now + timedelta(days=1)
    
    request = JobScheduleRequest(
        job_duration_minutes=60,
        deadline_utc=deadline,
        job_name="test-job",
        priority=Priority.LOW
    )
    
    # Mock the carbon service
    with patch("app.services.schedule_service.carbon_service") as mock_carbon_service:
        mock_carbon_service.get_intensity_for_date_range.return_value = mock_carbon_data
        
        # Execute
        result = await schedule_service.schedule_job(request)
        
        # Verify
        assert result is not None
        assert result.optimal_start_time is not None
        assert result.optimal_end_time is not None
        # The optimal slot should be where carbon intensity is lowest
        assert result.carbon_intensity <= 150  # Based on our mock data


@pytest.mark.asyncio
async def test_schedule_job_invalid_duration(schedule_service):
    """Test job scheduling with invalid duration."""
    # Setup - duration too short
    now = datetime.utcnow()
    deadline = now + timedelta(days=1)
    
    request = JobScheduleRequest(
        job_duration_minutes=10,  # Too short (min is 30)
        deadline_utc=deadline,
        job_name="test-job",
        priority=Priority.LOW
    )
    
    # Execute and verify
    with pytest.raises(InvalidScheduleRequestError):
        await schedule_service.schedule_job(request)
    
    # Setup - duration too long
    request = JobScheduleRequest(
        job_duration_minutes=2000,  # Too long (max is 1440)
        deadline_utc=deadline,
        job_name="test-job",
        priority=Priority.LOW
    )
    
    # Execute and verify
    with pytest.raises(InvalidScheduleRequestError):
        await schedule_service.schedule_job(request)


@pytest.mark.asyncio
async def test_schedule_job_deadline_in_past(schedule_service):
    """Test job scheduling with deadline in the past."""
    # Setup
    now = datetime.utcnow()
    deadline = now - timedelta(hours=1)  # In the past
    
    request = JobScheduleRequest(
        job_duration_minutes=60,
        deadline_utc=deadline,
        job_name="test-job",
        priority=Priority.LOW
    )
    
    # Execute and verify
    with pytest.raises(InvalidScheduleRequestError):
        await schedule_service.schedule_job(request)


@pytest.mark.asyncio
async def test_schedule_job_not_enough_time(schedule_service):
    """Test job scheduling when there's not enough time before deadline."""
    # Setup
    now = datetime.utcnow()
    deadline = now + timedelta(minutes=20)  # Not enough time for a 30-min job
    
    request = JobScheduleRequest(
        job_duration_minutes=30,
        deadline_utc=deadline,
        job_name="test-job",
        priority=Priority.LOW
    )
    
    # Execute and verify
    with pytest.raises(InvalidScheduleRequestError):
        await schedule_service.schedule_job(request)