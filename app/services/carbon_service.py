"""Service for interacting with the Carbon Intensity API."""

import logging
import httpx
from datetime import UTC, datetime, timedelta
from typing import Dict

from app.config import settings
from app.models.carbon import CarbonIntensityPeriod, CarbonForecast
from app.services.cache_service import cache_service
from app.utils.exceptions import (
    CarbonAPIUnavailableError,
    CarbonAPIResponseError,
)
from app.utils.time_utils import (
    get_settlement_period,
    datetime_from_period,
)

logger = logging.getLogger(__name__)


class CarbonIntensityService:
    """Service for fetching and processing carbon intensity data."""

    def __init__(self, use_cache=True):
        """Initialize the carbon intensity service."""
        self.base_url = settings.CARBON_INTENSITY_API_URL
        self.timeout = settings.CARBON_INTENSITY_TIMEOUT
        self.use_cache = use_cache

    async def get_cache(self, cache_key) -> str | None:
        """
        Retrieve data from cache if available and caching is enabled.

        Args:
            cache_key: The key to look up in the cache

        Returns:
            Cached data if available, None otherwise
        """
        if self.use_cache:
            return await cache_service.get(cache_key)
        else:
            return None

    async def get_intensity_for_period(
        self, date_str: str, period: int
    ) -> CarbonIntensityPeriod:
        """
        Get carbon intensity data for a specific date and period.

        Args:
            date_str: Date in YYYY-MM-DD format
            period: Settlement period (1-48)

        Returns:
            CarbonIntensityPeriod object

        Raises:
            CarbonAPIUnavailableError: If the Carbon API is unavailable
            CarbonAPIResponseError: If the response is invalid
        """
        cache_key = cache_service.get_carbon_forecast_key(date_str, [period])
        cached_data = await self.get_cache(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for {cache_key}")
            start_time, end_time = datetime_from_period(date_str, period)
            return CarbonIntensityPeriod(
                period=period,
                start_time=start_time,
                end_time=end_time,
                intensity_forecast=cached_data["forecast"],
                intensity_actual=cached_data.get("actual"),
                intensity_index=cached_data["index"],
            )

        # Fetch from API
        url = f"{self.base_url}/intensity/date/{date_str}/{period}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, timeout=self.timeout, headers={"Accept": "application/json"}
                )

                if response.status_code != 200:
                    error_msg = f"Carbon API returned status {response.status_code}"
                    logger.error(error_msg)
                    raise CarbonAPIResponseError(error_msg, response.status_code)

                data = response.json()

                if "error" in data:
                    error_msg = f"Carbon API error: {data['error']['message']}"
                    logger.error(error_msg)
                    raise CarbonAPIResponseError(error_msg)

                if (
                    not data.get("data")
                    or not isinstance(data["data"], list)
                    or len(data["data"]) == 0
                ):
                    error_msg = "Invalid data format from Carbon API"
                    logger.error(error_msg)
                    raise CarbonAPIResponseError(error_msg)

                # Process the response
                period_data = data["data"][0]
                start_time = datetime.fromisoformat(
                    period_data["from"].replace("Z", "+00:00")
                )
                end_time = datetime.fromisoformat(
                    period_data["to"].replace("Z", "+00:00")
                )

                intensity_data = period_data["intensity"]
                forecast = intensity_data["forecast"]
                actual = intensity_data.get("actual")
                index = intensity_data["index"]

                # Cache the data
                await cache_service.set(
                    cache_key, {"forecast": forecast, "actual": actual, "index": index}
                )

                return CarbonIntensityPeriod(
                    period=period,
                    start_time=start_time,
                    end_time=end_time,
                    intensity_forecast=forecast,
                    intensity_actual=actual,
                    intensity_index=index,
                )

        except httpx.TimeoutException:
            error_msg = "Carbon API request timed out"
            logger.error(error_msg)
            raise CarbonAPIUnavailableError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Carbon API request failed: {str(e)}"
            logger.error(error_msg)
            raise CarbonAPIUnavailableError(error_msg)

    async def get_intensity_for_date(self, date_str: str) -> CarbonForecast:
        """
        Get carbon intensity forecast for an entire day.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            CarbonForecast object

        Raises:
            CarbonAPIUnavailableError: If the Carbon API is unavailable
            CarbonAPIResponseError: If the response is invalid
        """
        # Check cache first
        cache_key = cache_service.get_carbon_forecast_key(date_str)
        cached_data = await self.get_cache(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for {cache_key}")
            return CarbonForecast(
                date=date_str,
                forecast_periods=[
                    CarbonIntensityPeriod(**period_data)
                    for period_data in cached_data["periods"]
                ],
                data_freshness=datetime.fromisoformat(cached_data["freshness"]),
            )

        # Fetch from API
        url = f"{self.base_url}/intensity/date/{date_str}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, timeout=self.timeout, headers={"Accept": "application/json"}
                )

                if response.status_code != 200:
                    error_msg = f"Carbon API returned status {response.status_code}"
                    logger.error(error_msg)
                    raise CarbonAPIResponseError(error_msg, response.status_code)

                data = response.json()

                if "error" in data:
                    error_msg = f"Carbon API error: {data['error']['message']}"
                    logger.error(error_msg)
                    raise CarbonAPIResponseError(error_msg)

                if (
                    not data.get("data")
                    or not isinstance(data["data"], list)
                    or len(data["data"]) == 0
                ):
                    error_msg = "Invalid data format from Carbon API"
                    logger.error(error_msg)
                    raise CarbonAPIResponseError(error_msg)

                # Process the response
                periods = []
                for period_data in data["data"]:
                    start_time = datetime.fromisoformat(
                        period_data["from"].replace("Z", "+00:00")
                    )
                    end_time = datetime.fromisoformat(
                        period_data["to"].replace("Z", "+00:00")
                    )
                    period = get_settlement_period(start_time)

                    intensity_data = period_data["intensity"]
                    forecast = intensity_data["forecast"]
                    actual = intensity_data.get("actual")
                    index = intensity_data["index"]

                    periods.append(
                        CarbonIntensityPeriod(
                            period=period,
                            start_time=start_time,
                            end_time=end_time,
                            intensity_forecast=forecast,
                            intensity_actual=actual,
                            intensity_index=index,
                        )
                    )

                # Sort periods by period number
                periods.sort(key=lambda p: p.period)

                # Create the forecast object
                now = datetime.now(UTC)
                forecast = CarbonForecast(
                    date=date_str, forecast_periods=periods, data_freshness=now
                )

                # Cache the data
                await cache_service.set(
                    cache_key,
                    {
                        "periods": [p.model_dump() for p in periods],
                        "freshness": now.isoformat(),
                    },
                )

                return forecast

        except httpx.TimeoutException:
            error_msg = "Carbon API request timed out"
            logger.error(error_msg)
            raise CarbonAPIUnavailableError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Carbon API request failed: {str(e)}"
            logger.error(error_msg)
            raise CarbonAPIUnavailableError(error_msg)

    async def get_intensity_for_date_range(
        self, start_date: str, end_date: str
    ) -> Dict[str, CarbonForecast]:
        """
        Get carbon intensity forecasts for a range of dates.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary mapping date strings to CarbonForecast objects

        Raises:
            CarbonAPIUnavailableError: If the Carbon API is unavailable
            CarbonAPIResponseError: If the response is invalid
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        if start_dt > end_dt:
            start_dt, end_dt = end_dt, start_dt

        # Limit to maximum forecast days
        max_days = settings.MAX_FORECAST_DAYS
        if (end_dt - start_dt).days > max_days:
            end_dt = start_dt + timedelta(days=max_days)

        result = {}
        current_dt = start_dt

        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            forecast = await self.get_intensity_for_date(date_str)
            result[date_str] = forecast
            current_dt += timedelta(days=1)

        return result


# Create a global instance of the carbon intensity service
carbon_service = CarbonIntensityService()
