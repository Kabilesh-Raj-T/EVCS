"""Weighted demand scoring for candidate EV charging station locations."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .weights import DEFAULT_DEMAND_WEIGHTS


def validate_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Validate and normalize demand-score weights."""

    cleaned = {key: float(value) for key, value in weights.items()}
    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError("Demand weights must sum to a positive value")
    return {key: value / total for key, value in cleaned.items()}


def compute_demand_score(
    features: pd.DataFrame | pd.Series | Mapping[str, float],
    weights: Mapping[str, float] | None = None,
    renormalize_active: bool = True,
) -> pd.Series | float:
    """Compute a weighted demand score from normalized feature columns."""

    active_weights = validate_weights(weights or DEFAULT_DEMAND_WEIGHTS)

    if isinstance(features, pd.DataFrame):
        if renormalize_active:
            active_weights = {
                col: weight
                for col, weight in active_weights.items()
                if col in features.columns and pd.to_numeric(features[col], errors="coerce").fillna(0.0).gt(0).any()
            }
            active_weights = validate_weights(active_weights) if active_weights else {}
        score = pd.Series(0.0, index=features.index)
        for col, weight in active_weights.items():
            if col in features.columns:
                score = score + pd.to_numeric(features[col], errors="coerce").fillna(0.0) * weight
        return score.clip(0.0, 1.0)

    if isinstance(features, pd.Series):
        return float(sum(float(features.get(col, 0.0) or 0.0) * weight for col, weight in active_weights.items()))

    return float(sum(float(features.get(col, 0.0) or 0.0) * weight for col, weight in active_weights.items()))
