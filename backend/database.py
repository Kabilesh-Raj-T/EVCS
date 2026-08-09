"""Load and cache all application data at startup."""

import logging
import os
import threading

import geopandas as gpd
import numpy as np
import pandas as pd

from config import CSV_PATH, DEMAND_FEATURES_PATH, GEOJSON_PATH, INDIA_DEFAULT_BOUNDS
from spatial import attach_district_boundaries, build_state_regions, load_adm2_boundary, serialize_regions
from utils import merge_geometries, normalize_name

logger = logging.getLogger("evcsapi")

data_loaded = False
_lock = threading.Lock()
existing_coords = np.empty((0, 2))
stations = pd.DataFrame()
polygon = None
india_boundary = gpd.GeoDataFrame()
state_regions = {}
REGION_OPTIONS = {"default_bounds": INDIA_DEFAULT_BOUNDS, "states": []}
demand_features = None


def load_data():
    global data_loaded, existing_coords, stations, polygon, india_boundary, state_regions, REGION_OPTIONS
    with _lock:
        if data_loaded:
            return
        india_boundary = gpd.read_file(GEOJSON_PATH).to_crs(epsg=4326)
        polygon = merge_geometries(india_boundary)
        df = pd.read_csv(CSV_PATH, usecols=["latitude_num", "longitude_num", "state", "district"], low_memory=False)
        df = df.dropna(subset=["latitude_num", "longitude_num"]).reset_index(drop=True)
        df["_state_key"] = df["state"].map(normalize_name)
        stations = df
        existing_coords = df[["latitude_num", "longitude_num"]].to_numpy(dtype=float)
        state_regions = build_state_regions(india_boundary)
        attach_district_boundaries(state_regions, load_adm2_boundary(), india_boundary)
        REGION_OPTIONS = serialize_regions(state_regions)
        data_loaded = True
        logger.info("Loaded %d stations, %d districts", len(existing_coords), sum(len(s["districts"]) for s in state_regions.values()))


def load_demand_features():
    global demand_features
    if demand_features is not None:
        return demand_features
    demand_features = pd.read_parquet(DEMAND_FEATURES_PATH)
    return demand_features
