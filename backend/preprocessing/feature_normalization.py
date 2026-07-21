"""Reusable 0-1 feature normalization methods."""

from __future__ import annotations

import logging
from typing import Iterable

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)
SUPPORTED_METHODS = {"minmax", "zscore", "robust"}


def _safe_minmax(values: pd.Series) -> pd.Series:
    valid = values.dropna()
    if valid.empty:
        return pd.Series(np.zeros(len(values)), index=values.index, dtype=float)
    min_value = valid.min()
    max_value = valid.max()
    if np.isclose(min_value, max_value):
        return pd.Series(np.zeros(len(values)), index=values.index, dtype=float)
    return ((values - min_value) / (max_value - min_value)).fillna(0.0).clip(0.0, 1.0)


def normalize_series(values: pd.Series, method: str = "minmax", invert: bool = False) -> pd.Series:
    """Normalize a numeric series to the 0-1 range."""

    method = method.lower().replace("_", "")
    if method not in SUPPORTED_METHODS:
        raise ValueError(f"Unsupported normalization method: {method}")

    numeric = pd.to_numeric(values, errors="coerce")
    if invert:
        numeric = -numeric

    if method == "minmax":
        return _safe_minmax(numeric)

    if method == "zscore":
        std = numeric.std(skipna=True)
        transformed = pd.Series(np.zeros(len(numeric)), index=numeric.index, dtype=float)
        if std and not np.isclose(std, 0):
            transformed = (numeric - numeric.mean(skipna=True)) / std
        return _safe_minmax(transformed)

    median = numeric.median(skipna=True)
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    transformed = pd.Series(np.zeros(len(numeric)), index=numeric.index, dtype=float)
    if iqr and not np.isclose(iqr, 0):
        transformed = (numeric - median) / iqr
    return _safe_minmax(transformed)


def normalize_features(
    df: pd.DataFrame,
    columns: Iterable[str],
    method: str = "minmax",
    invert_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Normalize selected columns in-place style and return a copied dataframe."""

    out = df.copy()
    inverted = set(invert_columns or [])
    for col in columns:
        if col not in out.columns:
            logger.warning("Skipping missing normalization column: %s", col)
            continue
        out[col] = normalize_series(out[col], method=method, invert=col in inverted)
    return out

