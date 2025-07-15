"""Main application module for the Green Time Schedule API."""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
from app.config import settings
from app.routes import schedule, carbon, health
from app.utils.exceptions import GreenScheduleException

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for scheduling batch jobs during periods of low carbon intensity",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, you'd want to restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(schedule.router, prefix=settings.API_V1_PREFIX)
app.include_router(carbon.router, prefix=settings.API_V1_PREFIX)
app.include_router(health.router)


# Exception handlers
@app.exception_handler(GreenScheduleException)
async def green_schedule_exception_handler(
    request: Request, exc: GreenScheduleException
):
    """Handle Green Schedule-specific exceptions."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": str(exc)},
    )


@app.get("/")
async def root():
    """Root endpoint redirecting to docs."""
    return {
        "message": "Green Time Schedule API",
        "docs": "/api/docs",
        "version": "0.1.0",
    }


if __name__ == "__main__":
    # This is for development only. In production, use:
    # uvicorn app.main:app --host 0.0.0.0 --port 8000
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
