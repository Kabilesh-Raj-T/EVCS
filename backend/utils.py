import re
import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from config import STATE_DISPLAY_OVERRIDES, INDIA_DEFAULT_BOUNDS, EARTH_RADIUS_KM

logger = logging.getLogger("evcsapi")

def normalize_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())

def payload_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()

def display_region_name(s: str) -> str:
    text = " ".join(str(s).strip().split())
    key = normalize_name(text)
    if not text or text.lower() == "nan":
        return ""
    if key in STATE_DISPLAY_OVERRIDES:
        return STATE_DISPLAY_OVERRIDES[key]
    if text.isupper():
        return text.title()
    return text

def bounds_to_dict(bounds):
    min_lon, min_lat, max_lon, max_lat = [float(v) for v in bounds]
    return {
        "lat_min": min_lat,
        "lat_max": max_lat,
        "lon_min": min_lon,
        "lon_max": max_lon,
    }

def first_existing_column(df: pd.DataFrame, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None

def coordinate_bounds(df: pd.DataFrame, lat_col: str, lon_col: str, padding=0.05):
    lat_min = float(df[lat_col].min())
    lat_max = float(df[lat_col].max())
    lon_min = float(df[lon_col].min())
    lon_max = float(df[lon_col].max())

    if lat_min == lat_max:
        lat_min -= padding
        lat_max += padding
    if lon_min == lon_max:
        lon_min -= padding
        lon_max += padding

    return {
        "lat_min": max(INDIA_DEFAULT_BOUNDS["lat_min"], lat_min - padding),
        "lat_max": min(INDIA_DEFAULT_BOUNDS["lat_max"], lat_max + padding),
        "lon_min": max(INDIA_DEFAULT_BOUNDS["lon_min"], lon_min - padding),
        "lon_max": min(INDIA_DEFAULT_BOUNDS["lon_max"], lon_max + padding),
    }

def detect_lat_lon_columns(df: pd.DataFrame):
    lower_cols = {c.lower(): c for c in df.columns}
    preferred_pairs = [
        ("latitude_num", "longitude_num"),
        ("latitude", "longitude"),
        ("lat", "lon"),
        ("lat", "lng"),
    ]
    for lat_key, lon_key in preferred_pairs:
        if lat_key in lower_cols and lon_key in lower_cols:
            return lower_cols[lat_key], lower_cols[lon_key]

    lat_col = lon_col = None
    for c in df.columns:
        n = c.lower()
        if lat_col is None and "lat" in n:
            lat_col = c
        if lon_col is None and ("lon" in n or "lng" in n or "long" in n):
            lon_col = c
    if lat_col is None or lon_col is None:
        raise ValueError(f"Could not detect lat/lon columns. Columns: {list(df.columns)}")
    return lat_col, lon_col

def to_float_series(s: pd.Series):
    cleaned = (
        s.astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace({"": np.nan})
    )
    return pd.to_numeric(cleaned, errors="coerce")

def merge_geometries(gdf: gpd.GeoDataFrame):
    if hasattr(gdf.geometry, "union_all"):
        return gdf.geometry.union_all()
    return gdf.geometry.unary_union

def geometry_from_series(series):
    gdf = gpd.GeoDataFrame(geometry=series, crs="EPSG:4326")
    return merge_geometries(gdf)

def filter_to_india(df: pd.DataFrame, lat_col: str, lon_col: str, polygon):
    station_points = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs="EPSG:4326",
    )
    in_india = station_points.intersects(polygon)
    filtered = df.loc[in_india.to_numpy()].copy()

    if filtered.empty and not df.empty:
        logger.warning("India boundary filter removed all rows; using coordinate-cleaned rows")
        filtered = df.copy()

    return filtered

def latlon_to_unit_xyz(lat_arr, lon_arr):
    lat = np.radians(lat_arr)
    lon = np.radians(lon_arr)
    x = np.cos(lat) * np.cos(lon)
    y = np.cos(lat) * np.sin(lon)
    z = np.sin(lat)
    return np.column_stack((x, y, z))

def chord_to_great_circle_km(chord_dist):
    half = np.clip(chord_dist / 2.0, 0.0, 1.0)
    angles = 2.0 * np.arcsin(half)
    return EARTH_RADIUS_KM * angles

def distance_km_between_points(a, b):
    chord = np.linalg.norm(
        latlon_to_unit_xyz(np.array([a[0]]), np.array([a[1]]))[0]
        - latlon_to_unit_xyz(np.array([b[0]]), np.array([b[1]]))[0]
    )
    return float(chord_to_great_circle_km(chord))

def generate_candidate_points(lat_min, lat_max, lon_min, lon_max, resolution, polygon):
    lat_vals = np.linspace(lat_min, lat_max, resolution)
    lon_vals = np.linspace(lon_min, lon_max, resolution)
    lat_grid, lon_grid = np.meshgrid(lat_vals, lon_vals, indexing="ij")
    lat_flat = lat_grid.ravel()
    lon_flat = lon_grid.ravel()

    pts_gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon_flat, lat_flat), crs="EPSG:4326")
    mask = pts_gdf.intersects(polygon)
    if mask.sum() == 0:
        return np.empty((0, 2), dtype=float)
    valid_lat = lat_flat[mask.values]
    valid_lon = lon_flat[mask.values]
    pts = np.column_stack([valid_lat, valid_lon])
    return np.unique(pts, axis=0)
