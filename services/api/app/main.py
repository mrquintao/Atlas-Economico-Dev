from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.errors import register_error_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    app = FastAPI(
        title="Atlas Econômico Brasileiro — API",
        version="0.1.0",
        description=(
            "API interna com séries históricas de indicadores econômicos brasileiros coletadas "
            "de fontes oficiais. Todas as datas em ISO 8601; valores acompanhados de unidade."
        ),
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    # State boundaries are ~100 KB of JSON (~28 KB compressed).
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
