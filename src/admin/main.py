"""
FastAPI Admin Panel entrypoint.

اجرا (dev): uvicorn src.admin.main:app --reload --port 8000
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from src.admin.routers import get_root_router
from src.core.config import get_settings
from src.core.exceptions import GreenVitaError
from src.core.logging import configure_logging, get_logger

logger = get_logger("admin.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    settings = get_settings()
    logger.info("admin_starting", app_env=settings.app_env, ai_provider=settings.ai_provider)
    yield
    logger.info("admin_stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="پنل مدیریت کلینیک گیاه‌پزشکی گرین‌ویتا",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.admin_session_secret,
        session_cookie="green_vita_admin_session",
        max_age=60 * 60 * 8,
        same_site="lax",
        https_only=False,
    )

    app.mount("/static", StaticFiles(directory="src/admin/static"), name="static")
    app.include_router(get_root_router())

    @app.exception_handler(GreenVitaError)
    async def app_error_handler(request: Request, exc: GreenVitaError) -> JSONResponse:
        logger.warning("app_error", path=str(request.url), code=exc.code, message=exc.message)
        return JSONResponse(status_code=400, content={"error": exc.code, "message": exc.message})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error", path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "خطای داخلی سرور رخ داد."},
        )

    return app


app = create_app()
