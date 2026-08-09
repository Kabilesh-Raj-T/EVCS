"""Weighted demand scoring for candidate EV charging station locations."""

from __future__ import annotations

import pandas as pd

from .weights import DEFAULT_DEMAND_WEIGHTS


def compute_demand_score(features: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.Series:
    """Return a weighted demand score in [0, 1] for each row of *features*.

    All four score columns are guaranteed present in the canonical
    demand_features.parquet dataset; weights are applied as a direct
    dot-product and the result is clipped to [0, 1].
    """
    w = weights or DEFAULT_DEMAND_WEIGHTS
    total = sum(w.values())
    if total <= 0:
        raise ValueError("Demand weights must sum to a positive value")
    normalized_weights = {k: v / total for k, v in w.items()}

    score = pd.Series(0.0, index=features.index)
    for col, weight in normalized_weights.items():
        if col in features.columns:
            score = score + features[col].clip(0.0, 1.0) * weight
    return score.clip(0.0, 1.0)
