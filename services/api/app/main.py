from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_v1_router
from app.api.v1.chat import router as chat_v1_router
from app.api.v1.contact import router as contact_v1_router
from app.api.v1.developer import developer_router, dev_programmatic_router
from app.api.v1.documents import router as documents_v1_router
from app.api.v1.health import router as health_v1_router, get_health
from app.api.v1.projects import router as projects_v1_router
from app.api.v1.study import router as study_v1_router
from app.core.config import settings
from app.core.errors import AppError, app_error_handler, generic_exception_handler
from app.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.DEBUG)
    logger.info("Starting StudySpace AI API service [%s mode]", settings.APP_ENV)
    yield
    logger.info("Shutting down StudySpace AI API service")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="StudySpace AI backend API for academic document intelligence.",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=settings.CORS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Root health endpoint for container / load balancer probes
    app.add_api_route("/health", get_health, methods=["GET"], tags=["Health"])

    # Versioned API routes
    app.include_router(health_v1_router, prefix=settings.API_PREFIX)
    app.include_router(auth_v1_router, prefix=settings.API_PREFIX)
    app.include_router(projects_v1_router, prefix=settings.API_PREFIX)
    app.include_router(documents_v1_router, prefix=settings.API_PREFIX)
    app.include_router(chat_v1_router, prefix=settings.API_PREFIX)
    app.include_router(study_v1_router, prefix=settings.API_PREFIX)
    app.include_router(contact_v1_router, prefix=settings.API_PREFIX)
    app.include_router(developer_router, prefix=settings.API_PREFIX)
    app.include_router(dev_programmatic_router, prefix=settings.API_PREFIX)

    return app


app = create_app()
