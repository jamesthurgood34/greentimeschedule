"""API routes for health checks."""

from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Health check endpoint.

    This endpoint returns the current status of the API and can be used
    for monitoring and health checks.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
    }
