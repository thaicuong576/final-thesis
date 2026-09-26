"""Source-verified operational snapshot promotion for reviewed bank packets."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path

from .bank_onboarding import load_verified_bank_dataset_candidate, verify_packet_artifacts
from .canonical_snapshot import materialize_canonical_snapshot
from .canonical_sqlite_provider import CanonicalSqliteDatasetProvider
from .dataset_contract import DatasetRef
from .dataset_provider import FinancialDatasetProvider
from .onboarding_contract import DatasetSnapshotMetadata
from .source_artifacts import resolve_primary_source_artifacts


_PROTECTED_STORE_STEMS = {
    "analysis_runs",
    "finance_master_v2",
    "gold_v5",
    "gold-v5",
}


@dataclass(frozen=True)
class OperationalBankSnapshot:
    """Accepted operational identity, provider and immutable byte hashes."""

    metadata: DatasetSnapshotMetadata
    provider: FinancialDatasetProvider
    source_content_hash: str
    snapshot_file_sha256: str
    dataset_ref: DatasetRef


def promote_bank_onboarding_snapshot(
    *,
    packet_path: Path,
    source_manifest_path: Path,
    reconciliation_path: Path,
    evidence_root: Path,
    target_path: Path,
) -> OperationalBankSnapshot:
    """Verify packet evidence and atomically create a separate operational DB.

    The target must be new and distinct from every input/evidence file. The
    generic canonical materializer performs the source/review/formula gates;
    the returned provider exposes the same DatasetProvider contract used by
    the Gold SQLite adapter.
    """

    packet_path = Path(packet_path).resolve()
    source_manifest_path = Path(source_manifest_path).resolve()
    reconciliation_path = Path(reconciliation_path).resolve()
    evidence_root = Path(evidence_root).resolve()
    target_path = Path(target_path).resolve()
    if target_path.stem.lower() in _PROTECTED_STORE_STEMS:
        raise ValueError("operational snapshot target cannot name a protected Gold or run-history store")
    for environment_name in ("SQLITE_DB_PATH", "ANALYSIS_RUNS_DB_PATH"):
        configured_path = os.environ.get(environment_name)
        if configured_path and target_path == Path(configured_path).resolve():
            raise ValueError("operational snapshot target cannot alias a configured analytical or run-history store")

    packet, candidate, raw_descriptor, report = load_verified_bank_dataset_candidate(
        packet_path=packet_path,
        source_manifest_path=source_manifest_path,
        reconciliation_path=reconciliation_path,
        evidence_root=evidence_root,
    )
    source_paths = tuple(
        (packet_path.parent / source.artifact_ref).resolve()
        for source in packet.sources
    )
    input_paths = {
        packet_path,
        source_manifest_path,
        reconciliation_path,
        *source_paths,
    }
    if target_path in input_paths:
        raise ValueError("operational snapshot target must be separate from source evidence")
    if target_path.exists():
        raise ValueError("operational snapshot target must be new and immutable")

    verified_paths, _ = verify_packet_artifacts(
        packet,
        packet_path=packet_path,
        source_manifest_path=source_manifest_path,
        evidence_root=evidence_root,
    )
    verified_source_artifacts = resolve_primary_source_artifacts(
        sources=candidate.all_sources,
        artifact_paths=verified_paths,
        evidence_root=evidence_root,
    )

    metadata = materialize_canonical_snapshot(
        target_path,
        candidate,
        raw_descriptor,
        report,
        verified_source_artifacts=verified_source_artifacts,
    )
    provider = CanonicalSqliteDatasetProvider(target_path, dataset_id=packet.dataset_id)
    dataset_ref = provider.current_dataset_ref()
    if (
        metadata.status.value != "accepted"
        or dataset_ref.dataset_id != metadata.dataset_id
        or dataset_ref.dataset_snapshot_id != metadata.dataset_snapshot_id
    ):
        raise ValueError("operational provider identity does not match accepted snapshot metadata")
    snapshot_file_sha256 = hashlib.sha256(target_path.read_bytes()).hexdigest()
    return OperationalBankSnapshot(
        metadata=metadata,
        provider=provider,
        source_content_hash=raw_descriptor.content_hash,
        snapshot_file_sha256=snapshot_file_sha256,
        dataset_ref=dataset_ref,
    )
