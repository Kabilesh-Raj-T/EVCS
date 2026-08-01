import os
import logging
import numpy as np
import pandas as pd
import geopandas as gpd
import threading
from typing import Optional

from config import (
    GEOJSON_PATH,
    CSV_PATH,
    ADM2_GEOJSON_PATH,
    DEMAND_FEATURES_PATH,
    INDIA_DEFAULT_BOUNDS,
)
from utils import (
    detect_lat_lon_columns,
    to_float_series,
    merge_geometries,
    filter_to_india,
)
from spatial import (
    build_state_regions,
    load_adm2_boundary,
    attach_district_boundaries,
    attach_station_regions,
    serialize_regions,
)

logger = logging.getLogger("evcsapi")

# ----------------------------
# Lazy-loaded data state
# ----------------------------
data_loaded = False
data_lock = threading.Lock()
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

    with data_lock:
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
