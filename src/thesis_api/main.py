"""FastAPI application shell for deployment walking skeleton."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .database import (
    get_analysis_report,
    get_analysis_run,
    list_analysis_runs,
)
from .schemas import AnalysisRequest, AnalysisResponse
from .service import AnalysisEngine, stream_analysis_query
from .settings import Settings, get_settings
from .snapshot_bootstrap import SnapshotBootstrapError, ensure_snapshot_from_settings


logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, semantic_critic=None, analysis_writer=None) -> FastAPI:
    """Factory creating the FastAPI application shell."""
    current_settings = settings or get_settings()
    sqlite_path = current_settings.get_sqlite_path()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """Hydrate an explicitly configured private snapshot before serving traffic."""
        try:
            ensure_snapshot_from_settings(current_settings)
        except SnapshotBootstrapError:
            logger.exception("Accepted snapshot bootstrap failed; refusing application startup.")
            raise
        yield

    engine = AnalysisEngine(
        sqlite_path, current_settings,
        semantic_critic=semantic_critic,
        analysis_writer=analysis_writer,
    )

    app = FastAPI(
        title="Final Thesis API",
        description="Deployment walking skeleton for hierarchical financial analysis application",
        version="0.1.0",
        lifespan=lifespan,
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

    def analysis_runs_path():
        try:
            return current_settings.get_analysis_runs_path(dataset_path=sqlite_path)
        except (OSError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The operational analysis history store is not configured separately from the accepted dataset.",
            ) from exc

    @app.get("/api/health", summary="Liveness probe")
    def health() -> dict[str, str]:
        """Liveness endpoint for load balancers, Render, and heartbeat monitors."""
        return {
            "status": "ok",
            "service": current_settings.app_name,
        }

    @app.get("/api/ready", summary="Readiness probe")
    def ready(response: Response) -> dict[str, Any]:
        """Readiness requires a runnable accepted snapshot for company claims."""
        capabilities = engine.get_capabilities()
        is_ready = bool(capabilities.get("analysis_available"))
        payload: dict[str, Any] = {
            "status": "ready" if is_ready else "unavailable",
            "database": capabilities.get("database_status", "disconnected"),
            "dataset_snapshot_id": capabilities.get("datasetSnapshotId"),
        }
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            payload["detail"] = capabilities.get("readiness", "Accepted snapshot unavailable.")
        return payload

    @app.get("/api/version", summary="Safe deployment version metadata")
    def version() -> dict[str, str]:
        """Safe deployment metadata reporting environment and revision without secrets."""
        return current_settings.get_version_metadata()

    @app.get(
        "/api/capabilities",
        summary="Retrieve capabilities declared by the configured accepted dataset snapshot",
    )
    def capabilities() -> dict[str, Any]:
        """Return scope and operations discovered through the dataset provider."""
        return engine.get_capabilities()

    @app.post(
        "/api/analyze",
        response_model=AnalysisResponse,
        response_model_exclude_none=True,
        summary="Submit analysis query to hierarchical multi-agent system",
    )
    def analyze(request: AnalysisRequest) -> AnalysisResponse:
        """Analyze financial health and CAMEL ratios across macro, sector, and company dimensions."""
        return engine.analyze(request)

    @app.post(
        "/api/analyze/stream",
        summary="Stream analysis session events (SSE)",
        response_class=StreamingResponse,
    )
    def analyze_stream(request: AnalysisRequest) -> StreamingResponse:
        """Stream real-time execution lifecycle events as Server-Sent Events (SSE)."""
        step_delay = 0.0 if current_settings.app_env == "test" else 0.35
        return StreamingResponse(
            stream_analysis_query(
                request,
                db_path=sqlite_path,
                step_delay=step_delay,
                settings=current_settings,
                semantic_critic=semantic_critic,
                analysis_writer=analysis_writer,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get(
        "/api/runs",
        summary="List recent analysis runs stored in SQLite",
    )
    def get_runs(limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent analysis runs ordered by created_at DESC."""
        return list_analysis_runs(analysis_runs_path(), limit=limit)

    @app.get(
        "/api/runs/{run_id}",
        summary="Retrieve specific analysis run with events and report",
    )
    def get_run(run_id: str) -> dict[str, Any]:
        """Retrieve specific analysis run by run_id."""
        run_record = get_analysis_run(analysis_runs_path(), run_id)
        if not run_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis run {run_id} not found",
            )
        return run_record

    @app.get(
        "/api/reports/{report_id}",
        summary="Retrieve report artifact by report_id or run_id",
    )
    def get_report(report_id: str) -> dict[str, Any]:
        """Retrieve report artifact directly from analysis_runs in SQLite."""
        report = get_analysis_report(analysis_runs_path(), report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found",
            )
        return report

    return app


app = create_app()
