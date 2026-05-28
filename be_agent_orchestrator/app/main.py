from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.logging import configure_logging
from app.core.middleware import AccessLogMiddleware, RequestIdMiddleware
from app.core.openapi import customize_openapi


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Dev-only HTTP access log. Registered before RequestIdMiddleware so the
    # request id is in context when the access line is emitted. Starlette
    # runs middlewares in reverse-registration order, so AccessLog ends up
    # outside RequestId at request time.
    if settings.environment == "local":
        app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)
    customize_openapi(app)

    app.include_router(api_router, prefix="/api")

    @app.get(
        "/health",
        tags=["meta"],
        summary="Liveness probe",
        description="Returns 200 if the API process is up. No auth required.",
        operation_id="meta_get_health",
    )
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
