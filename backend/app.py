import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap
from scipy.spatial import KDTree
import tempfile
import os
import re
from typing import Optional

# ----------------------------
# App + logging
# ----------------------------
app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evcsapi")

# ----------------------------
# Config
# ----------------------------
EARTH_RADIUS_KM = 6371.0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "charging_stations.csv")
GEOJSON_PATH = os.path.join(BASE_DIR, "gadm41_IND_1.json")
ADM2_GEOJSON_PATH = os.path.join(BASE_DIR, "data", "raw", "geoboundaries_adm2.geojson")
DEMAND_FEATURES_PATH = os.path.join(BASE_DIR, "data", "processed", "demand_features.parquet")
INDIA_CENTER = [22.9734, 78.6569]
INDIA_DEFAULT_BOUNDS = {
    "lat_min": 6.7,
    "lat_max": 35.6,
    "lon_min": 68.1,
    "lon_max": 97.5,
}

STATE_DISPLAY_OVERRIDES = {
    "andamanandnicobar": "Andaman & Nicobar",
    "andamannicobar": "Andaman & Nicobar",
    "andhrapradesh": "Andhra Pradesh",
    "arunachalpradesh": "Arunachal Pradesh",
    "dadraandnagarhaveli": "Dadra and Nagar Haveli",
    "damananddiu": "Daman and Diu",
    "delhi": "Delhi",
    "nctofdelhi": "Delhi",
    "himachalpradesh": "Himachal Pradesh",
    "jammuandkashmir": "Jammu and Kashmir",
    "jammukashmir": "Jammu and Kashmir",
    "madhyapradesh": "Madhya Pradesh",
    "tamilnadu": "Tamil Nadu",
    "uttarpradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "uttrakhand": "Uttarakhand",
    "utofdnhanddd": "Dadra and Nagar Haveli and Daman and Diu",
    "westbengal": "West Bengal",
}

# ----------------------------
# Helpers
# ----------------------------
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

def k_center_greedy(existing_coords, candidate_points, k):
    if candidate_points.size == 0 or k <= 0:
        return []

    cand = candidate_points.copy()
    cand_xyz = latlon_to_unit_xyz(cand[:, 0], cand[:, 1])

    if existing_coords.size == 0:
        min_dists = np.full(len(cand), np.inf)
    else:
        existing_xyz = latlon_to_unit_xyz(existing_coords[:, 0], existing_coords[:, 1])
        tree = KDTree(existing_xyz)
        # KDTree expects xyz inputs — we already converted candidate to xyz
        chord_dist, _ = tree.query(cand_xyz, k=1)
        min_dists = chord_to_great_circle_km(chord_dist)

    selected = []
    for _ in range(k):
        best_idx = int(np.argmax(min_dists))
        if min_dists[best_idx] == -1:
            break
        best_point = tuple(cand[best_idx])
        selected.append(best_point)

        new_xyz = cand_xyz[best_idx : best_idx + 1]
        chord = np.linalg.norm(cand_xyz - new_xyz, axis=1)
        dists_km = chord_to_great_circle_km(chord)
        min_dists = np.minimum(min_dists, dists_km)
        min_dists[best_idx] = -1
    return selected

def load_demand_features():
    global demand_features
    if demand_features is not None:
        return demand_features

    if not os.path.exists(DEMAND_FEATURES_PATH):
        logger.warning("Demand feature dataset not found at %s", DEMAND_FEATURES_PATH)
        demand_features = pd.DataFrame()
        return demand_features

    df = pd.read_parquet(DEMAND_FEATURES_PATH)
    required = {"latitude", "longitude", "demand_score"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Demand feature dataset is missing columns: {sorted(missing)}")
    demand_features = df.copy()
    logger.info("Loaded %d demand feature rows", len(demand_features))
    return demand_features

def normalize_array(values):
    arr = np.asarray(values, dtype=float)
    finite = np.isfinite(arr)
    if not finite.any():
        return np.zeros(len(arr), dtype=float)
    out = np.zeros(len(arr), dtype=float)
    min_value = np.nanmin(arr[finite])
    max_value = np.nanmax(arr[finite])
    if np.isclose(min_value, max_value):
        return out
    out[finite] = (arr[finite] - min_value) / (max_value - min_value)
    return np.clip(out, 0.0, 1.0)

def distance_km_between_points(a, b):
    chord = np.linalg.norm(
        latlon_to_unit_xyz(np.array([a[0]]), np.array([a[1]]))[0]
        - latlon_to_unit_xyz(np.array([b[0]]), np.array([b[1]]))[0]
    )
    return float(chord_to_great_circle_km(chord))

def adaptive_min_separation_km(region, k, default_km=12.0):
    bounds = region["bounds"]
    diagonal = distance_km_between_points(
        (bounds["lat_min"], bounds["lon_min"]),
        (bounds["lat_max"], bounds["lon_max"]),
    )
    if k <= 1:
        return min(default_km, diagonal)
    return max(1.0, min(default_km, diagonal / (np.sqrt(k) * 2.0)))

def demand_candidates_for_region(features, region, resolution):
    points_gdf = gpd.GeoDataFrame(
        features,
        geometry=gpd.points_from_xy(features["longitude"], features["latitude"]),
        crs="EPSG:4326",
    )
    mask = points_gdf.intersects(region["geometry"])
    candidates_df = features.loc[mask.to_numpy()].copy()

    if len(candidates_df) >= 20:
        return candidates_df

    generated = generate_candidate_points(
        region["bounds"]["lat_min"],
        region["bounds"]["lat_max"],
        region["bounds"]["lon_min"],
        region["bounds"]["lon_max"],
        resolution,
        region["geometry"],
    )
    if generated.size == 0:
        return candidates_df

    generated_df = pd.DataFrame(generated, columns=["latitude", "longitude"])
    if features.empty:
        generated_df["demand_score"] = 0.0
        return generated_df

    feature_coords = features[["latitude", "longitude"]].to_numpy(dtype=float)
    tree = KDTree(latlon_to_unit_xyz(feature_coords[:, 0], feature_coords[:, 1]))
    _, nearest_idx = tree.query(latlon_to_unit_xyz(generated[:, 0], generated[:, 1]), k=1)
    nearest_features = features.iloc[nearest_idx].reset_index(drop=True)

    generated_df["demand_score"] = pd.to_numeric(
        nearest_features.get("demand_score", 0.0),
        errors="coerce",
    ).fillna(0.0)
    for col in ["state", "district"]:
        if col in nearest_features.columns:
            generated_df[col] = nearest_features[col].to_numpy()
    return generated_df

def weighted_demand_optimizer(region, k, resolution, min_separation_km=None):
    if k <= 0:
        return []

    features = load_demand_features()
    if features.empty:
        logger.warning("Demand features unavailable; falling back to greedy optimizer")
        candidates = generate_candidate_points(
            region["bounds"]["lat_min"],
            region["bounds"]["lat_max"],
            region["bounds"]["lon_min"],
            region["bounds"]["lon_max"],
            100,
            region["geometry"],
        )
        return [
            {"lat": lat, "lon": lon, "demand_score": None, "selection_score": None}
            for lat, lon in k_center_greedy(region["coords"], candidates, k)
        ]

    candidates_df = demand_candidates_for_region(features, region, resolution)
    if candidates_df.empty:
        return []

    coords = candidates_df[["latitude", "longitude"]].to_numpy(dtype=float)
    demand = pd.to_numeric(candidates_df["demand_score"], errors="coerce").fillna(0.0).to_numpy(dtype=float)

    coverage_score = np.zeros(len(candidates_df), dtype=float)
    if region["coords"].size > 0:
        tree = KDTree(latlon_to_unit_xyz(region["coords"][:, 0], region["coords"][:, 1]))
        chord_dist, _ = tree.query(latlon_to_unit_xyz(coords[:, 0], coords[:, 1]), k=1)
        coverage_score = normalize_array(chord_to_great_circle_km(chord_dist))

    if np.nanmax(demand) > 0:
        selection_score = (0.85 * normalize_array(demand)) + (0.15 * coverage_score)
    else:
        selection_score = coverage_score

    order = np.argsort(-selection_score)
    selected = []
    selected_coords = []
    min_separation_km = min_separation_km or adaptive_min_separation_km(region, k)
    for idx in order:
        point = coords[idx]
        if selected_coords:
            existing_selected = np.asarray(selected_coords, dtype=float)
            chord = np.linalg.norm(
                latlon_to_unit_xyz(existing_selected[:, 0], existing_selected[:, 1])
                - latlon_to_unit_xyz(np.array([point[0]]), np.array([point[1]]))[0],
                axis=1,
            )
            if np.nanmin(chord_to_great_circle_km(chord)) < min_separation_km:
                continue

        row = candidates_df.iloc[idx]
        selected.append(
            {
                "lat": float(point[0]),
                "lon": float(point[1]),
                "demand_score": float(demand[idx]),
                "selection_score": float(selection_score[idx]),
                "state": row.get("state", ""),
                "district": row.get("district", ""),
            }
        )
        selected_coords.append(point)
        if len(selected) >= k:
            break

    if len(selected) < k:
        used = {(round(item["lat"], 10), round(item["lon"], 10)) for item in selected}
        for idx in order:
            point = coords[idx]
            key = (round(float(point[0]), 10), round(float(point[1]), 10))
            if key in used:
                continue
            row = candidates_df.iloc[idx]
            selected.append(
                {
                    "lat": float(point[0]),
                    "lon": float(point[1]),
                    "demand_score": float(demand[idx]),
                    "selection_score": float(selection_score[idx]),
                    "state": row.get("state", ""),
                    "district": row.get("district", ""),
                }
            )
            used.add(key)
            if len(selected) >= k:
                break

    return selected

def add_station_heatmap(map_obj, coords):
    if len(coords) == 0:
        return

    HeatMap(
        coords.tolist(),
        name="Existing EV charging station density",
        radius=9,
        blur=12,
        min_opacity=0.25,
        max_zoom=8,
    ).add_to(map_obj)

def build_state_regions(india_gdf: gpd.GeoDataFrame):
    regions = {}
    for raw_name, group in india_gdf.groupby("NAME_1"):
        display_name = display_region_name(raw_name)
        key = normalize_name(display_name)
        if not key:
            continue

        geometry = merge_geometries(group)
        if key in regions:
            geometry = merge_geometries(
                gpd.GeoSeries([regions[key]["geometry"], geometry], crs="EPSG:4326").to_frame("geometry")
            )

        regions[key] = {
            "name": display_name,
            "bounds": bounds_to_dict(geometry.bounds),
            "geometry": geometry,
            "districts": {},
        }
    return regions

def load_adm2_boundary():
    if not os.path.exists(ADM2_GEOJSON_PATH):
        logger.warning("ADM2 district GeoJSON not found at %s", ADM2_GEOJSON_PATH)
        return None
    try:
        adm2 = gpd.read_file(ADM2_GEOJSON_PATH).to_crs(epsg=4326)
        if adm2.empty:
            logger.warning("ADM2 district GeoJSON is empty")
            return None
        logger.info("Loaded %d ADM2 district polygons", len(adm2))
        return adm2
    except Exception:
        logger.exception("Failed to load ADM2 district GeoJSON")
        return None

def attach_district_boundaries(state_regions, district_gdf, india_gdf):
    if district_gdf is None or district_gdf.empty:
        return False

    district_col = first_existing_column(
        district_gdf,
        ["shapeName", "NAME_2", "district", "District", "DISTRICT", "dtname", "name"],
    )
    if not district_col:
        logger.warning("Could not detect district name column in ADM2 boundary")
        return False

    state_col = first_existing_column(india_gdf, ["NAME_1", "shapeName", "state", "State", "name"])
    if not state_col:
        logger.warning("Could not detect state name column in ADM1 boundary")
        return False

    centroids = district_gdf[[district_col, "geometry"]].copy()
    centroids["geometry"] = centroids.geometry.representative_point()
    joined = gpd.sjoin(
        centroids,
        india_gdf[[state_col, "geometry"]],
        how="left",
        predicate="within",
    )

    attached = 0
    for idx, row in joined.iterrows():
        state_name = display_region_name(row.get(state_col, ""))
        district_name = display_region_name(row.get(district_col, ""))
        state_key = normalize_name(state_name)
        district_key = normalize_name(district_name)
        if not state_key or not district_key or state_key not in state_regions:
            continue

        geometry = district_gdf.loc[idx, "geometry"]
        district_entry = state_regions[state_key]["districts"].get(district_key)
        if district_entry:
            geometry = geometry_from_series(gpd.GeoSeries([district_entry["geometry"], geometry], crs="EPSG:4326"))

        state_regions[state_key]["districts"][district_key] = {
            "name": district_name,
            "bounds": bounds_to_dict(geometry.bounds),
            "geometry": geometry,
            "data": pd.DataFrame(),
            "source": "adm2",
        }
        attached += 1

    logger.info("Attached %d ADM2 district polygons to states", attached)
    return attached > 0

def attach_station_regions(state_regions, stations_df, lat_col, lon_col, use_station_district_fallback=True):
    if "state" not in stations_df.columns:
        return

    stations_df["_state_name"] = stations_df["state"].map(display_region_name)
    stations_df["_state_key"] = stations_df["_state_name"].map(normalize_name)
    if "district" in stations_df.columns:
        stations_df["_district_name"] = stations_df["district"].map(display_region_name)
        stations_df["_district_key"] = stations_df["_district_name"].map(normalize_name)

    for state_key, state_df in stations_df.groupby("_state_key"):
        if not state_key:
            continue

        state_name = state_df["_state_name"].dropna().iloc[0]
        if state_key not in state_regions:
            state_regions[state_key] = {
                "name": state_name,
                "bounds": coordinate_bounds(state_df, lat_col, lon_col, padding=0.25),
                "geometry": None,
                "districts": {},
            }

        if "district" not in state_df.columns:
            continue

        for district_key, district_df in state_df.dropna(subset=["_district_key"]).groupby("_district_key"):
            if not district_key:
                continue

            existing = state_regions[state_key]["districts"].get(district_key)
            if existing is not None:
                existing_data = existing.get("data")
                if existing_data is None or existing_data.empty:
                    existing["data"] = district_df.copy()
                else:
                    existing["data"] = pd.concat([existing_data, district_df], ignore_index=True)
                continue

            if not use_station_district_fallback:
                continue

            district_name = district_df["_district_name"].dropna().iloc[0]
            state_regions[state_key]["districts"][district_key] = {
                "name": district_name,
                "bounds": coordinate_bounds(district_df, lat_col, lon_col, padding=0.1),
                "geometry": None,
                "data": district_df.copy(),
                "source": "station_bbox",
            }

def serialize_regions(state_regions):
    states = []
    for state in sorted(state_regions.values(), key=lambda item: item["name"]):
        districts = [
            {
                "name": district["name"],
                "bounds": district["bounds"],
            }
            for district in sorted(state["districts"].values(), key=lambda item: item["name"])
        ]
        states.append({
            "name": state["name"],
            "bounds": state["bounds"],
            "districts": districts,
        })

    return {
        "default_bounds": INDIA_DEFAULT_BOUNDS,
        "states": states,
    }

def make_bbox_polygon(bounds):
    from shapely.geometry import box

    return box(bounds["lon_min"], bounds["lat_min"], bounds["lon_max"], bounds["lat_max"])

def station_coords_within_geometry(geometry):
    if stations is None or geometry is None or geometry.is_empty:
        return np.empty((0, 2))
    station_points = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations[station_lon_col], stations[station_lat_col]),
        crs="EPSG:4326",
    )
    mask = station_points.intersects(geometry)
    return stations.loc[mask.to_numpy(), [station_lat_col, station_lon_col]].to_numpy(dtype=float)

# ----------------------------
# Lazy-loaded data
# ----------------------------
data_loaded = False
existing_coords = np.empty((0, 2))
stations = None
station_lat_col = None
station_lon_col = None
polygon = None
india_boundary = None
district_boundary = None
state_regions = {}
REGION_OPTIONS = {"default_bounds": INDIA_DEFAULT_BOUNDS, "states": []}
BASE_MAP_PATH: Optional[str] = None
demand_features = None

def load_data():
    global data_loaded, existing_coords, stations, station_lat_col, station_lon_col
    global polygon, india_boundary, district_boundary, state_regions, REGION_OPTIONS, BASE_MAP_PATH

    if data_loaded:
        return

    # GeoJSON load
    logger.info("Loading CSV and GeoJSON...")
    if not os.path.exists(GEOJSON_PATH):
        raise FileNotFoundError(f"GeoJSON not found at {GEOJSON_PATH}")
    india_boundary = gpd.read_file(GEOJSON_PATH).to_crs(epsg=4326)
    if india_boundary.empty:
        raise ValueError("India boundary GeoJSON is empty")

    polygon = merge_geometries(india_boundary)

    # CSV load
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found at {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    lat_col, lon_col = detect_lat_lon_columns(df)
    df[lat_col] = to_float_series(df[lat_col])
    df[lon_col] = to_float_series(df[lon_col])
    df = df.dropna(subset=[lat_col, lon_col]).copy()

    india_df = filter_to_india(df, lat_col, lon_col, polygon)
    stations = india_df
    station_lat_col = lat_col
    station_lon_col = lon_col
    existing_coords = india_df[[lat_col, lon_col]].to_numpy(dtype=float)
    state_regions = build_state_regions(india_boundary)
    district_boundary = load_adm2_boundary()
    has_real_districts = attach_district_boundaries(state_regions, district_boundary, india_boundary)
    attach_station_regions(
        state_regions,
        stations,
        lat_col,
        lon_col,
        use_station_district_fallback=not has_real_districts,
    )
    REGION_OPTIONS = serialize_regions(state_regions)
    logger.info("Loaded %d India charging station rows", len(existing_coords))

    data_loaded = True

def region_center(bounds):
    return [
        (bounds["lat_min"] + bounds["lat_max"]) / 2.0,
        (bounds["lon_min"] + bounds["lon_max"]) / 2.0,
    ]

def region_zoom(region_type):
    if region_type == "district":
        return 10
    if region_type == "state":
        return 7
    return 5

def bounds_from_payload(data):
    return {
        "lat_min": float(data.get("lat_min", INDIA_DEFAULT_BOUNDS["lat_min"])),
        "lat_max": float(data.get("lat_max", INDIA_DEFAULT_BOUNDS["lat_max"])),
        "lon_min": float(data.get("lon_min", INDIA_DEFAULT_BOUNDS["lon_min"])),
        "lon_max": float(data.get("lon_max", INDIA_DEFAULT_BOUNDS["lon_max"])),
    }

def resolve_region(data):
    region_type = normalize_name(data.get("region_type", ""))
    has_district = bool(payload_text(data.get("district")))
    if region_type == "state" and has_district:
        region_type = "district"

    if not region_type:
        bounds = bounds_from_payload(data)
        bbox_polygon = make_bbox_polygon(bounds)
        return {
            "type": "custom",
            "name": "Custom bounds",
            "bounds": bounds,
            "geometry": polygon.intersection(bbox_polygon),
            "coords": existing_coords,
            "map_center": region_center(bounds),
            "zoom": 5,
        }

    if region_type in {"allindia", "india", "country"}:
        return {
            "type": "all_india",
            "name": "All India",
            "bounds": INDIA_DEFAULT_BOUNDS,
            "geometry": polygon,
            "coords": existing_coords,
            "map_center": INDIA_CENTER,
            "zoom": 5,
        }

    if region_type == "state":
        state_name = data.get("region_name") or data.get("state")
        state_key = normalize_name(state_name)
        state = state_regions.get(state_key)
        if not state:
            raise ValueError(f"Unknown state: {state_name}")

        geometry = state["geometry"] or polygon.intersection(make_bbox_polygon(state["bounds"]))
        state_mask = stations["_state_key"] == state_key
        coords = stations.loc[state_mask, [station_lat_col, station_lon_col]].to_numpy(dtype=float)
        if coords.size == 0:
            coords = station_coords_within_geometry(geometry)
        return {
            "type": "state",
            "name": state["name"],
            "bounds": state["bounds"],
            "geometry": geometry,
            "coords": coords,
            "map_center": region_center(state["bounds"]),
            "zoom": region_zoom("state"),
        }

    if region_type == "district":
        state_name = data.get("region_name") or data.get("state")
        district_name = data.get("district")
        state_key = normalize_name(state_name)
        district_key = normalize_name(district_name)
        state = state_regions.get(state_key)
        if not state:
            raise ValueError(f"Unknown state: {state_name}")
        district = state["districts"].get(district_key)
        if not district:
            raise ValueError(f"Unknown district for {state['name']}: {district_name}")

        geometry_source = state["geometry"] or polygon
        if district.get("geometry") is not None:
            geometry = district["geometry"]
        else:
            geometry = geometry_source.intersection(make_bbox_polygon(district["bounds"]))

        district_data = district.get("data")
        if district_data is not None and not district_data.empty:
            coords = district_data[[station_lat_col, station_lon_col]].to_numpy(dtype=float)
        else:
            coords = station_coords_within_geometry(geometry)
        return {
            "type": "district",
            "name": f"{district['name']}, {state['name']}",
            "bounds": district["bounds"],
            "geometry": geometry,
            "coords": coords,
            "map_center": region_center(district["bounds"]),
            "zoom": region_zoom("district"),
        }

    raise ValueError(f"Unsupported region_type: {data.get('region_type')}")

def add_region_boundary(map_obj, region):
    if region["type"] == "all_india":
        folium.GeoJson(india_boundary, name="India").add_to(map_obj)
    elif region.get("geometry") is not None and not region["geometry"].is_empty:
        folium.GeoJson(region["geometry"].__geo_interface__, name=region["name"]).add_to(map_obj)

# ----------------------------
# Routes
# ----------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "EVCS backend",
        "data_loaded": data_loaded,
    })

@app.route("/", methods=["GET"])
def base():
    return jsonify({
        "status": "ok",
        "service": "EVCS backend",
        "endpoints": ["/health", "/regions", "/optimize"],
        "data_loaded": data_loaded,
    })

@app.route("/regions", methods=["GET"])
def regions():
    try:
        load_data()
        return jsonify(REGION_OPTIONS)
    except Exception as e:
        logger.exception("Error serving regions")
        return jsonify({"error": str(e)}), 500

@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        load_data()
        data = request.get_json(force=True)
        k = int(data.get("k", 5))
        resolution = int(data.get("resolution", 100))
        optimizer = normalize_name(data.get("optimizer", "greedy"))
        supported_optimizers = {"greedy", "kcenter", "coverage", "weighted", "demand", "demandweighted"}
        if optimizer not in supported_optimizers:
            return jsonify({"error": f"Unsupported optimizer: {data.get('optimizer')}"}), 400
        region = resolve_region(data)
        lat_min = region["bounds"]["lat_min"]
        lat_max = region["bounds"]["lat_max"]
        lon_min = region["bounds"]["lon_min"]
        lon_max = region["bounds"]["lon_max"]

        # Sanity checks
        if resolution <= 0 or resolution > 500:
            return jsonify({"error": "resolution out of range"}), 400
        if k < 0 or k > 1000:
            return jsonify({"error": "k out of range"}), 400
        if lat_min >= lat_max or lon_min >= lon_max:
            return jsonify({"error": "invalid geographic bounds"}), 400

        optimal = []
        weighted_points = []
        if optimizer in {"weighted", "demand", "demandweighted"} and k > 0:
            weighted_points = weighted_demand_optimizer(region, k, resolution)
            optimal = [(point["lat"], point["lon"]) for point in weighted_points]
        elif k > 0:
            candidates = generate_candidate_points(
                lat_min,
                lat_max,
                lon_min,
                lon_max,
                resolution,
                region["geometry"],
            )
            if candidates.size == 0:
                return jsonify({"error": "No candidate points found"}), 400
            optimal = k_center_greedy(region["coords"], candidates, k)

        # Make Folium map
        m = folium.Map(location=region["map_center"], zoom_start=region["zoom"])
        add_region_boundary(m, region)
        m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])

        add_station_heatmap(m, region["coords"])

        weighted_by_coord = {
            (round(point["lat"], 10), round(point["lon"], 10)): point
            for point in weighted_points
        }
        for i, (lat, lon) in enumerate(optimal, start=1):
            weighted_meta = weighted_by_coord.get((round(lat, 10), round(lon, 10)), {})
            popup = f"Suggested #{i}: ({lat:.6f}, {lon:.6f})"
            if "demand_score" in weighted_meta and weighted_meta["demand_score"] is not None:
                popup += f"<br>Demand score: {weighted_meta['demand_score']:.3f}"
                popup += f"<br>Selection score: {weighted_meta['selection_score']:.3f}"
            folium.Marker(
                location=[lat, lon],
                popup=popup,
                tooltip=f"New EV #{i}",
                icon=folium.Icon(color="red", icon="bolt", prefix="fa"),
            ).add_to(m)

        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        m.save(tmpfile.name)
        tmpfile.close()
        
        # Read the file content
        with open(tmpfile.name, "r", encoding="utf-8") as f:
            map_content = f.read()

        # Prepare points list
        points_data = []
        for i, (lat, lon) in enumerate(optimal, start=1):
            point_payload = {"id": i, "lat": lat, "lon": lon}
            weighted_meta = weighted_by_coord.get((round(lat, 10), round(lon, 10)))
            if weighted_meta:
                point_payload.update({
                    "demand_score": weighted_meta.get("demand_score"),
                    "selection_score": weighted_meta.get("selection_score"),
                    "state": weighted_meta.get("state", ""),
                    "district": weighted_meta.get("district", ""),
                })
            points_data.append(point_payload)

        logger.info("Generated optimization map: %s", tmpfile.name)
        
        # Return JSON with map HTML and points
        return jsonify({
            "map_html": map_content,
            "points": points_data,
            "region": {
                "type": region["type"],
                "name": region["name"],
                "bounds": region["bounds"],
            },
            "optimizer": "weighted" if optimizer in {"weighted", "demand", "demandweighted"} else "greedy",
        })

    except Exception as e:
        logger.exception("Error in /optimize")
        return jsonify({"error": str(e)}), 500

# Note: Do not call app.run() here for production. Gunicorn will serve the app.
# For local dev you can run: python -m flask run or use a small helper:
if __name__ == "__main__":
    # Local development only
    app.run(host="0.0.0.0", port=8000)
