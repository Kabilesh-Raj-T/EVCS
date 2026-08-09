"""Coordinate math, name normalization, and spatial geometry helpers."""

import re
import numpy as np
import geopandas as gpd
try:
    from config import EARTH_RADIUS_KM, INDIA_DEFAULT_BOUNDS, STATE_DISPLAY_OVERRIDES
except ImportError:
    from backend.config import EARTH_RADIUS_KM, INDIA_DEFAULT_BOUNDS, STATE_DISPLAY_OVERRIDES

def normalize_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower()) if s else ""

def display_region_name(s: str) -> str:
    if not s or str(s).lower() == "nan": return ""
    text = " ".join(str(s).strip().split())
    key = normalize_name(text)
    return STATE_DISPLAY_OVERRIDES.get(key, text.title() if text.isupper() else text)

def merge_geometries(gdf: gpd.GeoDataFrame):
    return gdf.geometry.union_all() if hasattr(gdf.geometry, "union_all") else gdf.geometry.unary_union

def latlon_to_unit_xyz(lat_arr, lon_arr) -> np.ndarray:
    lat, lon = np.radians(lat_arr), np.radians(lon_arr)
    return np.column_stack((np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)))

def chord_to_great_circle_km(chord_dist) -> np.ndarray:
    return EARTH_RADIUS_KM * (2.0 * np.arcsin(np.clip(np.asarray(chord_dist) / 2.0, 0.0, 1.0)))

def distance_km_between_points(a: tuple[float, float], b: tuple[float, float]) -> float:
    chord = np.linalg.norm(
        latlon_to_unit_xyz(np.array([a[0]]), np.array([a[1]]))[0]
        - latlon_to_unit_xyz(np.array([b[0]]), np.array([b[1]]))[0]
    )
    return float(chord_to_great_circle_km(chord))

def generate_candidate_points(
    lat_min: float, lat_max: float, lon_min: float, lon_max: float,
    resolution: int, polygon
) -> np.ndarray:
    lats = np.linspace(lat_min, lat_max, resolution)
    lons = np.linspace(lon_min, lon_max, resolution)
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    lat_flat, lon_flat = lat_grid.ravel(), lon_grid.ravel()
    pts_gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon_flat, lat_flat), crs="EPSG:4326")
    mask = pts_gdf.intersects(polygon)
    if not mask.any():
        return np.empty((0, 2), dtype=float)
    return np.unique(np.column_stack([lat_flat[mask.values], lon_flat[mask.values]]), axis=0)
