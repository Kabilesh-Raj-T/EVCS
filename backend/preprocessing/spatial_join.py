"""Spatial joins and nearest-distance helpers for India demand features."""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from .clean_data import display_name, normalize_name
from .config import CURRENT_ADM1_GEOJSON, INDIA_BOUNDS, RAW_DIR


logger = logging.getLogger(__name__)


def find_boundary_file(level: str) -> Path | None:
    """Find a boundary file in raw data, preferring geoBoundaries naming."""

    patterns = [
        f"*geoboundaries*{level}*.geojson",
        f"*{level}*.geojson",
        f"*{level}*.json",
        f"*{level}*.gpkg",
        f"*{level}*.shp",
    ]
    for pattern in patterns:
        matches = sorted(RAW_DIR.glob(pattern))
        if matches:
            return matches[0]
    if level.lower() == "adm1" and CURRENT_ADM1_GEOJSON.exists():
        return CURRENT_ADM1_GEOJSON
    return None


def load_boundary(level: str) -> gpd.GeoDataFrame | None:
    """Load an administrative boundary layer and standardize its CRS."""

    patterns = [
        f"*geoboundaries*{level}*.geojson",
        f"*{level}*.geojson",
        f"*{level}*.json",
        f"*{level}*.gpkg",
        f"*{level}*.shp",
    ]
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(sorted(RAW_DIR.glob(pattern)))
    if level.lower() == "adm1" and CURRENT_ADM1_GEOJSON.exists():
        paths.append(CURRENT_ADM1_GEOJSON)

    seen: set[Path] = set()
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        try:
            gdf = gpd.read_file(path).to_crs(epsg=4326)
            if gdf.empty:
                logger.warning("Boundary file is empty: %s", path)
                continue
            logger.info("Loaded %s boundary from %s (%d features)", level, path, len(gdf))
            return gdf
        except Exception as exc:
            logger.warning("Skipping unreadable %s boundary file %s: %s", level, path, exc)

    logger.warning("No usable %s boundary file found", level)
    return None


def boundary_name_column(gdf: gpd.GeoDataFrame, level: str) -> str | None:
    """Detect the most likely name column for ADM1/ADM2 data."""

    candidates = {
        "adm1": ["shapeName", "shapeName_1", "NAME_1", "state", "State", "ST_NM", "name"],
        "adm2": ["shapeName", "shapeName_2", "NAME_2", "district", "District", "DISTRICT", "dtname", "name"],
    }[level.lower()]
    for col in candidates:
        if col in gdf.columns:
            return col
    non_geom = [col for col in gdf.columns if col != gdf.geometry.name]
    return non_geom[0] if non_geom else None


def india_geometry(adm1: gpd.GeoDataFrame | None = None):
    """Return a dissolved India geometry, falling back to configured bounds."""

    if adm1 is not None and not adm1.empty:
        if hasattr(adm1.geometry, "union_all"):
            return adm1.geometry.union_all()
        return adm1.geometry.unary_union
    return box(INDIA_BOUNDS["lon_min"], INDIA_BOUNDS["lat_min"], INDIA_BOUNDS["lon_max"], INDIA_BOUNDS["lat_max"])


def points_to_gdf(df: pd.DataFrame, lat_col: str = "latitude", lon_col: str = "longitude") -> gpd.GeoDataFrame:
    """Convert a latitude/longitude dataframe to an EPSG:4326 GeoDataFrame."""

    return gpd.GeoDataFrame(df.copy(), geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs="EPSG:4326")


def assign_administrative_regions(
    points: pd.DataFrame,
    adm1: gpd.GeoDataFrame | None,
    adm2: gpd.GeoDataFrame | None,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
) -> pd.DataFrame:
    """Assign state and district names to point candidates using spatial joins."""

    out = points.copy()
    out["state"] = out.get("state", "")
    out["district"] = out.get("district", "")

    point_gdf = points_to_gdf(out, lat_col, lon_col)

    if adm1 is not None and not adm1.empty:
        state_col = boundary_name_column(adm1, "adm1")
        joined = gpd.sjoin(point_gdf, adm1[[state_col, "geometry"]], how="left", predicate="within")
        out["state"] = joined[state_col].map(display_name).fillna(out["state"]).to_numpy()

    if adm2 is not None and not adm2.empty:
        district_col = boundary_name_column(adm2, "adm2")
        joined = gpd.sjoin(point_gdf, adm2[[district_col, "geometry"]], how="left", predicate="within")
        out["district"] = joined[district_col].map(display_name).fillna(out["district"]).to_numpy()

    out["state_key"] = out["state"].map(normalize_name)
    out["district_key"] = out["district"].map(normalize_name)
    return out


def coverage_by_region(df: pd.DataFrame) -> dict[str, object]:
    """Summarize record coverage by state and district."""

    state_counts = df["state"].fillna("").replace("", "Unknown").value_counts().to_dict() if "state" in df else {}
    district_counts = (
        df["district"].fillna("").replace("", "Unknown").value_counts().head(500).to_dict()
        if "district" in df
        else {}
    )
    return {"by_state": state_counts, "by_district": district_counts}
