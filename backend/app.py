import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import numpy as np
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap
from shapely.geometry import Point
from scipy.spatial import KDTree
import tempfile
import os
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

# ----------------------------
# Helpers
# ----------------------------
def normalize_name(s: str) -> str:
    return str(s).replace(" ", "").lower()

def detect_lat_lon_columns(df: pd.DataFrame):
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
    return (
        s.astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace({"": np.nan})
        .astype(float)
    )

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

# ----------------------------
# Lazy-loaded data
# ----------------------------
data_loaded = False
existing_coords = np.empty((0, 2))
polygon = None
tn_boundary = None
BASE_MAP_PATH: Optional[str] = None

def load_data():
    global data_loaded, existing_coords, polygon, tn_boundary, BASE_MAP_PATH

    if data_loaded:
        return

    logger.info("Loading CSV and GeoJSON...")
    # CSV load
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found at {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    lat_col, lon_col = detect_lat_lon_columns(df)
    df[lat_col] = to_float_series(df[lat_col])
    df[lon_col] = to_float_series(df[lon_col])
    df = df.dropna(subset=[lat_col, lon_col]).copy()

    if "state" in df.columns:
        df["state_norm"] = df["state"].astype(str).str.lower()
        tn_df = df[df["state_norm"].str.contains("tamil", na=False)].copy()
        if tn_df.empty:
            tn_df = df.copy()
    else:
        tn_df = df.copy()
    existing_coords = tn_df[[lat_col, lon_col]].to_numpy(dtype=float)

    # GeoJSON load
    if not os.path.exists(GEOJSON_PATH):
        raise FileNotFoundError(f"GeoJSON not found at {GEOJSON_PATH}")
    india = gpd.read_file(GEOJSON_PATH)
    name_col = None
    for c in ["NAME_1", "NAME_2", "NAME", "ST_NM"]:
        if c in india.columns:
            name_col = c
            break
    if name_col is None:
        raise ValueError("Could not detect state name column in GeoJSON")

    india["_n"] = india[name_col].astype(str).map(normalize_name)
    tn_boundary = india[india["_n"].str.contains("tamilnadu", na=False)].to_crs(epsg=4326)
    if tn_boundary.empty:
        raise ValueError("Tamil Nadu polygon not found in GeoJSON")

    polygon = tn_boundary.geometry.iloc[0]

    # Generate base heatmap once
    centroid = polygon.centroid
    base_map = folium.Map(location=[centroid.y, centroid.x], zoom_start=7)
    folium.GeoJson(tn_boundary, name="Tamil Nadu").add_to(base_map)

    if len(existing_coords) > 0:
        HeatMap(existing_coords.tolist(), radius=8, blur=12).add_to(base_map)

    BASE_MAP_PATH = os.path.join(tempfile.gettempdir(), "existing_heatmap.html")
    base_map.save(BASE_MAP_PATH)
    logger.info("Base heatmap saved at %s", BASE_MAP_PATH)

    data_loaded = True

# ----------------------------
# Routes
# ----------------------------
@app.route("/", methods=["GET"])
def base():
    try:
        load_data()
        if BASE_MAP_PATH and os.path.exists(BASE_MAP_PATH):
            return send_file(BASE_MAP_PATH, mimetype="text/html")
        return "<html><body><h3>Heatmap not available</h3></body></html>", 503
    except Exception as e:
        logger.exception("Error serving base heatmap")
        return jsonify({"error": str(e)}), 500

@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        load_data()
        data = request.get_json(force=True)
        k = int(data.get("k", 5))
        resolution = int(data.get("resolution", 100))
        lat_min = float(data.get("lat_min", 8.0))
        lat_max = float(data.get("lat_max", 13.5))
        lon_min = float(data.get("lon_min", 76.0))
        lon_max = float(data.get("lon_max", 80.5))

        # Sanity checks
        if resolution <= 0 or resolution > 1000:
            return jsonify({"error": "resolution out of range"}), 400
        if k < 0 or k > 1000:
            return jsonify({"error": "k out of range"}), 400

        candidates = generate_candidate_points(lat_min, lat_max, lon_min, lon_max, resolution, polygon)
        if candidates.size == 0:
            return jsonify({"error": "No candidate points found"}), 400

        optimal = k_center_greedy(existing_coords, candidates, k)

        # Make Folium map
        m = folium.Map(location=[polygon.centroid.y, polygon.centroid.x], zoom_start=7)
        folium.GeoJson(tn_boundary, name="Tamil Nadu").add_to(m)

        if len(existing_coords) > 0:
            HeatMap(existing_coords.tolist(), radius=8, blur=12).add_to(m)

        for i, (lat, lon) in enumerate(optimal, start=1):
            folium.Marker(
                location=[lat, lon],
                popup=f"Suggested #{i}: ({lat:.6f}, {lon:.6f})",
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
        points_data = [{"id": i, "lat": lat, "lon": lon} for i, (lat, lon) in enumerate(optimal, start=1)]

        logger.info("Generated optimization map: %s", tmpfile.name)
        
        # Return JSON with map HTML and points
        return jsonify({
            "map_html": map_content,
            "points": points_data
        })

    except Exception as e:
        logger.exception("Error in /optimize")
        return jsonify({"error": str(e)}), 500

# Note: Do not call app.run() here for production. Gunicorn will serve the app.
# For local dev you can run: python -m flask run or use a small helper:
if __name__ == "__main__":
    # Local development only
    app.run(host="0.0.0.0", port=8000)
