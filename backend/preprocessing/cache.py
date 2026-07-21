"""Reusable cache helpers for data files and spatial indexes."""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.spatial import KDTree

from .config import CACHE_DIR, DATA_DIR, PROCESSED_DIR, RAW_DIR, REPORTS_DIR


logger = logging.getLogger(__name__)
EARTH_RADIUS_KM = 6371.0


@dataclass
class SpatialIndex:
    """A KD-tree over WGS84 latitude/longitude coordinates."""

    name: str
    tree: KDTree | None
    coords: np.ndarray
    source_columns: tuple[str, str]

    @property
    def is_empty(self) -> bool:
        return self.tree is None or self.coords.size == 0


def ensure_directories() -> None:
    """Create all data and report directories used by the preprocessing layer."""

    for path in (DATA_DIR, RAW_DIR, PROCESSED_DIR, CACHE_DIR, REPORTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def latlon_to_unit_xyz(coords: np.ndarray) -> np.ndarray:
    """Convert latitude/longitude pairs to unit-sphere XYZ coordinates."""

    if coords.size == 0:
        return np.empty((0, 3), dtype=float)
    lat = np.radians(coords[:, 0])
    lon = np.radians(coords[:, 1])
    return np.column_stack(
        (
            np.cos(lat) * np.cos(lon),
            np.cos(lat) * np.sin(lon),
            np.sin(lat),
        )
    )


def chord_to_great_circle_km(chord_dist: np.ndarray | float) -> np.ndarray | float:
    """Convert unit-sphere chord distance to great-circle kilometers."""

    half = np.clip(np.asarray(chord_dist) / 2.0, 0.0, 1.0)
    return EARTH_RADIUS_KM * (2.0 * np.arcsin(half))


def build_spatial_index(
    df: pd.DataFrame,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    name: str = "unnamed",
) -> SpatialIndex:
    """Build a spatial index for nearest-neighbor distance queries."""

    if df is None or df.empty or lat_col not in df.columns or lon_col not in df.columns:
        return SpatialIndex(name=name, tree=None, coords=np.empty((0, 2)), source_columns=(lat_col, lon_col))

    coords_df = df[[lat_col, lon_col]].apply(pd.to_numeric, errors="coerce").dropna()
    coords = coords_df.to_numpy(dtype=float)
    if coords.size == 0:
        return SpatialIndex(name=name, tree=None, coords=np.empty((0, 2)), source_columns=(lat_col, lon_col))

    xyz = latlon_to_unit_xyz(coords)
    return SpatialIndex(name=name, tree=KDTree(xyz), coords=coords, source_columns=(lat_col, lon_col))


def query_nearest_distance_km(index: SpatialIndex, points: pd.DataFrame, lat_col: str, lon_col: str) -> np.ndarray:
    """Return nearest distance in kilometers from points to a cached spatial index."""

    if index.is_empty or points.empty:
        return np.full(len(points), np.nan, dtype=float)
    query_coords = points[[lat_col, lon_col]].to_numpy(dtype=float)
    query_xyz = latlon_to_unit_xyz(query_coords)
    chord_dist, _ = index.tree.query(query_xyz, k=1)
    return np.asarray(chord_to_great_circle_km(chord_dist), dtype=float)


def cache_path(name: str) -> Path:
    """Return the pickle cache path for a named object."""

    safe_name = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in name.lower())
    return CACHE_DIR / f"{safe_name}.pkl"


def save_pickle(name: str, obj: Any) -> Path:
    """Persist a reusable object into the preprocessing cache."""

    ensure_directories()
    path = cache_path(name)
    with path.open("wb") as fh:
        pickle.dump(obj, fh)
    logger.info("Saved cache: %s", path)
    return path


def load_pickle(name: str) -> Any | None:
    """Load a cached object if it exists."""

    path = cache_path(name)
    if not path.exists():
        return None
    with path.open("rb") as fh:
        logger.info("Loaded cache: %s", path)
        return pickle.load(fh)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON document with stable indentation."""

    ensure_directories()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object is not JSON serializable: {type(value)!r}")


def existing_files(paths: Iterable[Path]) -> list[str]:
    """Return existing paths as strings for reports."""

    return [str(path) for path in paths if path.exists()]

