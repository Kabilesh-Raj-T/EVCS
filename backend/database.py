"""Load and cache all application data at startup."""

import logging
import os
import threading

import geopandas as gpd
import numpy as np
import pandas as pd

import sys
import pickle
import subprocess
from config import CSV_PATH, DEMAND_FEATURES_PATH, INDIA_DEFAULT_BOUNDS, PREPROCESSED_GEOMETRIES_PATH
from utils import normalize_name

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
            
        # Load stations data
        df = pd.read_csv(CSV_PATH, usecols=["latitude_num", "longitude_num", "state", "district"], low_memory=False)
        df = df.dropna(subset=["latitude_num", "longitude_num"]).reset_index(drop=True)
        df["_state_key"] = df["state"].map(normalize_name)
        stations = df
        existing_coords = df[["latitude_num", "longitude_num"]].to_numpy(dtype=float)
        
        # Ensure geometries are preprocessed
        if not os.path.exists(PREPROCESSED_GEOMETRIES_PATH):
            logger.warning("Geometry cache missing. Running preprocessing script...")
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preprocessing", "preprocess_geometries.py")
            subprocess.run([sys.executable, script_path], check=True)
            
        with open(PREPROCESSED_GEOMETRIES_PATH, "rb") as f:
            cache = pickle.load(f)
        india_boundary = cache["india_boundary"]
        polygon = cache["polygon"]
        state_regions = cache["state_regions"]
        REGION_OPTIONS = cache["REGION_OPTIONS"]
        logger.info("Loaded geometries from cache.")
            
        data_loaded = True
        logger.info("Loaded %d stations, %d districts", len(existing_coords), sum(len(s["districts"]) for s in state_regions.values()))


def load_demand_features():
    global demand_features
    if demand_features is not None:
        return demand_features
    demand_features = pd.read_parquet(DEMAND_FEATURES_PATH)
    return demand_features
