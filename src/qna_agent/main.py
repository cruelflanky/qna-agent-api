import logging
import sys
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from qna_agent.config import get_settings
from qna_agent.database import close_db, get_db, init_db
from qna_agent.models.schemas import HealthResponse, ReadyResponse
from qna_agent.routers import chats_router, events_router, messages_router


def setup_logging() -> None:
    """Configure structured logging."""
    settings = get_settings()

    # Configure format based on environment
    if settings.log_format == "json":
        # JSON format for production (easier to parse in log aggregators)
        format_str = (
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        # Human-readable format for development
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=format_str,
        stream=sys.stdout,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger = logging.getLogger(__name__)

    # Startup
    setup_logging()
    logger.info("Starting application...")
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="QnA Agent API",
        description="Production-ready QnA agent API with OpenAI and local knowledge base",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware (configure for your needs)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(chats_router)
    app.include_router(messages_router)
    app.include_router(events_router)

    # Health endpoints
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["health"],
        summary="Liveness probe",
    )
    async def health() -> HealthResponse:
        """
        Liveness probe endpoint.

        Returns 200 if the application is running.
        Used by Kubernetes liveness probe.
        """
        return HealthResponse(status="healthy")

    @app.get(
        "/ready",
        response_model=ReadyResponse,
        tags=["health"],
        summary="Readiness probe",
        responses={
            200: {"description": "Service is ready"},
            503: {"description": "Service is not ready"},
        },
    )
    async def ready(
        response: Response,
        db: AsyncSession = Depends(get_db),
    ) -> ReadyResponse:
        """
        Readiness probe endpoint.

        Checks database connectivity.
        Used by Kubernetes readiness probe.
        """
        checks = {}

        # Check database
        try:
            await db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {str(e)}"

        # Determine overall status
        all_ok = all(v == "ok" for v in checks.values())

        if not all_ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return ReadyResponse(
            status="ready" if all_ok else "not_ready",
            checks=checks,
        )

    return app


# Create app instance
app = create_app()


# Entry point for uvicorn
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "qna_agent.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,  # Disable in production
    )
