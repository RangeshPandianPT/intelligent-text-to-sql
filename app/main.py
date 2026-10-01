"""
SDE-SQL FastAPI Application Entry Point
"""

import logging
from fastapi import FastAPI
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Returns service health status."""
    logger.info("Health check called")
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "model": settings.ollama_model,
        "database": settings.database_path,
    }

from app.api.routes import router as api_router
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
