"""Provider-neutral proof that the application boundary is storage agnostic.

The helper intentionally composes only application contracts and runtime
tools.  Concrete providers remain responsible for translating their own
storage into those contracts.
"""

from __future__ import annotations

from .analysis_request import AnalysisRequest
from .application_runtime import ApplicationRuntimeContext
from .dataset_contract import CanonicalObservation, DatasetRef
from .dataset_provider import FinancialDatasetProvider
from .dataset_tool_runtime import DatasetToolRuntime


def run_metric_probe(
    provider: FinancialDatasetProvider,
    dataset_ref: DatasetRef,
    request: AnalysisRequest,
    *,
    entity_id: str,
    period_id: str,
    metric_id: str,
) -> CanonicalObservation | None:
    """Read one scoped observation through the portable application path."""

    if request.dataset_ref != dataset_ref:
        raise ValueError("dataset reference does not match analysis request")
    context = ApplicationRuntimeContext.from_request(request, provider)
    return DatasetToolRuntime(context).get_metric(entity_id, period_id, metric_id)
