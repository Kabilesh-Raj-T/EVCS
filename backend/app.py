import logging
import tempfile
import numpy as np
import pandas as pd
import geopandas as gpd
import h3

from shapely.geometry import shape
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from scipy.spatial import KDTree

import folium
from folium.plugins import HeatMap

# ============================================================
# CONFIG
# ============================================================

CSV_PATH = "charging_stations.csv"
GEOJSON_PATH = "gadm41_IND_1.json"

LAT_COL = "latitude"
LON_COL = "longitude"

H3_RESOLUTION = 7          # ~5 km hexes
MAX_K = 500
EARTH_RADIUS_KM = 6371.0

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evcs-api")

# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)
CORS(app)

# ============================================================
# MATH
# ============================================================

def latlon_to_unit_xyz(lat, lon):
    lat = np.radians(lat)
    lon = np.radians(lon)
    return np.column_stack([
        np.cos(lat) * np.cos(lon),
        np.cos(lat) * np.sin(lon),
        np.sin(lat)
    ])


def chord_to_great_circle_km(chord):
    half = np.clip(chord / 2.0, 0, 1)
    return EARTH_RADIUS_KM * (2 * np.arcsin(half))


def k_center_greedy(existing, candidates, k):
    if k <= 0 or len(candidates) == 0:
        return []

    cand_xyz = latlon_to_unit_xyz(candidates[:, 0], candidates[:, 1])

    if len(existing) == 0:
        min_dist = np.full(len(candidates), np.inf)
    else:
        tree = KDTree(latlon_to_unit_xyz(existing[:, 0], existing[:, 1]))
        chord, _ = tree.query(cand_xyz, k=1)
        min_dist = chord_to_great_circle_km(chord)

    selected = []

    for _ in range(k):
        idx = int(np.argmax(min_dist))
        if min_dist[idx] < 0:
            break

        selected.append(tuple(candidates[idx]))

        chord = np.linalg.norm(cand_xyz - cand_xyz[idx], axis=1)
        min_dist = np.minimum(min_dist, chord_to_great_circle_km(chord))
        min_dist[idx] = -1

    return selected

# ============================================================
# STARTUP: LOAD DATA ONCE
# ============================================================

logger.info("Initializing base data")

# ---- Load Indian states
states = gpd.read_file(GEOJSON_PATH).to_crs(epsg=4326)

STATE_GEOMS = {
    row["NAME_1"]: row.geometry
    for _, row in states.iterrows()
}

# ---- Load charging stations
df = pd.read_csv(CSV_PATH)

stations_gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df[LON_COL], df[LAT_COL]),
    crs="EPSG:4326"
)

# ============================================================
# REGION CACHE
# ============================================================

REGION_CACHE = {}

def load_region(region_name):
    if region_name in REGION_CACHE:
        return REGION_CACHE[region_name]

    if region_name not in STATE_GEOMS:
        raise ValueError("Invalid region")

    polygon = STATE_GEOMS[region_name].unary_union

    # ---- Stations inside region (spatial truth)
    stations = stations_gdf[
        stations_gdf.within(polygon)
    ][[LAT_COL, LON_COL]].to_numpy()

    # ---- H3 candidate generation
    geojson = shape(polygon).__geo_interface__

    hexes = h3.polyfill_geojson(
        geojson,
        res=H3_RESOLUTION,
        geo_json_conformant=True
    )

    candidates = np.array([
        h3.h3_to_geo(h)  # (lat, lon)
        for h in hexes
    ])

    REGION_CACHE[region_name] = {
        "polygon": polygon,
        "stations": stations,
        "candidates": candidates
    }

    logger.info(
        "Region loaded: %s | stations=%d | candidates=%d",
        region_name, len(stations), len(candidates)
    )

    return REGION_CACHE[region_name]

# ============================================================
# ROUTES
# ============================================================

@app.route("/regions", methods=["GET"])
def regions():
    return jsonify(sorted(STATE_GEOMS.keys()))


@app.route("/optimize", methods=["POST"])
def optimize():
    data = request.get_json(force=True)

    region = data.get("region", "Tamil Nadu")
    k = int(data.get("k", 5))

    if k < 1 or k > MAX_K:
        return jsonify({"error": "k out of range"}), 400

    region_data = load_region(region)

    optimal = k_center_greedy(
        region_data["stations"],
        region_data["candidates"],
        k
    )

    poly = region_data["polygon"]
    centroid = poly.centroid

    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=7)
    folium.GeoJson(poly).add_to(m)

    if len(region_data["stations"]) > 0:
        HeatMap(region_data["stations"].tolist()).add_to(m)

    for i, (lat, lon) in enumerate(optimal, 1):
        folium.Marker(
            location=[lat, lon],
            tooltip=f"Suggested #{i}",
            icon=folium.Icon(color="red", icon="bolt", prefix="fa"),
        ).add_to(m)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    m.save(tmp.name)
    tmp.close()

    return send_file(tmp.name, mimetype="text/html")

# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
