"""Cleaning utilities for source datasets used by demand feature generation."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable

import geopandas as gpd
import numpy as np
import pandas as pd

from .config import INDIA_BOUNDS


logger = logging.getLogger(__name__)

STATE_DISPLAY_OVERRIDES = {
    "andamanandnicobar": "Andaman & Nicobar",
    "andhrapradesh": "Andhra Pradesh",
    "arunachalpradesh": "Arunachal Pradesh",
    "dadraandnagarhaveli": "Dadra and Nagar Haveli",
    "damananddiu": "Daman and Diu",
    "gujarat": "Gujarat",
    "himachalpradesh": "Himachal Pradesh",
    "jammuandkashmir": "Jammu and Kashmir",
    "madhyapradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "nctofdelhi": "Delhi",
    "tamilnadu": "Tamil Nadu",
    "uttarpradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "westbengal": "West Bengal",
}


def normalize_name(value: object) -> str:
    """Normalize administrative names for joins."""

    if pd.isna(value):
        return ""
    text = " ".join(str(value).strip().split())
    return re.sub(r"[^a-z0-9]", "", text.lower())


def display_name(value: object) -> str:
    """Return a human-readable name with whitespace normalized."""

    if pd.isna(value):
        return ""
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(value))
    text = re.sub(r"[^A-Za-z0-9&().,'/\- ]+", " ", text)
    text = " ".join(text.strip().split())
    key = normalize_name(text)
    if key in STATE_DISPLAY_OVERRIDES:
        return STATE_DISPLAY_OVERRIDES[key]
    if not text or len(key) < 2:
        return ""
    return text.title() if text.isupper() else text


def detect_coordinate_columns(df: pd.DataFrame) -> tuple[str, str]:
    """Detect latitude and longitude columns in a tabular source."""

    lower_cols = {str(col).lower(): col for col in df.columns}
    for lat_key, lon_key in (
        ("latitude_num", "longitude_num"),
        ("latitude_deg", "longitude_deg"),
        ("latitude", "longitude"),
        ("lat", "lon"),
        ("lat", "lng"),
    ):
        if lat_key in lower_cols and lon_key in lower_cols:
            return str(lower_cols[lat_key]), str(lower_cols[lon_key])

    lat_col = lon_col = None
    for col in df.columns:
        name = str(col).lower()
        if lat_col is None and "lat" in name:
            lat_col = str(col)
        if lon_col is None and ("lon" in name or "lng" in name or "long" in name):
            lon_col = str(col)
    if lat_col is None or lon_col is None:
        raise ValueError(f"Could not detect coordinate columns from {list(df.columns)}")
    return lat_col, lon_col


def to_numeric_coordinates(df: pd.DataFrame, lat_col: str, lon_col: str) -> pd.DataFrame:
    """Coerce latitude and longitude columns to numeric values."""

    out = df.copy()
    for col in (lat_col, lon_col):
        out[col] = (
            out[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
            .replace({"": np.nan, "nan": np.nan, "None": np.nan})
        )
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def validate_india_coordinates(df: pd.DataFrame, lat_col: str, lon_col: str) -> pd.DataFrame:
    """Keep rows with plausible India latitude/longitude coordinates."""

    before = len(df)
    valid = df[
        df[lat_col].between(INDIA_BOUNDS["lat_min"], INDIA_BOUNDS["lat_max"])
        & df[lon_col].between(INDIA_BOUNDS["lon_min"], INDIA_BOUNDS["lon_max"])
    ].copy()
    logger.info("Coordinate validation kept %d/%d rows", len(valid), before)
    return valid


def remove_duplicate_points(
    df: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    extra_cols: Iterable[str] | None = None,
    precision: int = 6,
) -> tuple[pd.DataFrame, int]:
    """Remove duplicate records using rounded coordinates and optional identity columns."""

    out = df.copy()
    out["_lat_key"] = out[lat_col].round(precision)
    out["_lon_key"] = out[lon_col].round(precision)
    subset = ["_lat_key", "_lon_key"]
    if extra_cols:
        subset.extend([col for col in extra_cols if col in out.columns])
    before = len(out)
    out = out.drop_duplicates(subset=subset).drop(columns=["_lat_key", "_lon_key"])
    return out.reset_index(drop=True), before - len(out)


def read_table(path: Path) -> pd.DataFrame:
    """Read CSV, Excel, Parquet, or JSON tabular data."""

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, low_memory=False)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in {".json", ".geojson"}:
        try:
            return gpd.read_file(path)
        except Exception:
            return pd.read_json(path)
    raise ValueError(f"Unsupported table format: {path}")


def standardize_point_dataset(df: pd.DataFrame, dataset_name: str) -> tuple[pd.DataFrame, dict[str, object]]:
    """Clean a point dataset and return standardized latitude/longitude columns."""

    lat_col, lon_col = detect_coordinate_columns(df)
    cleaned = to_numeric_coordinates(df, lat_col, lon_col).dropna(subset=[lat_col, lon_col]).copy()
    cleaned = validate_india_coordinates(cleaned, lat_col, lon_col)
    cleaned["latitude"] = cleaned[lat_col].astype(float)
    cleaned["longitude"] = cleaned[lon_col].astype(float)
    cleaned, duplicates_removed = remove_duplicate_points(cleaned, "latitude", "longitude")
    report = {
        "dataset": dataset_name,
        "records": len(cleaned),
        "duplicates_removed": duplicates_removed,
        "missing_values": cleaned.isna().sum().to_dict(),
    }
    return cleaned, report
