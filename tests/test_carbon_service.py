"""Tests for the carbon intensity service."""

import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock


from app.services.carbon_service import CarbonIntensityService
from app.utils.exceptions import CarbonAPIUnavailableError, CarbonAPIResponseError


@pytest.fixture()
def carbon_service_with_cache():
    """Fixture for the carbon intensity service."""
    # ensure cache is cleared before each test
    return CarbonIntensityService(use_cache=True)


@pytest.fixture()
def carbon_service_no_cache():
    """Fixture for the carbon intensity service."""
    # ensure cache is cleared before each test
    return CarbonIntensityService(use_cache=False)


@pytest.fixture
def mock_carbon_api_response():
    """Fixture for mock Carbon Intensity API response."""
    return {
        "data": [
            {
                "from": "2024-06-20T14:00Z",
                "to": "2024-06-20T14:30Z",
                "intensity": {"forecast": 120, "actual": 115, "index": "low"},
            }
        ]
    }


@pytest.fixture
def mock_carbon_api_error_response():
    """Fixture for mock Carbon Intensity API error response."""
    return {"error": {"code": "400 Bad Request", "message": "Invalid date format"}}


@pytest.mark.asyncio
async def test_get_intensity_for_period_success(
    carbon_service_with_cache, mock_carbon_api_response
):
    """Test successful retrieval of carbon intensity for a specific period."""
    # Setup
    date_str = "2024-06-20"
    period = 29  # 14:00-14:30

    # Mock httpx client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_carbon_api_response

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response)):
        # Execute
        result = await carbon_service_with_cache.get_intensity_for_period(
            date_str, period
        )

        # Verify
        assert result is not None
        assert result.period == period
        assert result.intensity_forecast == 120
        assert result.intensity_actual == 115
        assert result.intensity_index == "low"


@pytest.mark.asyncio
async def test_get_intensity_for_period_api_error(
    carbon_service_with_cache, mock_carbon_api_error_response
):
    """Test handling of API errors when getting intensity for a period."""
    # Setup
    date_str = "invalid-date"
    period = 29

    # Mock httpx client with error response
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = mock_carbon_api_error_response

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response)):
        # Execute and verify
        with pytest.raises(CarbonAPIResponseError):
            await carbon_service_with_cache.get_intensity_for_period(date_str, period)


@pytest.mark.asyncio
async def test_get_intensity_for_period_api_unavailable(carbon_service_no_cache):
    """Test handling of API unavailability when getting intensity for a period."""
    # Setup
    date_str = "2024-06-20"
    period = 29

    # Mock httpx client with connection error
    with patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(side_effect=httpx.RequestError("Connection error")),
    ):
        # Execute and verify
        with pytest.raises(CarbonAPIUnavailableError):
            await carbon_service_no_cache.get_intensity_for_period(date_str, period)


@pytest.mark.asyncio
async def test_get_intensity_for_date_success(carbon_service_with_cache):
    """Test successful retrieval of carbon intensity for a full day."""
    # Setup
    date_str = "2024-06-20"

    # Mock response with multiple periods
    mock_response = {
        "data": [
            {
                "from": "2024-06-20T00:00Z",
                "to": "2024-06-20T00:30Z",
                "intensity": {"forecast": 200, "actual": 195, "index": "moderate"},
            },
            {
                "from": "2024-06-20T00:30Z",
                "to": "2024-06-20T01:00Z",
                "intensity": {"forecast": 190, "actual": 185, "index": "moderate"},
            },
            # Add more periods as needed
        ]
    }

    # Mock httpx client
    mock_response_obj = MagicMock()
    mock_response_obj.status_code = 200
    mock_response_obj.json.return_value = mock_response

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response_obj)):
        # Execute
        result = await carbon_service_with_cache.get_intensity_for_date(date_str)

        # Verify
        assert result is not None
        assert result.date == date_str
        assert len(result.forecast_periods) == 2  # Based on our mock data
        assert result.forecast_periods[0].intensity_forecast == 200
        assert result.forecast_periods[1].intensity_forecast == 190


@pytest.mark.asyncio
async def test_get_intensity_for_date_range(carbon_service_with_cache):
    """Test retrieval of carbon intensity for a date range."""
    # Setup
    start_date = "2024-06-20"
    end_date = "2024-06-21"

    # Mock the get_intensity_for_date method
    with patch.object(
        carbon_service_with_cache,
        "get_intensity_for_date",
        new=AsyncMock(return_value=MagicMock()),
    ) as mock_get_for_date:
        # Execute
        result = await carbon_service_with_cache.get_intensity_for_date_range(
            start_date, end_date
        )

        # Verify
        assert result is not None
        assert isinstance(result, dict)
        # Should have called get_intensity_for_date twice (for each date)
        assert mock_get_for_date.call_count == 2
        mock_get_for_date.assert_any_call(start_date)
        mock_get_for_date.assert_any_call(end_date)


@pytest.mark.asyncio
async def test_caching(carbon_service_with_cache, mock_carbon_api_response):
    """Test that caching works correctly."""
    # Setup
    date_str = "2024-06-20"
    period = 29

    # Mock cache service
    mock_cache = MagicMock()
    mock_cache.get = AsyncMock(return_value=None)  # First call: cache miss
    mock_cache.set = AsyncMock(return_value=True)

    # Mock httpx client
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_carbon_api_response

    with (
        patch("app.services.carbon_service.cache_service", mock_cache),
        patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_response)),
    ):
        # First call - should hit the API
        await carbon_service_with_cache.get_intensity_for_period(date_str, period)

        # Verify cache was checked and then set
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()

        # Reset mocks
        mock_cache.get.reset_mock()
        mock_cache.set.reset_mock()

        # Setup cache hit for second call
        cached_data = {"forecast": 120, "actual": 115, "index": "low"}
        mock_cache.get = AsyncMock(return_value=cached_data)

        # Second call - should use cache
        result = await carbon_service_with_cache.get_intensity_for_period(
            date_str, period
        )

        # Verify cache was checked but not set (since we had a hit)
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_not_called()

        # Verify result uses cached data
        assert result.intensity_forecast == 120
        assert result.intensity_actual == 115
        assert result.intensity_index == "low"
