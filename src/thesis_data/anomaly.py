"""Deterministic verification triggers for prepared agent facts.

These rules identify cases that deserve a focused check; they do not label a
case as a contradiction.  Threshold-based rules are opt-in so a numeric
deviation cannot silently become an unregistered research assumption.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class AnomalyTrigger:
    """A deterministic request for bounded verification."""

    rule_id: str
    metric_id: str
    description: str
    affected_agents: tuple[str, ...]
    verification_request: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "metric_id": self.metric_id,
            "description": self.description,
            "affected_agents": list(self.affected_agents),
            "verification_request": self.verification_request,
        }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _validate_thresholds(
    thresholds: Mapping[str, float] | None,
) -> Mapping[str, float]:
    if thresholds is None:
        return {}
    for metric_id, threshold in thresholds.items():
        if not metric_id:
            raise ValueError("deviation threshold metric IDs must not be empty")
        value = _finite_number(threshold)
        if value is None or value <= 0:
            raise ValueError(
                f"deviation threshold for {metric_id} must be a positive finite number"
            )
    return thresholds


def detect_anomaly_triggers(
    facts: Mapping[str, Any],
    metric_ids: Sequence[str],
    *,
    deviation_thresholds: Mapping[str, float] | None = None,
) -> tuple[AnomalyTrigger, ...]:
    """Return stable, ordered verification triggers from one prepared context.

    Missing company and sector values are always triggerable.  A company versus
    sector deviation is emitted only when the caller explicitly registers a
    positive threshold for that metric and both sides have the same known unit.
    This prevents the trigger layer from guessing whether, for example, a
    ratio and a percentage are comparable.
    """

    normalized_metrics = tuple(metric_ids)
    if not normalized_metrics or any(not metric_id for metric_id in normalized_metrics):
        raise ValueError("metric_ids must contain at least one non-empty identifier")
    thresholds = _validate_thresholds(deviation_thresholds)

    company = _mapping(facts.get("company"))
    sector = _mapping(facts.get("sector"))
    company_metrics = _mapping(company.get("metrics"))
    sector_benchmarks = _mapping(sector.get("sector_benchmarks"))
    company_units = _mapping(company.get("metric_units"))
    sector_units = _mapping(sector.get("metric_units"))

    triggers: list[AnomalyTrigger] = []
    for metric_id in normalized_metrics:
        company_value = _finite_number(company_metrics.get(metric_id))
        if company_value is None:
            triggers.append(
                AnomalyTrigger(
                    rule_id="company_metric_missing",
                    metric_id=metric_id,
                    description=f"Company value for {metric_id} is missing or not accepted.",
                    affected_agents=("company",),
                    verification_request=(
                        f"Verify whether an accepted company observation exists for {metric_id}; "
                        "if not, preserve the missing reason."
                    ),
                )
            )

        sector_value = _finite_number(sector_benchmarks.get(metric_id))
        if sector_value is None:
            triggers.append(
                AnomalyTrigger(
                    rule_id="sector_benchmark_missing",
                    metric_id=metric_id,
                    description=f"Sector benchmark for {metric_id} is missing or not accepted.",
                    affected_agents=("sector",),
                    verification_request=(
                        f"Verify whether an accepted sector benchmark exists for {metric_id}; "
                        "if not, preserve the missing reason."
                    ),
                )
            )
            continue

        threshold = thresholds.get(metric_id)
        company_unit = company_units.get(metric_id)
        sector_unit = sector_units.get(metric_id)
        if (
            company_value is not None
            and threshold is not None
            and company_unit == sector_unit
            and isinstance(company_unit, str)
            and company_unit.strip()
            and company_unit != "unknown"
            and abs(company_value - sector_value) > float(threshold)
        ):
            triggers.append(
                AnomalyTrigger(
                    rule_id="company_sector_deviation",
                    metric_id=metric_id,
                    description=(
                        f"Company value {company_value:g} for {metric_id} differs from "
                        f"the sector benchmark {sector_value:g} by more than "
                        f"{float(threshold):g} {company_unit}."
                    ),
                    affected_agents=("company", "sector", "orchestrator"),
                    verification_request=(
                        f"Verify the definition, unit, period, and source support for the "
                        f"company and sector values of {metric_id} before explaining the deviation."
                    ),
                )
            )

    return tuple(triggers)
