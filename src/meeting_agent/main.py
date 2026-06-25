"""FastAPI application factory with lifespan management."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from meeting_agent.api.router import api_router
from meeting_agent.core.config import settings
from meeting_agent.core.exceptions import MeetingAgentError
from meeting_agent.infrastructure.database.connection import engine
from meeting_agent.infrastructure.database.models import Base

logger = logging.getLogger(__name__)

# Directory holding the bundled web GUI (served as a static SPA).
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — startup and shutdown."""
    # Startup
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created.")

    # Start scheduler if enabled
    if settings.scheduler_enabled:
        try:
            from meeting_agent.workers.scheduler import start_scheduler

            await start_scheduler()
            logger.info("Scheduler started.")
        except Exception as e:
            logger.warning("Could not start scheduler: %s", e)

    yield

    # Shutdown
    logger.info("Shutting down %s...", settings.app_name)
    if settings.scheduler_enabled:
        try:
            from meeting_agent.workers.scheduler import shutdown_scheduler

            await shutdown_scheduler()
        except Exception:
            pass
    await engine.dispose()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI Meeting Agent — Automatically joins meetings, records audio, "
            "transcribes speech, generates summaries, extracts tasks, and emails participants."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(MeetingAgentError)
    async def meeting_agent_error_handler(request: Request, exc: MeetingAgentError):
        return JSONResponse(
            status_code=400,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    # Routes
    app.include_router(api_router)

    # Web GUI — served as a static SPA under /app so it never shadows /api, /docs, /redoc.
    if STATIC_DIR.is_dir():
        @app.get("/", include_in_schema=False)
        async def root_redirect():
            return RedirectResponse(url="/app/")

        app.mount("/app", StaticFiles(directory=str(STATIC_DIR), html=True), name="app-static")
    else:  # pragma: no cover - dev convenience warning
        logger.warning("Static GUI directory not found at %s — skipping web app mount.", STATIC_DIR)

    return app
