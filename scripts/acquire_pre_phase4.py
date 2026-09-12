"""Verify and register the bounded pre-Phase-4 acquisition package.

This script deliberately does not implement a provider, RAG, chunking, or
embedding pipeline.  It only hashes already retrieved public artifacts,
creates the source/document manifest, and registers conservative candidate
observations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ACQ_ROOT = ROOT / "data" / "raw" / "pre-phase4-acquisition-v1"
MANIFEST_PATH = ROOT / "data" / "manifests" / "pre-phase4-acquisition-v1.jsonl"
CANDIDATE_PATH = (
    ROOT
    / "data"
    / "reconciliation"
    / "pre-phase4-acquisition-v1"
    / "candidate-observations.jsonl"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def artifact(
    source_id: str,
    path: str,
    url: str,
    publisher: str,
    mime_type: str,
    source_tier: str,
    notes: str,
    *,
    retrieval_method: str = "curl -L --fail",
    retrieved_at_utc: str | None = None,
    candidate_status: str = "RETRIEVED",
) -> dict[str, Any]:
    full_path = ROOT / path
    return {
        "record_type": "structured_artifact",
        "data_lane": "structured",
        "source_id": source_id,
        "artifact_id": source_id,
        "publisher": publisher,
        "source_url": url,
        "retrieved_at_utc": retrieved_at_utc,
        "content_hash_sha256": sha256(full_path),
        "local_path": path,
        "mime_type": mime_type,
        "original_filename": full_path.name,
        "source_tier": source_tier,
        "candidate_status": candidate_status,
        "acquisition_status": "RETRIEVED",
        "retrieval_method": retrieval_method,
        "notes": notes,
    }


def document(
    document_id: str,
    source_id: str,
    path: str,
    url: str,
    publisher: str,
    document_type: str,
    title: str,
    notes: str,
    *,
    issued_date: str | None = None,
    effective_date: str | None = None,
    document_number: str | None = None,
    retrieval_method: str = "curl -L --fail",
    retrieved_at_utc: str | None = None,
    acquisition_status: str = "RETRIEVED",
    source_tier: str = "primary",
) -> dict[str, Any]:
    full_path = ROOT / path
    return {
        "record_type": "document",
        "data_lane": "unstructured",
        "document_id": document_id,
        "source_id": source_id,
        "publisher": publisher,
        "document_type": document_type,
        "title": title,
        "source_url": url,
        "retrieved_at_utc": retrieved_at_utc,
        "content_hash_sha256": sha256(full_path),
        "local_path": path,
        "mime_type": "application/pdf" if full_path.suffix.lower() == ".pdf" else "text/html",
        "original_filename": full_path.name,
        "language": "vi",
        "issued_date": issued_date,
        "effective_date": effective_date,
        "document_number": document_number,
        "jurisdiction": "Vietnam",
        "source_tier": source_tier,
        "acquisition_status": acquisition_status,
        "retrieval_method": retrieval_method,
        "notes": notes,
    }


def failed_route(
    source_id: str,
    url: str,
    publisher: str,
    failure_category: str,
    result: str,
    attempted: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "record_type": "failed_route",
        "data_lane": "structured_or_unstructured",
        "source_id": source_id,
        "publisher": publisher,
        "source_url": url,
        "retrieved_at_utc": now_utc(),
        "acquisition_status": failure_category,
        "http_or_result": result,
        "attempted_action": attempted,
        "notes": notes,
        "local_path": None,
        "content_hash_sha256": None,
    }


def build_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    previous = (
        "reused_existing_local_acquisition; exact artifact was already present in "
        "the prior tracked macro manifest, with original retrieval timestamp unavailable"
    )
    existing_time = None
    current_time = now_utc()

    records = [
        artifact(
            "nso_statistical_summary_2024_pdf",
            "data/raw/pre-phase4-acquisition-v1/structured/nso/nien-giam-tom-tat-2024.pdf",
            "https://www.nso.gov.vn/wp-content/uploads/2026/01/Nien-giam-tom-tat-2024.pdf",
            "National Statistics Office of Vietnam",
            "application/pdf",
            "primary",
            "Official 2024 statistical summary; page 15 reports year-end economic credit growth of 15.1%.",
            retrieved_at_utc=current_time,
        ),
        artifact(
            "nso_statistical_yearbook_2024_pdf",
            "data/raw/pre-phase4-acquisition-v1/structured/nso/NGTK-Cuc-TK-2024_BQ.pdf",
            "https://www.nso.gov.vn/wp-content/uploads/2025/06/NGTK-Cuc-TK-2024_BQ.pdf",
            "National Statistics Office of Vietnam",
            "application/pdf",
            "primary",
            "Official yearbook acquired for annual banking tables and native aggregate-source investigation.",
            retrieved_at_utc=current_time,
        ),
        artifact(
            "sbv_policy_rates_history_api",
            "data/raw/pre-phase4-acquisition-v1/structured/sbv/sbv-policy-rates-history-api.json",
            "https://sbv.gov.vn/o/headless-delivery/v1.0/content-structures/3450482/structured-contents?pageSize=100&sort=datePublished:desc",
            "State Bank of Vietnam",
            "application/json",
            "primary",
            "Prior official acquisition; record 3451452 identifies refinancing 4.500% and Decision 1123/QD-NHNN.",
            retrieval_method=previous,
            retrieved_at_utc=existing_time,
        ),
        artifact(
            "sbv_policy_rates_overview_page",
            "data/raw/pre-phase4-acquisition-v1/structured/sbv/sbv-policy-rates-overview.html",
            "https://sbv.gov.vn/vi/l%C3%A3i-su%E1%BA%A5t1",
            "State Bank of Vietnam",
            "text/html",
            "primary",
            "Prior official policy-rate overview artifact; supporting page only, not a new observation.",
            retrieval_method=previous,
            retrieved_at_utc=existing_time,
        ),
        artifact(
            "sbv_policy_rates_regulated_page",
            "data/raw/pre-phase4-acquisition-v1/structured/sbv/sbv-policy-rates-regulated.html",
            "https://sbv.gov.vn/vi/l%C3%A3i-su%E1%BA%A5t-nhnn-quy-%C4%91%E1%BB%8Bnh",
            "State Bank of Vietnam",
            "text/html",
            "primary",
            "Prior official supporting page; stale display fields remain excluded by the frozen adjudication.",
            retrieval_method=previous,
            retrieved_at_utc=existing_time,
        ),
        artifact(
            "sbv_credit_statistics_route",
            "data/raw/pre-phase4-acquisition-v1/structured/sbv/sbv-credit-statistics-route.html",
            "https://www.sbv.gov.vn/vi/du-no-tin-dung-doi-voi-nen-kt-dttktt",
            "State Bank of Vietnam",
            "text/html",
            "primary",
            "Official statistical route for credit outstanding and growth; exact 2024 year-end row still requires reconciliation.",
            retrieval_method=previous,
            retrieved_at_utc=existing_time,
        ),
        artifact(
            "sbv_credit_statistics_api_2024",
            "data/raw/pre-phase4-acquisition-v1/structured/sbv/sbv-credit-statistics-api-2024.json",
            "https://sbv.gov.vn/o/headless-delivery/v1.0/structured-contents",
            "State Bank of Vietnam",
            "application/json",
            "primary",
            "Prior official 2024 API response; totalCount=0 in the bounded query, retained as negative evidence.",
            retrieval_method=previous,
            retrieved_at_utc=existing_time,
        ),
        document(
            "law_credit_institutions_32_2024_part1",
            "chinhphu_law_32_2024_part1",
            "data/raw/pre-phase4-acquisition-v1/documents/laws/Luat-Cac-To-Chuc-Tin-Dung-32-2024-QH15-part1.pdf",
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/32-2024-qh15_1.pdf",
            "Government of Vietnam Portal",
            "law",
            "Luật Các tổ chức tín dụng số 32/2024/QH15, phần 1",
            "Original official PDF artifact; downloaded from the Government portal attachment.",
            issued_date="2024-01-18",
            effective_date="2024-07-01",
            document_number="32/2024/QH15",
            retrieved_at_utc=current_time,
        ),
        document(
            "law_credit_institutions_32_2024_part2",
            "chinhphu_law_32_2024_part2",
            "data/raw/pre-phase4-acquisition-v1/documents/laws/Luat-Cac-To-Chuc-Tin-Dung-32-2024-QH15-part2.pdf",
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/9/32-2024-qh15_2.pdf",
            "Government of Vietnam Portal",
            "law",
            "Luật Các tổ chức tín dụng số 32/2024/QH15, phần 2",
            "Original official PDF artifact; downloaded from the Government portal attachment.",
            issued_date="2024-01-18",
            effective_date="2024-07-01",
            document_number="32/2024/QH15",
            retrieved_at_utc=current_time,
        ),
        document(
            "sbv_circular_06_2024",
            "chinhphu_circular_06_2024",
            "data/raw/pre-phase4-acquisition-v1/documents/circulars/Thong-tu-06-2024-TT-NHNN.pdf",
            "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/7/06-nhnn.pdf",
            "Government of Vietnam Portal / State Bank of Vietnam",
            "circular",
            "Thông tư 06/2024/TT-NHNN",
            "Official regulation extending restructuring/kept debt-group treatment through 31/12/2024; unstructured corpus only.",
            issued_date="2024-06-18",
            effective_date="2024-06-18",
            document_number="06/2024/TT-NHNN",
            retrieved_at_utc=current_time,
        ),
        document(
            "sbv_circular_09_2024_official_page",
            "congbao_circular_09_2024",
            "data/raw/pre-phase4-acquisition-v1/documents/circulars/Thong-tu-09-2024-TT-NHNN.html",
            "https://congbao.chinhphu.vn/van-ban/thong-tu-so-09-2024-tt-nhnn-42148.htm",
            "Electronic Gazette of the Government of Vietnam",
            "circular_publication_page",
            "Thông tư 09/2024/TT-NHNN",
            "Official publication page retained because the linked CDN PDF returned 502 during acquisition; no semantic extraction performed.",
            issued_date="2024-06-28",
            effective_date="2024-07-01",
            document_number="09/2024/TT-NHNN",
            retrieved_at_utc=current_time,
        ),
        document(
            "nso_banking_statistics_landing",
            "nso_banking_statistics_landing_source",
            "data/raw/pre-phase4-acquisition-v1/documents/sector-reports/nso-banking-statistics-landing.html",
            "https://www.nso.gov.vn/en/banking-insurance-and-state-budget/",
            "National Statistics Office of Vietnam",
            "statistical_catalogue",
            "NSO banking, insurance and state-budget statistical tables",
            "Official catalogue page identifying annual 31 December banking tables; retained as unstructured source metadata.",
            retrieved_at_utc=current_time,
        ),
        document(
            "nso_statistical_yearbook_2024_landing",
            "nso_statistical_yearbook_2024_landing_source",
            "data/raw/pre-phase4-acquisition-v1/documents/sector-reports/nso-statistical-yearbook-2024-landing.html",
            "https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2025/06/nien-giam-thong-ke-2024/",
            "National Statistics Office of Vietnam",
            "statistical_publication_page",
            "Niên giám thống kê 2024 publication page",
            "Official landing page for the acquired yearbook; useful for publication metadata and provenance.",
            issued_date="2025-06-01",
            retrieved_at_utc=current_time,
        ),
        document(
            "sbv_policy_rate_context_2023",
            "sbv_policy_rate_context_2023_source",
            "data/raw/pre-phase4-acquisition-v1/documents/decisions/sbv-policy-rate-decision-context-2023-06-16.html",
            "https://baochinhphu.vn/ngan-hang-nha-nuoc-tiep-tuc-dieu-chinh-lai-suat-dieu-hanh-102230616132756661.htm",
            "Government of Vietnam Portal",
            "official_context_article",
            "SBV policy-rate adjustment context, 16/06/2023",
            "Official Government context article retained as cross-check/discovery only; not the primary observation source.",
            issued_date="2023-06-16",
            retrieved_at_utc=current_time,
            source_tier="secondary_official_context",
        ),
        document(
            "sbv_credit_growth_2024_09_17",
            "sbv_credit_growth_2024_09_17_source",
            "data/raw/pre-phase4-acquisition-v1/documents/macro-reports/sbv-credit-growth-2024-09-17.html",
            "https://sbv.gov.vn/vi/w/sbv615626",
            "State Bank of Vietnam",
            "official_article",
            "SBV credit growth update at 17/09/2024",
            "Official article retained as out-of-period negative evidence: 7.38% at 17/09/2024 and 15% orientation.",
            issued_date="2024-09-17",
            retrieved_at_utc=existing_time,
            retrieval_method=previous,
        ),
        document(
            "sbv_credit_growth_lead_2025_03_18",
            "sbv_credit_growth_lead_2025_03_18_source",
            "data/raw/pre-phase4-acquisition-v1/documents/macro-reports/sbv-credit-growth-lead-2025-03-18.html",
            "https://sbv.gov.vn/vi/w/sbv624617",
            "State Bank of Vietnam / Tạp chí Ngân hàng",
            "research_article",
            "2024 credit growth research lead reporting 15.08%",
            "SBV-hosted research/commentary artifact; discovery/cross-check only, never promoted as primary Gold evidence.",
            issued_date="2025-03-18",
            retrieved_at_utc=existing_time,
            retrieval_method=previous,
            source_tier="secondary_research_hosted_on_official_domain",
        ),
    ]

    failed = [
        failed_route(
            "vbpl_law_32_direct_route",
            "https://vbpl.vn/FileData/TW/Lists/vbpq/Attachments/166170/VanBanGoc_Luat%20TCTD%20so%2032.%20ban%20hanh.pdf",
            "National Legal Database",
            "ACCESS_DENIED",
            "HTTP 403",
            "curl -L --fail direct PDF retrieval",
            "An alternate official Government Portal representation was acquired successfully.",
        ),
        failed_route(
            "sbv_policy_rates_current_route",
            "https://sbv.gov.vn/vi/l%C3%A3i-su%E1%BA%A5t1",
            "State Bank of Vietnam",
            "WAF_BLOCKED",
            "HTTP 403",
            "curl -L --fail current page retrieval",
            "Prior local official artifact was reused; no WAF circumvention attempted.",
        ),
        failed_route(
            "sbv_credit_statistics_current_route",
            "https://www.sbv.gov.vn/vi/du-no-tin-dung-doi-voi-nen-kt-dttktt",
            "State Bank of Vietnam",
            "WAF_BLOCKED",
            "HTTP 403",
            "curl -L --fail current route retrieval",
            "Prior local official route artifact was reused; year-end query remains unresolved.",
        ),
        failed_route(
            "sbv_sector_survey_pdf",
            "https://www.sbv.gov.vn/webcenter/contentattachfile/idcplg?dDocName=SBV586620&filename=558038.pdf",
            "State Bank of Vietnam",
            "WAF_BLOCKED",
            "HTTP 403",
            "curl -L --fail official PDF retrieval",
            "The route was recorded and not bypassed; NSO yearbook remains the acquired native aggregate source package.",
        ),
        failed_route(
            "congbao_circular_09_pdf_cdn",
            "https://g7.cdnchinhphu.vn/api/download/stream?file_name=2024_781%20%2B%20782_09-2024-TT-NHNN.pdf",
            "Electronic Gazette of the Government of Vietnam",
            "UPSTREAM_ERROR",
            "HTTP 502",
            "official publication-page PDF attachment retrieval",
            "The official publication HTML page was acquired instead; no content was inferred from the failed PDF route.",
        ),
        failed_route(
            "sbv_credit_statistics_api_2024_new_attempt",
            "https://sbv.gov.vn/o/headless-delivery/v1.0/structured-contents",
            "State Bank of Vietnam",
            "WAF_BLOCKED",
            "HTTP 403",
            "direct public API retrieval",
            "Existing prior API response with totalCount=0 was reused as negative evidence.",
        ),
    ]
    return records, failed


def build_candidates(source_ids: set[str]) -> list[dict[str, Any]]:
    candidates = [
        {
            "candidate_id": "macro_policy_rate_nso_sbv_candidate_v1",
            "entity": "VN",
            "metric_id": "macro.policy_rate",
            "value": 4.5,
            "unit": "percent_per_annum",
            "period": "2024_Q4",
            "as_of_date": "2024-12-31",
            "period_basis": "quarter_end_state",
            "effective_from": "2023-06-19",
            "source_id": "sbv_policy_rates_history_api",
            "source_locator": "content_structure=3450482;record=3451452;banglaiSuats[1];loaiLaiSuat=Lãi suất tái cấp vốn",
            "quality_status": "review_required",
            "reason": "Existing two independent review passes are preserved; acquisition package has not promoted a new Gold row.",
            "raw_value": "4,500%",
            "normalization_notes": "SBV refinancing rate; Decision 1123/QD-NHNN; state carried to 2024-12-31.",
        },
        {
            "candidate_id": "macro_credit_growth_nso_2024_candidate_v1",
            "entity": "VN",
            "metric_id": "macro.credit_growth",
            "value": 15.1,
            "unit": "percent",
            "period": "2024_Q4",
            "as_of_date": "2024-12-31",
            "period_basis": "annual_change_vs_end_2023",
            "source_id": "nso_statistical_summary_2024_pdf",
            "source_locator": "PDF page 15 / printed page 14; section summary sentence beginning Tại thời điểm 31/12/2024",
            "quality_status": "review_required",
            "reason": "Official year-end candidate requires reconciliation of definition, rounding and publication vintage against the frozen contract.",
            "raw_value": "15,1%",
            "normalization_notes": "Source-native rounded value; do not replace the prior 15.08% research lead or derive an exact value without official stock inputs.",
        },
        {
            "candidate_id": "sector_system_credit_growth_nso_candidate_v1",
            "entity": "VN_BANKING_SYSTEM",
            "proposed_metric_id": "sector.system_credit_growth",
            "value": 15.1,
            "unit": "percent",
            "period": "2024_Q4",
            "as_of_date": "2024-12-31",
            "period_basis": "annual_change_vs_end_2023",
            "source_id": "nso_statistical_summary_2024_pdf",
            "source_locator": "PDF page 15 / printed page 14; credit growth of the economy sentence",
            "quality_status": "review_required",
            "reason": "Aggregate candidate may support a sector capability, but domain/entity mapping must be explicitly reconciled before canonical metric creation.",
            "raw_value": "15,1%",
            "normalization_notes": "Proposed sector ID only; not accepted and not a five-bank peer statistic.",
        },
        {
            "candidate_id": "sector_system_credit_outstanding_yearbook_candidate_v1",
            "entity": "VN_BANKING_SYSTEM",
            "proposed_metric_id": "sector.system_credit_outstanding",
            "value": None,
            "unit": "VND",
            "period": "2024_Q4",
            "as_of_date": "2024-12-31",
            "period_basis": "point_in_time_year_end",
            "source_id": "nso_statistical_yearbook_2024_pdf",
            "source_locator": "Banking statistics tables; exact table/row mapping pending controlled extraction",
            "quality_status": "review_required",
            "reason": "Official aggregate source acquired, but no numeric row is registered until table/row semantics are machine-reconciled.",
            "raw_value": None,
            "normalization_notes": "Do not map deposits or total liquidity to credit outstanding.",
        },
        {
            "candidate_id": "sector_system_npl_missing_v1",
            "entity": "VN_BANKING_SYSTEM",
            "proposed_metric_id": "sector.system_npl_ratio",
            "value": None,
            "unit": "percent",
            "period": "2024_Q4",
            "as_of_date": None,
            "period_basis": "point_in_time_year_end",
            "source_id": None,
            "source_locator": None,
            "quality_status": "missing",
            "reason": "DATA_UNAVAILABLE: no sufficiently clear official 2024 year-end system NPL observation acquired in this bounded pass.",
            "raw_value": None,
            "normalization_notes": "No estimate, peer-derived substitute or secondary value inserted.",
        },
    ]
    missing = {
        candidate["source_id"]
        for candidate in candidates
        if candidate.get("source_id")
    } - source_ids
    if missing:
        raise ValueError(f"candidate references unknown source IDs: {sorted(missing)}")
    return candidates


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"missing acquisition registry: {path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path}:{line_number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"registry row is not an object at {path}:{line_number}")
        rows.append(row)
    return rows


def validate_manifest(records: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    if not records:
        raise ValueError("acquisition manifest is empty")

    ids = [row.get("source_id") for row in records]
    if any(not source_id for source_id in ids):
        raise ValueError("manifest row is missing source_id")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate source_id in acquisition manifest")

    document_ids = [
        row.get("document_id")
        for row in records
        if row.get("record_type") == "document"
    ]
    if any(not document_id for document_id in document_ids):
        raise ValueError("document row is missing document_id")
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("duplicate document_id in acquisition manifest")

    retrieved_source_ids: set[str] = set()
    failed_source_ids: set[str] = set()
    for row in records:
        record_type = row.get("record_type")
        source_id = row["source_id"]
        if record_type == "failed_route":
            if row.get("local_path") is not None or row.get("content_hash_sha256") is not None:
                raise ValueError(f"failed route contains a local artifact: {source_id}")
            failed_source_ids.add(source_id)
            continue
        if record_type not in {"structured_artifact", "document"}:
            raise ValueError(f"unknown manifest record_type: {record_type}")
        local_path = row.get("local_path")
        expected_hash = row.get("content_hash_sha256")
        if not local_path or not expected_hash:
            raise ValueError(f"retrieved row lacks path/hash: {source_id}")
        path = ROOT / local_path
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"missing or empty acquisition artifact: {path}")
        if sha256(path) != expected_hash:
            raise ValueError(f"artifact hash mismatch: {source_id}")
        retrieved_source_ids.add(source_id)

    if retrieved_source_ids & failed_source_ids:
        raise ValueError("source_id is both retrieved and failed")
    return retrieved_source_ids, failed_source_ids


def validate_candidates(
    candidates: list[dict[str, Any]],
    retrieved_source_ids: set[str],
    failed_source_ids: set[str],
) -> None:
    if not candidates:
        raise ValueError("candidate registry is empty")
    for candidate in candidates:
        source_id = candidate.get("source_id")
        quality_status = candidate.get("quality_status")
        if quality_status not in {"review_required", "missing"}:
            raise ValueError(f"candidate has unsupported promotion state: {candidate.get('candidate_id')}")
        if source_id is not None:
            if source_id in failed_source_ids:
                raise ValueError(f"candidate references failed route: {source_id}")
            if source_id not in retrieved_source_ids:
                raise ValueError(f"candidate references unknown source ID: {source_id}")
        if quality_status == "missing":
            if candidate.get("value") is not None or "DATA_UNAVAILABLE" not in candidate.get("reason", ""):
                raise ValueError(f"missing candidate lacks explicit unavailable semantics: {candidate.get('candidate_id')}")


def run() -> dict[str, int]:
    """Verify the committed package without rewriting any acquisition metadata."""
    records = read_jsonl(MANIFEST_PATH)
    candidates = read_jsonl(CANDIDATE_PATH)
    retrieved_source_ids, failed_source_ids = validate_manifest(records)
    validate_candidates(candidates, retrieved_source_ids, failed_source_ids)
    return {
        "retrieved_records": len(retrieved_source_ids),
        "failed_routes": len(failed_source_ids),
        "candidate_observations": len(candidates),
        "documents": sum(row.get("record_type") == "document" for row in records),
        "structured_artifacts": sum(
            row.get("record_type") == "structured_artifact" for row in records
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="verify the committed package")
    args = parser.parse_args()
    if not args.verify:
        parser.error("only --verify is supported in this acquisition-only script")
    print(json.dumps(run(), sort_keys=True))


if __name__ == "__main__":
    main()
