"""Evidence-root resolver for immutable source artifacts.

The receipt type is an internal boundary between filesystem verification and
canonical snapshot promotion. Callers cannot satisfy promotion with a hash
string alone: the resolver reads bytes beneath an explicit evidence root and
binds those bytes to the accepted primary source records.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Mapping, Sequence

from .dataset_contract import DatasetSource
from .schema import QualityStatus


_SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
_RECEIPT_SEAL = object()


@dataclass(frozen=True)
class _VerifiedArtifact:
    source_ref: str
    source_type: str
    source_tier: str
    content_hash: str
    content: bytes


class VerifiedSourceArtifacts:
    """Opaque verifier-created proof of source bytes for snapshot promotion."""

    __slots__ = ("_artifacts", "_seal")

    def __init__(self, artifacts: tuple[_VerifiedArtifact, ...], seal: object) -> None:
        if seal is not _RECEIPT_SEAL:
            raise TypeError("verified source receipts must come from the evidence-root resolver")
        self._artifacts = artifacts
        self._seal = seal

    def matches(self, sources: Sequence[DatasetSource]) -> bool:
        """Recheck record identity and hashes against the resolver-read bytes."""

        if self._seal is not _RECEIPT_SEAL:
            return False
        expected_sources = {
            source.source_ref: source
            for source in sources
            if source.validation_status is QualityStatus.VALID
            and getattr(source.source_tier, "value", source.source_tier) == "primary"
        }
        actual = {artifact.source_ref: artifact for artifact in self._artifacts}
        if set(actual) != set(expected_sources):
            return False
        for source_ref, source in expected_sources.items():
            artifact = actual[source_ref]
            tier = getattr(source.source_tier, "value", source.source_tier)
            if (
                artifact.source_type != source.source_type
                or artifact.source_tier != tier
                or artifact.content_hash.lower() != source.content_hash.lower()
                or hashlib.sha256(artifact.content).hexdigest() != source.content_hash.lower()
            ):
                return False
        return True


def resolve_primary_source_artifacts(
    *,
    sources: Sequence[DatasetSource],
    artifact_paths: Mapping[str, Path],
    evidence_root: Path,
) -> VerifiedSourceArtifacts:
    """Read and verify each accepted primary source beneath an explicit root."""

    root = Path(evidence_root).resolve()
    if not root.is_dir():
        raise ValueError("explicit evidence root must be an existing directory")

    required_sources = {
        source.source_ref: source
        for source in sources
        if source.validation_status is QualityStatus.VALID
        and getattr(source.source_tier, "value", source.source_tier) == "primary"
    }
    verified: list[_VerifiedArtifact] = []
    for source_ref, source in sorted(required_sources.items()):
        if not _SHA256_PATTERN.fullmatch(source.content_hash):
            raise ValueError("accepted primary source content hash must be an exact SHA-256")
        artifact_path = artifact_paths.get(source_ref)
        if artifact_path is None:
            raise ValueError(f"accepted primary source has no evidence artifact: {source_ref}")
        resolved_path = Path(artifact_path).resolve()
        if not resolved_path.is_relative_to(root):
            raise ValueError("primary source artifact must resolve inside the explicit evidence root")
        try:
            content = resolved_path.read_bytes()
        except OSError as exc:
            raise ValueError(f"primary source artifact is unavailable: {source_ref}") from exc
        digest = hashlib.sha256(content).hexdigest()
        if digest != source.content_hash.lower():
            raise ValueError(f"primary source artifact SHA-256 verification failed: {source_ref}")
        verified.append(
            _VerifiedArtifact(
                source_ref=source_ref,
                source_type=source.source_type,
                source_tier=getattr(source.source_tier, "value", source.source_tier),
                content_hash=digest,
                content=content,
            )
        )
    return VerifiedSourceArtifacts(tuple(verified), _RECEIPT_SEAL)
