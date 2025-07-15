"""API routes for carbon intensity forecasts."""

from fastapi import APIRouter, HTTPException, Path, Query
from datetime import datetime, timedelta
from typing import Optional

from app.models.carbon import CarbonForecast
from app.services.carbon_service import carbon_service
from app.utils.exceptions import (
    CarbonAPIUnavailableError,
    CarbonAPIResponseError,
)

router = APIRouter(prefix="/carbon", tags=["carbon"])


@router.get("/forecast/{date}", response_model=CarbonForecast)
async def get_carbon_forecast(
    date: str = Path(..., description="Date in YYYY-MM-DD format"),
):
    """
    Get carbon intensity forecast for a specific date.
    
    This endpoint returns the carbon intensity forecast for all 48 half-hour
    periods in the specified date. This can be used to visualize the carbon
    intensity profile throughout the day.
    """
    try:
        return await carbon_service.get_intensity_for_date(date)
    except CarbonAPIUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except CarbonAPIResponseError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        # Log unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/forecast", response_model=dict)
async def get_carbon_forecast_range(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
):
    """
    Get carbon intensity forecasts for a range of dates.
    
    This endpoint returns carbon intensity forecasts for multiple days, which
    can be useful for longer-term planning. If end_date is not provided, only
    the start_date forecast will be returned.
    """
    if not end_date:
        # If end_date is not provided, use start_date
        end_date = start_date
    
    try:
        return await carbon_service.get_intensity_for_date_range(start_date, end_date)
    except CarbonAPIUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except CarbonAPIResponseError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        # Log unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")