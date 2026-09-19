"""FastAPI application shell for deployment walking skeleton."""

from __future__ import annotations

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .database import check_database_connection
from .schemas import AnalysisRequest, AnalysisResponse
from .service import AnalysisEngine
from .settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Factory creating the FastAPI application shell."""
    current_settings = settings or get_settings()
    engine = AnalysisEngine(current_settings.get_sqlite_path())

    app = FastAPI(
        title="Final Thesis API",
        description="Deployment walking skeleton for hierarchical financial analysis application",
        version="0.1.0",
    )

    # Explicit CORS configuration
    cors_kwargs = {
        "allow_origins": current_settings.cors_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["*"],
    }
    if current_settings.cors_origin_regex:
        cors_kwargs["allow_origin_regex"] = current_settings.cors_origin_regex

    app.add_middleware(CORSMiddleware, **cors_kwargs)

    @app.get("/api/health", summary="Liveness probe")
    def health() -> dict[str, str]:
        """Liveness endpoint for load balancers, Render, and heartbeat monitors."""
        return {
            "status": "ok",
            "service": current_settings.app_name,
        }

    @app.get("/api/ready", summary="Readiness probe")
    def ready(response: Response) -> dict[str, str]:
        """Readiness endpoint verifying Supabase PostgreSQL infrastructure connectivity."""
        is_connected, message = check_database_connection(current_settings.database_url)
        if is_connected:
            return {
                "status": "ready",
                "database": "connected",
            }
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unavailable",
            "database": "disconnected",
            "detail": message,
        }

    @app.get("/api/version", summary="Safe deployment version metadata")
    def version() -> dict[str, str]:
        """Safe deployment metadata reporting environment and revision without secrets."""
        return current_settings.get_version_metadata()

    @app.post(
        "/api/analyze",
        response_model=AnalysisResponse,
        summary="Submit analysis query to hierarchical multi-agent system",
    )
    def analyze(request: AnalysisRequest) -> AnalysisResponse:
        """Analyze financial health and CAMEL ratios across macro, sector, and company dimensions."""
        return engine.analyze(request)

    return app


app = create_app()
