"""Tests for the schedule service."""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, AsyncMock

from app.models.scheduling import JobScheduleRequest, Priority
from app.models.carbon import CarbonIndex
from app.services.schedule_service import ScheduleService
from app.utils.exceptions import InvalidScheduleRequestError


@pytest.fixture
def schedule_service():
    """Fixture for the schedule service."""
    return ScheduleService()


@pytest.fixture
def mock_carbon_data():
    """Fixture for mock carbon intensity data."""
    from app.models.carbon import CarbonForecast, CarbonIntensityPeriod

    # Get current date and next day for testing
    now = datetime.now(UTC)
    today_date = now.date()
    tomorrow_date = (now + timedelta(days=1)).date()

    today_str = today_date.strftime("%Y-%m-%d")
    tomorrow_str = tomorrow_date.strftime("%Y-%m-%d")

    # Create proper CarbonForecast objects with forecast_periods
    today_periods = [
        CarbonIntensityPeriod(
            period=1,
            start_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            ),
            end_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(minutes=30),
            intensity_forecast=200,
            intensity_index=CarbonIndex.MODERATE,
        ),
        CarbonIntensityPeriod(
            period=2,
            start_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(minutes=30),
            end_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(minutes=60),
            intensity_forecast=180,
            intensity_index=CarbonIndex.LOW,
        ),
        CarbonIntensityPeriod(
            period=29,
            start_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(hours=14),
            end_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(hours=14, minutes=30),
            intensity_forecast=120,
            intensity_index=CarbonIndex.LOW,
        ),
        CarbonIntensityPeriod(
            period=30,
            start_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(hours=14, minutes=30),
            end_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(hours=15),
            intensity_forecast=110,
            intensity_index=CarbonIndex.LOW,
        ),
        CarbonIntensityPeriod(
            period=31,
            start_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(hours=15),
            end_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(hours=15, minutes=30),
            intensity_forecast=100,
            intensity_index=CarbonIndex.VERY_LOW,
        ),
        CarbonIntensityPeriod(
            period=32,
            start_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(hours=15, minutes=30),
            end_time=datetime.combine(
                today_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(hours=16),
            intensity_forecast=105,
            intensity_index=CarbonIndex.LOW,
        ),
    ]

    tomorrow_periods = [
        CarbonIntensityPeriod(
            period=1,
            start_time=datetime.combine(
                tomorrow_date, datetime.min.time().replace(tzinfo=UTC)
            ),
            end_time=datetime.combine(
                tomorrow_date, datetime.min.time().replace(tzinfo=UTC)
            )
            + timedelta(minutes=30),
            intensity_forecast=150,
            intensity_index=CarbonIndex.LOW,
        ),
    ]

    return {
        today_str: CarbonForecast(
            date=today_str,
            forecast_periods=today_periods,
            data_freshness=datetime.now(UTC),
        ),
        tomorrow_str: CarbonForecast(
            date=tomorrow_str,
            forecast_periods=tomorrow_periods,
            data_freshness=datetime.now(UTC),
        ),
    }


@pytest.mark.asyncio
async def test_schedule_job_success(schedule_service, mock_carbon_data):
    """Test successful job scheduling."""
    # Setup
    now = datetime.now(UTC)
    deadline = now + timedelta(days=1)

    request = JobScheduleRequest(
        job_duration_minutes=60,
        deadline_utc=deadline,
        job_name="test-job",
        priority=Priority.LOW,
    )

    # Mock the carbon service and time utils to properly match periods
    with (
        patch("app.services.schedule_service.carbon_service") as mock_carbon_service,
        patch(
            "app.services.schedule_service.get_date_periods_between"
        ) as mock_date_periods,
    ):
        # Set up mock for carbon service
        mock_carbon_service.get_intensity_for_date_range = AsyncMock()
        mock_carbon_service.get_intensity_for_date_range.return_value = mock_carbon_data

        # Mock _get_carbon_data_for_windows to return the exact format expected by _calculate_window_intensity
        with patch.object(
            schedule_service, "_get_carbon_data_for_windows"
        ) as mock_get_carbon_data:
            today_str = datetime.now(UTC).date().strftime("%Y-%m-%d")

            # Set up the carbon data in the exact format expected by _calculate_window_intensity
            processed_carbon_data = {
                today_str: [
                    {
                        "period": 1,
                        "start_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        ),
                        "end_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(minutes=30),
                        "intensity": 120,
                        "index": CarbonIndex.LOW,
                    },
                    {
                        "period": 2,
                        "start_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(minutes=30),
                        "end_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(minutes=60),
                        "intensity": 110,
                        "index": CarbonIndex.LOW,
                    },
                    {
                        "period": 29,
                        "start_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(hours=14),
                        "end_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(hours=14, minutes=30),
                        "intensity": 100,
                        "index": CarbonIndex.VERY_LOW,
                    },
                    {
                        "period": 30,
                        "start_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(hours=14, minutes=30),
                        "end_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(hours=15),
                        "intensity": 105,
                        "index": CarbonIndex.LOW,
                    },
                    {
                        "period": 31,
                        "start_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(hours=15),
                        "end_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(hours=15, minutes=30),
                        "intensity": 95,
                        "index": CarbonIndex.VERY_LOW,
                    },
                    {
                        "period": 32,
                        "start_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(hours=15, minutes=30),
                        "end_time": datetime.combine(
                            datetime.now(UTC).date(),
                            datetime.min.time().replace(tzinfo=UTC),
                        )
                        + timedelta(hours=16),
                        "intensity": 100,
                        "index": CarbonIndex.VERY_LOW,
                    },
                ]
            }

            # Set up the mock to return our processed data
            mock_get_carbon_data.return_value = processed_carbon_data

            # Set up mock for date periods - ensure we return periods that match our mock data
            mock_date_periods.return_value = {
                today_str: [
                    1,
                    2,
                    29,
                    30,
                    31,
                    32,
                ]  # These match the periods in our processed data
            }

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
    from pydantic import ValidationError

    # Test the Pydantic validation first
    now = datetime.now(UTC)
    deadline = now + timedelta(days=1)

    # Verify Pydantic validation for too short duration
    with pytest.raises(ValidationError) as exc_info:
        JobScheduleRequest(
            job_duration_minutes=10,  # Too short (min is 30)
            deadline_utc=deadline,
            job_name="test-job",
            priority=Priority.LOW,
        )
    assert "job_duration_minutes" in str(exc_info.value)
    assert "greater than or equal to 30" in str(exc_info.value)

    # Create a valid request object first, then modify it to bypass Pydantic validation
    valid_request = JobScheduleRequest(
        job_duration_minutes=30,  # Valid value
        deadline_utc=deadline,
        job_name="test-job",
        priority=Priority.LOW,
    )

    # Now modify the valid object to have an invalid duration
    valid_request.job_duration_minutes = (
        10  # Too short, should be caught by service validation
    )

    # Execute and verify service validation
    with pytest.raises(InvalidScheduleRequestError):
        await schedule_service.schedule_job(valid_request)

    # Test too long duration
    # First create a valid request, then modify it
    valid_request = JobScheduleRequest(
        job_duration_minutes=60,
        deadline_utc=deadline,
        job_name="test-job",
        priority=Priority.LOW,
    )

    # Now modify to have an invalid duration that's too long
    valid_request.job_duration_minutes = (
        2000  # Too long, should be caught by service validation
    )

    # Execute and verify service validation
    with pytest.raises(InvalidScheduleRequestError):
        await schedule_service.schedule_job(valid_request)


@pytest.mark.asyncio
async def test_schedule_job_deadline_in_past(schedule_service):
    """Test job scheduling with deadline in the past."""
    # Setup
    now = datetime.now(UTC)
    deadline = now - timedelta(hours=1)  # In the past

    request = JobScheduleRequest(
        job_duration_minutes=60,
        deadline_utc=deadline,
        job_name="test-job",
        priority=Priority.LOW,
    )

    # Execute and verify
    with pytest.raises(InvalidScheduleRequestError):
        await schedule_service.schedule_job(request)


@pytest.mark.asyncio
async def test_schedule_job_not_enough_time(schedule_service):
    """Test job scheduling when there's not enough time before deadline."""
    # Setup
    now = datetime.now(UTC)
    deadline = now + timedelta(minutes=20)  # Not enough time for a 30-min job

    request = JobScheduleRequest(
        job_duration_minutes=30,
        deadline_utc=deadline,
        job_name="test-job",
        priority=Priority.LOW,
    )

    # Execute and verify
    with pytest.raises(InvalidScheduleRequestError):
        await schedule_service.schedule_job(request)
