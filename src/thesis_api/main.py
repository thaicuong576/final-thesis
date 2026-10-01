"""FastAPI application shell for deployment walking skeleton."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import dataclasses
import json
import logging
from pathlib import Path
from typing import Any, Optional
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .database import (
    get_analysis_report,
    get_analysis_run,
    get_analysis_run_trace,
    list_analysis_runs,
)
from .run_history_storage import hydrate_run_history
from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
    RunTraceDTO,
    UploadMetricItemDTO,
    UploadResponseDTO,
    UploadRowIssueDTO,
    UploadSummaryDTO,
)
from .service import AnalysisEngine, stream_analysis_query
from .settings import Settings, get_settings
from .snapshot_bootstrap import SnapshotBootstrapError, ensure_snapshot_from_settings
from thesis_data.user_upload import (
    generate_ctg_error_sample_csv,
    generate_vib_error_sample_csv,
    generate_vib_sample_csv,
    generate_ctg_sample_csv,
    UploadRowIssue,
    generate_template_csv,
    materialize_user_upload_snapshot,
    validate_and_parse_upload_csv,
)


logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    semantic_critic=None,
    analysis_writer=None,
    planner_client=None,
) -> FastAPI:
    """Factory creating the FastAPI application shell."""
    current_settings = settings or get_settings()
    sqlite_path = current_settings.get_sqlite_path()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """Hydrate an explicitly configured private snapshot and run history before serving traffic."""
        try:
            ensure_snapshot_from_settings(current_settings)
        except SnapshotBootstrapError:
            logger.exception("Accepted snapshot bootstrap failed; refusing application startup.")
            raise

        try:
            runs_path = current_settings.get_analysis_runs_path(dataset_path=sqlite_path)
            hydrate_run_history(runs_path, current_settings)
        except Exception as exc:
            logger.warning("Remote run history hydration warning: %s", exc)

        yield

    engine = AnalysisEngine(
        sqlite_path, current_settings,
        semantic_critic=semantic_critic,
        analysis_writer=analysis_writer,
        planner_client=planner_client,
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
        "/api/analysis-runs",
        summary="Alias for /api/runs",
        include_in_schema=False,
    )
    def get_analysis_runs_alias(limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent analysis runs ordered by created_at DESC (alias)."""
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
        "/api/runs/{run_id}/trace",
        response_model=RunTraceDTO,
        response_model_exclude_none=True,
        summary="Retrieve structured execution trace for an analysis run",
    )
    def get_run_trace(run_id: str) -> RunTraceDTO:
        """Retrieve chronological, structured trace steps recorded during execution of run_id."""
        trace = get_analysis_run_trace(analysis_runs_path(), run_id)
        if not trace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis run trace for {run_id} not found",
            )
        return RunTraceDTO.model_validate(trace)

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

    def _reject_entity_already_served(result: Any) -> Any:
        """A bank that the served dataset already covers cannot be uploaded again.

        Two sources for the same ticker would give two different figures for one bank; the
        user is pointed to the existing data instead.
        """
        if result.status != "accepted" or not result.entity_id:
            return result
        try:
            served = {
                str(e.get("id") or e.get("ticker") or "").upper()
                for e in engine.get_capabilities().get("entities", [])
            }
        except Exception:  # noqa: BLE001 - capability lookup must not block an upload
            return result
        if result.entity_id.upper() not in served:
            return result
        issue = UploadRowIssue(
            row=0,
            field="entity_id",
            message_vi=(
                f"{result.entity_id} đã có trong bộ dữ liệu hệ thống; hãy hỏi trực tiếp về "
                f"{result.entity_id} thay vì tải lên. Chức năng tải lên dành cho ngân hàng chưa có trong dữ liệu."
            ),
        )
        return dataclasses.replace(result, status="rejected", row_issues=[*result.row_issues, issue])

    @app.post(
        "/api/onboarding/uploads",
        response_model=UploadResponseDTO,
        summary="Upload and validate a new bank CSV file",
    )
    async def upload_bank_csv(
        file: UploadFile = File(..., description="CSV file of bank financial statements"),
        entity_id: Optional[str] = Form(None, description="Optional bank ticker (3 letters)"),
        display_name: Optional[str] = Form(None, description="Optional bank display name"),
    ) -> UploadResponseDTO:
        """Parse, validate, and operationalize a user-supplied bank CSV."""
        content = await file.read()
        upload_id = f"up-{uuid.uuid4().hex[:12]}"
        uploads_dir = current_settings.get_user_uploads_dir()

        result = validate_and_parse_upload_csv(
            content,
            upload_id=upload_id,
            form_entity_id=entity_id,
            form_display_name=display_name,
        )
        result = _reject_entity_already_served(result)

        now_iso = datetime.now(timezone.utc).isoformat()
        if result.status == "accepted":
            sqlite_path = uploads_dir / f"{upload_id}.sqlite"
            try:
                materialize_user_upload_snapshot(result, sqlite_path)
            except Exception as exc:
                logger.error("Failed to materialize upload SQLite snapshot: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Lỗi khi dựng snapshot dữ liệu: {str(exc)}",
                ) from exc

        # Save record JSON and raw CSV
        record_data = {
            "upload_id": result.upload_id,
            "entity_id": result.entity_id,
            "display_name": result.display_name,
            "status": result.status,
            "period_id": result.period_id,
            "created_at": now_iso,
            "filename": file.filename or "upload.csv",
            "metrics": [m.to_dict() for m in result.metrics],
            "row_issues": [i.to_dict() for i in result.row_issues],
            "limitations_vi": result.limitations_vi,
        }

        meta_file = uploads_dir / f"{upload_id}.json"
        csv_file = uploads_dir / f"{upload_id}.csv"
        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(record_data, f, ensure_ascii=False, indent=2)
            with open(csv_file, "wb") as f:
                f.write(content)
        except OSError as exc:
            logger.error("Failed to write upload artifacts to %s: %s", uploads_dir, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi lưu trữ tệp tải lên vào hệ thống.",
            ) from exc

        return UploadResponseDTO.model_validate(record_data)

    @app.get(
        "/api/onboarding/uploads",
        response_model=list[UploadSummaryDTO],
        summary="List user-supplied bank uploads",
    )
    def list_uploads() -> list[UploadSummaryDTO]:
        """List all previously uploaded bank files and their status."""
        uploads_dir = current_settings.get_user_uploads_dir()
        summaries: list[UploadSummaryDTO] = []
        for path in uploads_dir.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                summaries.append(
                    UploadSummaryDTO(
                        upload_id=d["upload_id"],
                        entity_id=d["entity_id"],
                        display_name=d.get("display_name", d["entity_id"]),
                        status=d["status"],
                        period_id=d.get("period_id", ""),
                        created_at=d.get("created_at", ""),
                        row_issues_count=len(d.get("row_issues", [])),
                        metrics_count=len(d.get("metrics", [])),
                    )
                )
            except Exception:
                continue
        summaries.sort(key=lambda item: item.created_at, reverse=True)
        return summaries

    @app.get(
        "/api/onboarding/uploads/{upload_id}",
        response_model=UploadResponseDTO,
        summary="Get details of a specific bank upload",
    )
    def get_upload_detail(upload_id: str) -> UploadResponseDTO:
        """Retrieve full validation results and metrics for a specific upload."""
        uploads_dir = current_settings.get_user_uploads_dir()
        meta_file = uploads_dir / f"{upload_id.strip()}.json"
        if not meta_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload '{upload_id}' not found.",
            )
        try:
            with open(meta_file, encoding="utf-8") as f:
                data = json.load(f)
            return UploadResponseDTO.model_validate(data)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi đọc dữ liệu tệp tải lên: {str(exc)}",
            ) from exc

    @app.get(
        "/api/onboarding/template.csv",
        summary="Download CSV template for bank financial statements",
    )
    def download_template() -> Response:
        """Download blank CSV template with required input headers and metrics."""
        csv_content = generate_template_csv()
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="bank_onboarding_template.csv"'},
        )

    @app.get(
        "/api/onboarding/samples/{name}.csv",
        summary="Download sample CSV for demonstration",
    )
    def download_sample(name: str) -> Response:
        """Download CTG sample CSV (valid 'ctg-2024q4' or error 'ctg-2024q4-loi')."""
        clean_name = name.strip().lower()
        if clean_name == "vib-2025q4":
            content = generate_vib_sample_csv()
            filename = "vib-2025q4.csv"
        elif clean_name == "vib-2025q4-loi":
            content = generate_vib_error_sample_csv()
            filename = "vib-2025q4-loi.csv"
        elif clean_name == "ctg-2024q4":
            content = generate_ctg_sample_csv()
            filename = "ctg-2024q4.csv"
        elif clean_name == "ctg-2024q4-loi":
            content = generate_ctg_error_sample_csv()
            filename = "ctg-2024q4-loi.csv"
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mẫu '{name}' không tồn tại. Các mẫu hỗ trợ: vib-2025q4, vib-2025q4-loi, ctg-2024q4, ctg-2024q4-loi.",
            )
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return app


app = create_app()
