"""FastAPI application shell for deployment walking skeleton."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import csv
import dataclasses
import io
import json
import logging
from pathlib import Path
import hashlib
import re
import secrets
import threading
from typing import Any, Optional
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .auth import (
    AuthConfigurationError,
    AuthErrorResponse,
    AuthStatusResponse,
    LoginRequest,
    LoginResponse,
    create_access_token,
    default_rate_limiter,
    get_client_ip,
    is_public_path,
    verify_access_token,
    verify_credentials,
)


from .database import (
    get_analysis_report,
    get_analysis_run,
    get_analysis_run_trace,
    list_analysis_runs,
)
from .lineage import router as lineage_router
from .market_data import router as market_router
from .run_history_storage import hydrate_run_history
from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
    RunTraceDTO,
    UploadMetricItemDTO,
    UploadResponseDTO,
    UploadRowIssueDTO,
    UploadSummaryDTO,
    FilingCandidateRowDTO,
    FilingCreateResponseDTO,
    FilingDetailDTO,
    FilingProgressDTO,
    FilingRowAlternativeDTO,
    FilingRowIssueDTO,
    FilingRowUpdateRequest,
    FilingRowUpdateResponse,
    FilingSampleDTO,
    FilingStatementPagesDTO,
    FilingSummaryDTO,
    FilingValidationDTO,
)
from .filing_ocr import PyMuPDFTesseractPageTextProvider, TesseractNotFoundError
from .filing_llamaparse import LlamaParseError, LlamaParseProvider
from .filing_llm_selector import refine_candidates_with_llm
from .service import AnalysisEngine, stream_analysis_query
from .settings import Settings, get_settings
from .snapshot_bootstrap import SnapshotBootstrapError, ensure_snapshot_from_settings
from thesis_data.filing_extract import (
    ExtractionResult,
    PageInput,
    classify_pages,
    extract_candidates_from_pages,
)
from thesis_data.filing_sample import (
    build_sample_filing_dict,
    generate_sample_placeholder_png,
    list_sample_summaries,
)
from thesis_data.filing_validate import validate_filing_rows
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
        if current_settings.auth_enabled:
            try:
                current_settings.validate_auth_configuration()
            except ValueError as exc:
                logger.exception("Auth configuration invalid; refusing application startup.")
                raise AuthConfigurationError(str(exc)) from exc

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

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if not current_settings.auth_enabled:
            return await call_next(request)

        if is_public_path(request.url.path, request.method):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Yêu cầu đăng nhập để truy cập tài nguyên này.",
                    "code": "auth_required",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header[7:].strip()
        payload = verify_access_token(
            token,
            secret=current_settings.auth_token_secret,
            expected_username=current_settings.app_login_user,
        )
        if not payload:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Token xác thực không hợp lệ hoặc đã hết hạn.",
                    "code": "auth_required",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)

    app.state.sqlite_path = sqlite_path
    app.include_router(lineage_router)
    app.include_router(market_router)

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
        auth_valid = True
        if current_settings.auth_enabled:
            try:
                current_settings.validate_auth_configuration()
            except ValueError:
                auth_valid = False

        payload: dict[str, Any] = {
            "status": "ready" if (is_ready and auth_valid) else "unavailable",
            "database": capabilities.get("database_status", "disconnected"),
            "dataset_snapshot_id": capabilities.get("datasetSnapshotId"),
            "auth_required": bool(current_settings.auth_enabled),
        }
        if not is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            payload["detail"] = capabilities.get("readiness", "Accepted snapshot unavailable.")
        elif not auth_valid:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            payload["detail"] = "Authentication configuration is invalid."
        return payload

    @app.get("/api/version", summary="Safe deployment version metadata")
    def version() -> dict[str, str]:
        """Safe deployment metadata reporting environment and revision without secrets."""
        return current_settings.get_version_metadata()

    @app.get(
        "/api/auth/status",
        response_model=AuthStatusResponse,
        summary="Get authentication gate status",
    )
    def auth_status() -> AuthStatusResponse:
        """Return whether authentication is required for protected endpoints."""
        return AuthStatusResponse(required=bool(current_settings.auth_enabled))

    @app.post(
        "/api/auth/login",
        response_model=LoginResponse,
        responses={
            401: {"model": AuthErrorResponse, "description": "Invalid credentials"},
            429: {"model": AuthErrorResponse, "description": "Too many failed attempts"},
        },
        summary="Shared-credential login",
    )
    def auth_login(request: Request, body: LoginRequest) -> Response:
        """Authenticate with shared credentials and receive an access token."""
        client_ip = get_client_ip(request)
        if default_rate_limiter.is_rate_limited(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Quá nhiều lần thử không thành công. Vui lòng thử lại sau.",
                    "code": "too_many_attempts",
                },
            )

        valid = False
        if (
            current_settings.app_login_user
            and current_settings.app_login_password
            and current_settings.auth_token_secret
        ):
            valid = verify_credentials(
                body.username,
                body.password,
                expected_user=current_settings.app_login_user,
                expected_password=current_settings.app_login_password,
            )

        if not valid:
            default_rate_limiter.record_failure(client_ip)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Tên đăng nhập hoặc mật khẩu không chính xác.",
                    "code": "invalid_credentials",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        default_rate_limiter.record_success(client_ip)
        token, expires_at = create_access_token(
            username=current_settings.app_login_user,
            secret=current_settings.auth_token_secret,
            ttl_hours=current_settings.auth_token_ttl_hours,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "access_token": token,
                "token_type": "bearer",
                "expires_at": expires_at,
            },
        )


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

    @app.post(
        "/api/onboarding/filings",
        response_model=FilingCreateResponseDTO,
        status_code=status.HTTP_202_ACCEPTED,
        summary="Upload and extract bank financial statement PDF",
    )
    async def upload_filing_pdf(
        file: UploadFile = File(..., description="Annual financial statement PDF"),
        entity_id: str = Form(..., description="Bank ticker (3-10 chars)"),
        display_name: Optional[str] = Form(None, description="Optional bank display name"),
        fiscal_year: int = Form(..., description="Reporting fiscal year (e.g. 2025)"),
        reporting_scope: str = Form(..., description="Reporting scope ('consolidated' or 'separate')"),
    ) -> Response:
        """Parse, OCR, classify, and extract candidate rows from an annual financial statement PDF."""
        clean_entity = entity_id.strip().upper()
        if not re.fullmatch(r"^[A-Za-z0-9_]{3,10}$", clean_entity):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã ngân hàng '{entity_id}' không hợp lệ (yêu cầu từ 3 đến 10 ký tự).",
            )

        try:
            served = {
                str(e.get("id") or e.get("ticker") or "").upper()
                for e in engine.get_capabilities().get("entities", [])
            }
        except Exception:
            served = set()
        if clean_entity in served:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{clean_entity} đã có trong bộ dữ liệu hệ thống; hãy hỏi trực tiếp về "
                    f"{clean_entity} thay vì tải lên. Chức năng nạp báo cáo tài chính dành cho ngân hàng chưa có trong dữ liệu."
                ),
            )

        if fiscal_year < 2000 or fiscal_year > 2100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Năm tài chính không hợp lệ (yêu cầu từ năm 2000 đến 2100).",
            )

        clean_scope = reporting_scope.strip().lower()
        if clean_scope not in ("consolidated", "separate"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phạm vi báo cáo không hợp lệ (yêu cầu 'consolidated' hoặc 'separate').",
            )

        content = await file.read()
        if len(content) > 40 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Kích thước tệp vượt quá giới hạn cho phép (tối đa 40 MB, thực tế: {len(content)} bytes).",
            )

        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tệp tải lên không phải là định dạng PDF hợp lệ.",
            )

        try:
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            if doc.is_encrypted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tệp PDF bị đặt mật khẩu bảo vệ hoặc mã hóa.",
                )
            page_count = len(doc)
            doc.close()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tệp PDF bị hỏng hoặc không thể đọc: {str(exc)}",
            ) from exc

        filing_id = f"fl-{secrets.token_hex(6)}"
        uploads_dir = current_settings.get_user_uploads_dir()
        filing_dir = uploads_dir / "filings" / filing_id
        pages_dir = filing_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = filing_dir / "source.pdf"
        try:
            pdf_path.write_bytes(content)
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi lưu trữ tệp PDF: {str(exc)}",
            ) from exc

        pdf_sha256 = hashlib.sha256(content).hexdigest().upper()
        now_iso = datetime.now(timezone.utc).isoformat()
        effective_display = display_name or clean_entity

        meta: dict[str, Any] = {
            "filing_id": filing_id,
            "entity_id": clean_entity,
            "display_name": effective_display,
            "fiscal_year": fiscal_year,
            "reporting_scope": clean_scope,
            "status": "processing",
            "error_code": None,
            "message_vi": None,
            "filename": file.filename or "source.pdf",
            "sha256": pdf_sha256,
            "page_count": page_count,
            "progress": {"pages_done": 0, "page_count": page_count},
            "text_layer_pages": 0,
            "ocr_pages": 0,
            "statement_pages": {"balance_sheet": [], "income_statement": [], "loan_quality_note": []},
            "unit_detected": None,
            "rows": [],
            "limitations_vi": None,
            "created_at": now_iso,
        }

        meta_file = filing_dir / "meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        def _process_filing() -> None:
            try:
                def _progress_cb(done: int, total: int) -> None:
                    try:
                        meta["progress"] = {"pages_done": done, "page_count": total}
                        with open(meta_file, "w", encoding="utf-8") as mf:
                            json.dump(meta, mf, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                custom_provider = getattr(app.state, "filing_page_provider", None)
                pages_sent_to_ocr = 0

                cutoff_note: Optional[str] = None

                if custom_provider is not None:
                    pages = custom_provider.extract_all_pages(
                        pdf_path,
                        cache_dir=pages_dir,
                        max_workers=4,
                        progress_callback=_progress_cb,
                    )
                    pages_sent_to_ocr = getattr(custom_provider, "total_pages_sent", 0)
                else:
                    has_llama_key = bool(
                        current_settings.llama_cloud_api_key
                        and current_settings.llama_cloud_api_key.get_secret_value().strip()
                    )
                    use_llamaparse = False
                    if current_settings.ocr_provider == "llamaparse":
                        use_llamaparse = True
                    elif current_settings.ocr_provider == "auto" and has_llama_key:
                        use_llamaparse = True

                    ocr_scope = getattr(current_settings, "filing_ocr_scope", "full").lower()
                    max_pages = getattr(current_settings, "llama_max_pages_per_filing", 300)

                    import fitz

                    doc = fitz.open(pdf_path)
                    total_pages = len(doc)
                    doc.close()

                    cutoff_note: Optional[str] = None
                    if total_pages > max_pages:
                        cutoff_note = (
                            f"Tài liệu có {total_pages} trang, vượt quá giới hạn cấu hình {max_pages} trang; "
                            f"hệ thống chỉ xử lý {max_pages} trang đầu."
                        )
                        effective_pages_limit = max_pages
                    else:
                        effective_pages_limit = total_pages

                    if not use_llamaparse:
                        provider = PyMuPDFTesseractPageTextProvider()
                        if ocr_scope == "selected":
                            stage_a_pages = []
                            for pno in range(1, effective_pages_limit + 1):
                                p_inp = provider.get_page_text(pdf_path, pno, cache_dir=None)
                                stage_a_pages.append(p_inp)
                            stmt_pages = classify_pages(stage_a_pages)
                            selected_pages = stmt_pages.get_selected_pages_with_overflow(
                                total_pages=effective_pages_limit,
                                max_pages=max_pages,
                            )
                            pages_sent_to_ocr = len(selected_pages)
                            for pno in selected_pages:
                                provider.get_page_text(pdf_path, pno, cache_dir=pages_dir)
                            pages = [
                                provider.get_page_text(pdf_path, pno, cache_dir=pages_dir)
                                for pno in range(1, effective_pages_limit + 1)
                            ]
                        else:
                            pages = provider.extract_all_pages(
                                pdf_path,
                                cache_dir=pages_dir,
                                max_workers=4,
                                progress_callback=_progress_cb,
                                max_pages=effective_pages_limit,
                            )
                            pages_sent_to_ocr = sum(1 for p in pages if p.source == "ocr")
                    else:
                        tesseract_provider = PyMuPDFTesseractPageTextProvider(dpi=100)
                        tesseract_avail = tesseract_provider.is_tesseract_available()
                        api_key = (
                            current_settings.llama_cloud_api_key.get_secret_value()
                            if current_settings.llama_cloud_api_key
                            else None
                        )
                        lp_provider = LlamaParseProvider(
                            api_key=api_key,
                            timeout_s=90.0,
                            max_retries=2,
                            tesseract_fallback=tesseract_provider if tesseract_avail else None,
                        )

                        if ocr_scope == "full":
                            pages = lp_provider.extract_pages(
                                pdf_path,
                                list(range(1, effective_pages_limit + 1)),
                                cache_dir=pages_dir,
                                progress_callback=_progress_cb,
                                chunk_size=40,
                                max_workers=2,
                            )
                            pages_sent_to_ocr = len(pages)
                        else:
                            doc = fitz.open(pdf_path)
                            stage_a_pages: list[PageInput] = []
                            unreadable_pages: list[int] = []
                            for pno in range(1, effective_pages_limit + 1):
                                page = doc[pno - 1]
                                txt = page.get_text()
                                if len(txt.strip()) >= 200 and txt.count("\ufffd") <= 20:
                                    stage_a_pages.append(PageInput(page_number=pno, text=txt, source="text_layer"))
                                else:
                                    unreadable_pages.append(pno)
                            doc.close()

                            if unreadable_pages:
                                if tesseract_avail:
                                    for pno in unreadable_pages:
                                        page_inp = tesseract_provider.get_page_text(pdf_path, pno, cache_dir=None)
                                        stage_a_pages.append(page_inp)
                                else:
                                    for pno in unreadable_pages:
                                        stage_a_pages.append(PageInput(page_number=pno, text="", source="text_layer"))

                            stage_a_pages.sort(key=lambda p: p.page_number)
                            stmt_pages = classify_pages(stage_a_pages)
                            selected_pages = stmt_pages.get_selected_pages_with_overflow(
                                total_pages=effective_pages_limit,
                                max_pages=max_pages,
                            )
                            if not selected_pages and unreadable_pages and not tesseract_avail:
                                selected_pages = list(range(1, min(effective_pages_limit, max_pages) + 1))

                            lp_pages = lp_provider.extract_pages(
                                pdf_path,
                                selected_pages,
                                cache_dir=pages_dir,
                                progress_callback=_progress_cb,
                                chunk_size=40,
                                max_workers=2,
                            )
                            pages_sent_to_ocr = len(selected_pages)
                            lp_map = {p.page_number: p for p in lp_pages}
                            pages = [lp_map.get(p.page_number, p) for p in stage_a_pages]

                ext = extract_candidates_from_pages(
                    pages,
                    entity_id=clean_entity,
                    fiscal_year=fiscal_year,
                    reporting_scope=clean_scope,
                    display_name=effective_display,
                    filing_id=filing_id,
                )

                if getattr(current_settings, "filing_llm_assist", False):
                    ext, _ = refine_candidates_with_llm(
                        ext,
                        pages,
                        settings=current_settings,
                    )

                extra_notes: list[str] = []
                if cutoff_note:
                    extra_notes.append(cutoff_note)
                extra_notes.append(f"Đã đọc {len(pages)} trang")
                if pages_sent_to_ocr > 0:
                    extra_notes.append(f"Đã gửi {pages_sent_to_ocr} trang tới dịch vụ OCR")

                current_limitations = list(ext.limitations_vi) if isinstance(ext.limitations_vi, list) else [ext.limitations_vi]
                for note in reversed(extra_notes):
                    if note not in current_limitations:
                        current_limitations.insert(0, note)
                ext = ExtractionResult(
                    filing_id=ext.filing_id,
                    entity_id=ext.entity_id,
                    display_name=ext.display_name,
                    fiscal_year=ext.fiscal_year,
                    reporting_scope=ext.reporting_scope,
                    page_count=ext.page_count,
                    ocr_provider=ext.ocr_provider,
                    text_layer_pages=ext.text_layer_pages,
                    ocr_pages=ext.ocr_pages,
                    statement_pages=ext.statement_pages,
                    unit_detected=ext.unit_detected,
                    rows=ext.rows,
                    validation=ext.validation,
                    limitations_vi=current_limitations,
                )

                meta["status"] = "ready"
                meta["ocr_provider"] = ext.ocr_provider
                meta["text_layer_pages"] = ext.text_layer_pages
                meta["ocr_pages"] = ext.ocr_pages
                meta["pages_sent_to_ocr"] = pages_sent_to_ocr
                meta["statement_pages"] = ext.statement_pages.to_dict()
                meta["unit_detected"] = ext.unit_detected
                meta["rows"] = [r.to_dict() for r in ext.rows]
                val = validate_filing_rows(ext.rows, page_texts={p.page_number: p.text for p in pages})
                meta["validation"] = val.to_dict()
                meta["limitations_vi"] = ext.limitations_vi
                meta["progress"] = {"pages_done": page_count, "page_count": page_count}
                with open(meta_file, "w", encoding="utf-8") as mf:
                    json.dump(meta, mf, ensure_ascii=False, indent=2)
            except TesseractNotFoundError as exc:
                meta["status"] = "failed"
                meta["error_code"] = "ocr_unavailable"
                meta["message_vi"] = str(exc)
                with open(meta_file, "w", encoding="utf-8") as mf:
                    json.dump(meta, mf, ensure_ascii=False, indent=2)
            except LlamaParseError as exc:
                meta["status"] = "failed"
                meta["error_code"] = "provider_error"
                meta["message_vi"] = str(exc)
                with open(meta_file, "w", encoding="utf-8") as mf:
                    json.dump(meta, mf, ensure_ascii=False, indent=2)
            except Exception as exc:
                logger.error("Failed to process filing %s: %s", filing_id, exc)
                meta["status"] = "failed"
                meta["error_code"] = "extraction_failed"
                meta["message_vi"] = f"Lỗi trong quá trình đọc và trích xuất tài liệu: {str(exc)}"
                with open(meta_file, "w", encoding="utf-8") as mf:
                    json.dump(meta, mf, ensure_ascii=False, indent=2)

        if getattr(app.state, "filing_sync_execution", False):
            _process_filing()
        else:
            threading.Thread(target=_process_filing, daemon=True).start()

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"filing_id": filing_id, "status": "processing"},
        )

    @app.get(
        "/api/onboarding/filings",
        response_model=list[FilingSummaryDTO],
        summary="List user-supplied bank filings",
    )
    def list_filings() -> list[FilingSummaryDTO]:
        """List recently uploaded bank filings and their status."""
        uploads_dir = current_settings.get_user_uploads_dir()
        filings_dir = uploads_dir / "filings"
        if not filings_dir.exists():
            return []
        summaries: list[FilingSummaryDTO] = []
        for meta_path in filings_dir.glob("fl-*/meta.json"):
            try:
                with open(meta_path, encoding="utf-8") as f:
                    d = json.load(f)
                candidate_count = sum(1 for r in d.get("rows", []) if r.get("status") == "candidate")
                review_count = sum(1 for r in d.get("rows", []) if r.get("status") == "needs_review")
                summaries.append(
                    FilingSummaryDTO(
                        filing_id=d["filing_id"],
                        entity_id=d.get("entity_id", ""),
                        display_name=d.get("display_name", d.get("entity_id", "")),
                        fiscal_year=d.get("fiscal_year", 0),
                        reporting_scope=d.get("reporting_scope", "consolidated"),
                        status=d["status"],
                        created_at=d.get("created_at", ""),
                        filename=d.get("filename", ""),
                        page_count=d.get("page_count", 0),
                        candidate_rows_count=candidate_count,
                        needs_review_count=review_count,
                    )
                )
            except Exception:
                continue
        summaries.sort(key=lambda item: item.created_at, reverse=True)
        return summaries

    @app.get(
        "/api/onboarding/filings/{filing_id}",
        response_model=FilingDetailDTO,
        summary="Get details of a specific bank filing",
    )
    def get_filing_detail(filing_id: str) -> FilingDetailDTO:
        """Retrieve full candidate extraction results and statement pages for a filing."""
        clean_id = filing_id.strip()
        if not re.fullmatch(r"^fl-[a-f0-9]{12}$", clean_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã filing '{filing_id}' không hợp lệ (yêu cầu định dạng fl- + 12 ký tự hex).",
            )
        uploads_dir = current_settings.get_user_uploads_dir()
        meta_file = uploads_dir / "filings" / clean_id / "meta.json"
        if not meta_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Filing '{clean_id}' không tồn tại.",
            )
        try:
            with open(meta_file, encoding="utf-8") as f:
                data = json.load(f)
            return FilingDetailDTO.model_validate(data)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi đọc dữ liệu tệp filing: {str(exc)}",
            ) from exc

    @app.get(
        "/api/onboarding/filing-samples",
        response_model=list[FilingSampleDTO],
        summary="List pre-built financial filing samples for demonstration",
    )
    def list_filing_samples() -> list[FilingSampleDTO]:
        """Return catalog of curated filing samples built from verified data."""
        return [FilingSampleDTO.model_validate(s) for s in list_sample_summaries()]

    @app.post(
        "/api/onboarding/filing-samples/{sample_id}/open",
        response_model=FilingDetailDTO,
        summary="Open a pre-built filing sample into a ready filing",
    )
    def open_filing_sample(sample_id: str) -> FilingDetailDTO:
        """Instantiate a ready filing directly from verified sample data (no OCR)."""
        clean_id = sample_id.strip().lower()
        uploads_dir = current_settings.get_user_uploads_dir()
        filing_id = f"fl-{uuid.uuid4().hex[:12]}"
        try:
            filing_data = build_sample_filing_dict(clean_id, filing_id=filing_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mẫu filing '{sample_id}' không tồn tại.",
            )
        except Exception as exc:
            logger.error("Failed to build filing sample %s: %s", sample_id, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi khởi tạo mẫu filing: {str(exc)}",
            ) from exc

        # Persist filing meta.json
        filing_dir = uploads_dir / "filings" / filing_id
        pages_dir = filing_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        meta_file = filing_dir / "meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(filing_data, f, ensure_ascii=False, indent=2)

        return FilingDetailDTO.model_validate(filing_data)

    @app.get(
        "/api/onboarding/filings/{filing_id}/pages/{n}.png",
        summary="Get rendered page image (120 dpi PNG)",
    )
    def get_filing_page_image(filing_id: str, n: int) -> Response:
        """Render and return page n of the filing as a 120 DPI PNG image."""
        clean_id = filing_id.strip()
        if not re.fullmatch(r"^fl-[a-f0-9]{12}$", clean_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã filing '{filing_id}' không hợp lệ.",
            )
        if n < 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Số trang phải lớn hơn hoặc bằng 1.",
            )

        uploads_dir = current_settings.get_user_uploads_dir()
        filing_dir = uploads_dir / "filings" / clean_id
        meta_path = filing_dir / "meta.json"
        pdf_path = filing_dir / "source.pdf"

        if not meta_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Filing '{clean_id}' không tồn tại.",
            )

        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            page_count = meta.get("page_count", 0)
            if n > page_count:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Trang {n} vượt quá tổng số {page_count} trang.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

        cache_png = filing_dir / "pages" / f"p{n:03d}.png"
        if cache_png.exists():
            return Response(content=cache_png.read_bytes(), media_type="image/png")

        # Resolve PDF source or sample placeholder
        effective_pdf: Optional[Path] = None
        if pdf_path.exists():
            effective_pdf = pdf_path
        else:
            # Check local official raw PDFs
            entity_id = meta.get("entity_id", "")
            local_pdf = Path("data/raw/official/bank-2025-top10-v1") / f"{entity_id}_2025_audited_consolidated.pdf"
            if not local_pdf.exists():
                root = Path(__file__).resolve().parents[2]
                local_pdf = root / "data" / "raw" / "official" / "bank-2025-top10-v1" / f"{entity_id}_2025_audited_consolidated.pdf"
            if local_pdf.exists():
                effective_pdf = local_pdf

        if effective_pdf is not None:
            provider = getattr(app.state, "filing_page_provider", None) or PyMuPDFTesseractPageTextProvider()
            try:
                png_bytes = provider.render_page_png(effective_pdf, n, dpi=120, cache_path=cache_png)
                return Response(content=png_bytes, media_type="image/png")
            except IndexError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Trang {n} không tồn tại.",
                )
            except Exception as exc:
                logger.error("Failed to render page %d: %s", n, exc)
                if meta.get("ocr_provider") != "sample":
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Lỗi dựng ảnh trang: {str(exc)}",
                    ) from exc

        if meta.get("ocr_provider") == "sample":
            png_bytes = generate_sample_placeholder_png(
                n,
                page_count=page_count,
                entity_id=meta.get("entity_id", ""),
            )
            cache_png.parent.mkdir(parents=True, exist_ok=True)
            cache_png.write_bytes(png_bytes)
            return Response(content=png_bytes, media_type="image/png")

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tệp PDF nguồn của filing '{clean_id}' không tồn tại.",
        )

    @app.put(
        "/api/onboarding/filings/{filing_id}/rows/{row_id}",
        response_model=FilingRowUpdateResponse,
        summary="Update and/or confirm a candidate row in a filing",
    )
    def update_filing_row(
        filing_id: str,
        row_id: str,
        payload: FilingRowUpdateRequest,
    ) -> FilingRowUpdateResponse:
        """Update value and/or confirmation status for a specific filing row, re-running validation."""
        clean_id = filing_id.strip()
        if not re.fullmatch(r"^fl-[a-f0-9]{12}$", clean_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã filing '{filing_id}' không hợp lệ.",
            )

        uploads_dir = current_settings.get_user_uploads_dir()
        filing_dir = uploads_dir / "filings" / clean_id
        meta_file = filing_dir / "meta.json"
        if not meta_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Filing '{clean_id}' không tồn tại.",
            )

        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi đọc dữ liệu tệp filing: {str(exc)}",
            ) from exc

        if meta.get("status") != "ready":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Filing không ở trạng thái sẵn sàng (ready) để chỉnh sửa.",
            )

        # Find target row
        target_row: Optional[dict[str, Any]] = None
        for r in meta.get("rows", []):
            if r.get("row_id") == row_id:
                target_row = r
                break

        if target_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dòng '{row_id}' không tồn tại trong filing.",
            )

        # Validate decimal format of value_billion_vnd if provided
        val_str = payload.value_billion_vnd
        val_dec: Optional[Decimal] = None
        if val_str is not None:
            v_cleaned = val_str.strip()
            if v_cleaned == "":
                val_str = None
            else:
                try:
                    val_dec = Decimal(v_cleaned)
                except (InvalidOperation, ValueError):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Giá trị '{val_str}' không phải là số thập phân hợp lệ.",
                    )
                if val_dec.is_nan() or val_dec.is_infinite():
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Giá trị không được là NaN hoặc vô cực.",
                    )
                parts = v_cleaned.split(".")
                if len(parts) == 2 and len(parts[1]) > 6:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Giá trị vượt quá độ chính xác tối đa (tối đa 6 chữ số thập phân).",
                    )
                metric_id = target_row.get("metric_id", "")
                if metric_id not in ("bank.input.profit_after_tax", "bank.input.parent_attributable_profit") and val_dec < Decimal("0"):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Chỉ tiêu {target_row.get('label_vi', metric_id)} không được mang giá trị âm.",
                    )
                val_str = v_cleaned

        extracted_val = target_row.get("extracted_value_billion_vnd")
        if val_str != extracted_val:
            target_row["edited"] = True
            target_row["source"] = "user"

        target_row["value_billion_vnd"] = val_str
        target_row["confirmed"] = payload.confirmed

        # Load page text cache if available
        page_texts: dict[int, str] = {}
        pages_cache_dir = filing_dir / "pages"
        if pages_cache_dir.exists():
            for p_file in pages_cache_dir.glob("p*.txt"):
                m = re.search(r"p(\d+)\.txt", p_file.name)
                if m:
                    try:
                        page_texts[int(m.group(1))] = p_file.read_text(encoding="utf-8")
                    except Exception:
                        pass

        # Re-run full validation
        val_res = validate_filing_rows(meta.get("rows", []), page_texts=page_texts)
        meta["validation"] = val_res.to_dict()

        # Update row status based on value and issues
        if target_row["value_billion_vnd"] is None:
            target_row["status"] = "missing"
        elif any(row_id in c.row_ids and c.severity in ("error", "warning") for c in val_res.checks):
            target_row["status"] = "needs_review"
        else:
            target_row["status"] = "candidate"

        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi lưu trữ filing: {str(exc)}",
            ) from exc

        return FilingRowUpdateResponse(
            row=FilingCandidateRowDTO.model_validate(target_row),
            validation=FilingValidationDTO.model_validate(val_res.to_dict()),
        )

    @app.post(
        "/api/onboarding/filings/{filing_id}/confirm",
        response_model=UploadResponseDTO,
        summary="Confirm candidate rows and materialize operational snapshot",
    )
    def confirm_filing(filing_id: str) -> UploadResponseDTO:
        """Confirm filing into an operational SQLite snapshot once ready_to_confirm is true."""
        clean_id = filing_id.strip()
        if not re.fullmatch(r"^fl-[a-f0-9]{12}$", clean_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã filing '{filing_id}' không hợp lệ.",
            )

        uploads_dir = current_settings.get_user_uploads_dir()
        filing_dir = uploads_dir / "filings" / clean_id
        meta_file = filing_dir / "meta.json"
        if not meta_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Filing '{clean_id}' không tồn tại.",
            )

        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi đọc dữ liệu tệp filing: {str(exc)}",
            ) from exc

        # Idempotency check: if already confirmed, return existing upload
        existing_upload_id = meta.get("upload_id")
        if existing_upload_id:
            existing_upload_file = uploads_dir / f"{existing_upload_id}.json"
            if existing_upload_file.exists():
                try:
                    with open(existing_upload_file, encoding="utf-8") as f:
                        data = json.load(f)
                    return UploadResponseDTO.model_validate(data)
                except Exception:
                    pass

        # Check readiness
        val_res = validate_filing_rows(meta.get("rows", []))
        if not val_res.ready_to_confirm:
            reasons = "; ".join(val_res.blocking_reasons_vi) if val_res.blocking_reasons_vi else "Filing chưa hoàn thành kiểm tra hoặc chưa được xác nhận đủ 20 dòng."
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Filing chưa sẵn sàng để xác nhận: {reasons}",
            )

        clean_entity = meta.get("entity_id", "").strip().upper()
        clean_name = meta.get("display_name") or clean_entity

        # Build CSV according to UPLOAD-1 format
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow([
            "observation_id",
            "entity_id",
            "metric_id",
            "value",
            "unit",
            "period_id",
            "period_basis",
            "reporting_scope",
            "source_locator",
            "source_url",
            "source_sha256",
        ])

        source_url = meta.get("source_url") or f"urn:filing:{clean_id}:{meta.get('filename', 'source.pdf')}"
        source_sha256 = meta.get("sha256", "")
        scope = meta.get("reporting_scope", "consolidated")

        for r in meta.get("rows", []):
            m_id = r["metric_id"]
            p_id = r["period_id"]
            val = r.get("value_billion_vnd", "")
            p_basis = "annual" if m_id in ("bank.input.profit_after_tax", "bank.input.parent_attributable_profit") else "point_in_time"
            page = r.get("page") or 1
            label = r.get("row_label") or r.get("raw_text") or r.get("label_vi") or m_id
            locator = f"pdf_page={page}; row={label}"
            obs_id = f"{clean_entity.lower()}-{m_id.replace('.', '-')}-{p_id.lower()}"
            writer.writerow([
                obs_id,
                clean_entity,
                m_id,
                val,
                "billion_vnd",
                p_id,
                p_basis,
                scope,
                locator,
                source_url,
                source_sha256,
            ])

        csv_content = csv_buffer.getvalue()
        csv_bytes = csv_content.encode("utf-8")

        upload_id = f"up-{uuid.uuid4().hex[:12]}"
        upload_result = validate_and_parse_upload_csv(
            csv_bytes,
            upload_id=upload_id,
            form_entity_id=clean_entity,
            form_display_name=clean_name,
        )

        if upload_result.status == "rejected":
            translated_issues = []
            rows_list = meta.get("rows", [])
            for iss in upload_result.row_issues:
                iss_dict = iss.to_dict()
                if 1 <= iss.row <= len(rows_list):
                    iss_dict["row_id"] = rows_list[iss.row - 1].get("row_id")
                translated_issues.append(iss_dict)
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": "Snapshot bị từ chối trong quá trình kiểm tra cấu trúc và tính toán lại chỉ tiêu.",
                    "row_issues": translated_issues,
                },
            )

        # Materialize SQLite snapshot
        sqlite_path = uploads_dir / f"{upload_id}.sqlite"
        try:
            materialize_user_upload_snapshot(upload_result, sqlite_path)
        except Exception as exc:
            logger.error("Failed to materialize filing operational snapshot %s: %s", upload_id, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi khởi tạo cơ sở dữ liệu snapshot vận hành: {str(exc)}",
            ) from exc

        # Limitation: UPLOAD-1 label + PDF extraction provenance statement
        pdf_provenance_sentence = "Số liệu được trích từ tệp PDF do người dùng tải lên và xác nhận."
        full_limitations = f"{upload_result.limitations_vi} {pdf_provenance_sentence}".strip()

        now_iso = datetime.now(timezone.utc).isoformat()
        upload_meta = {
            "upload_id": upload_id,
            "entity_id": clean_entity,
            "display_name": clean_name,
            "status": upload_result.status,
            "period_id": upload_result.period_id,
            "created_at": now_iso,
            "metrics": [m.to_dict() for m in upload_result.metrics],
            "limitations_vi": full_limitations,
            "source_type": "filing",
            "filing_id": clean_id,
        }

        # Save upload metadata and CSV
        upload_meta_file = uploads_dir / f"{upload_id}.json"
        upload_csv_file = uploads_dir / f"{upload_id}.csv"
        with open(upload_meta_file, "w", encoding="utf-8") as f:
            json.dump(upload_meta, f, ensure_ascii=False, indent=2)
        with open(upload_csv_file, "wb") as f:
            f.write(csv_bytes)

        # Update filing meta with upload_id
        meta["upload_id"] = upload_id
        meta["limitations_vi"] = [full_limitations]
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return UploadResponseDTO.model_validate(upload_meta)

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
