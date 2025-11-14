"""
Main FastAPI application for Drone Search Segment Planning Tool.
"""
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import os

from app.api.routes import router as api_router
from app.version import VERSION, BUILD_DATE, get_version_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Drone Search Segment Planning Tool",
    description="Automatically divide search areas into optimal drone search segments",
    version=VERSION
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors with details."""
    errors = exc.errors()
    logger.error(f"Validation error on {request.method} {request.url}")
    logger.error(f"Request body: {await request.body()}")
    logger.error(f"Validation errors: {errors}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Version endpoint
@app.get("/api/v1/version")
async def get_version():
    """Get API version information."""
    return get_version_info()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Drone Search Segment Planning Tool",
        "version": VERSION,
        "build_date": BUILD_DATE
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Drone Search Segment Planning Tool API",
        "version": VERSION,
        "build_date": BUILD_DATE,
        "docs": "/docs",
        "health": "/health"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("=" * 80)
    logger.info(f"Starting Drone Search Segment Planning Tool API")
    logger.info(f"Version: {VERSION}")
    logger.info(f"Build Date: {BUILD_DATE}")
    logger.info("=" * 80)

    # Create required directories
    directories = [
        "/app/data/projects",
        "/app/data/dems",
        "/app/data/vegetation",
        "/app/data/roads",
        "/app/data/trails",
        "/app/exports"
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Drone Search Segment Planning Tool API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
