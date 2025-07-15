"""API routes for job scheduling."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional

from app.models.scheduling import JobScheduleRequest, JobScheduleResponse
from app.services.schedule_service import schedule_service
from app.utils.exceptions import (
    InvalidScheduleRequestError,
    NoViableTimeSlotError,
    CarbonAPIUnavailableError,
    CarbonAPIResponseError,
)

router = APIRouter(prefix="/schedule", tags=["scheduling"])


@router.post("/job", response_model=JobScheduleResponse)
async def schedule_job(request: JobScheduleRequest):
    """
    Schedule a job to run during periods of low carbon intensity.
    
    This endpoint will analyze carbon intensity forecasts and find the optimal
    time slot for running a batch job with the specified duration, before the
    given deadline. It will return the optimal start time and a list of alternative
    time slots.
    """
    try:
        return await schedule_service.schedule_job(request)
    except InvalidScheduleRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NoViableTimeSlotError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CarbonAPIUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except CarbonAPIResponseError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        # Log unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")