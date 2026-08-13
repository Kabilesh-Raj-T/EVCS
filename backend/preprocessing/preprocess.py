"""EVCS preprocessing pipeline: load raw data → build demand features → save parquet."""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import KDTree

from backend.utils import latlon_to_unit_xyz, chord_to_great_circle_km
from .config import (
    CACHE_DIR, COMMERCIAL_DENSITY_RADIUS_KM, CURRENT_ADM1_GEOJSON, CURRENT_BEE_CSV,
    DATA_QUALITY_REPORT_PATH, DATASET_SUMMARY_PATH, DEFAULT_GRID_RESOLUTION,
    DEMAND_FEATURES_PATH, FEATURE_STATISTICS_PATH, INDIA_BOUNDS, PROCESSED_DIR, RAW_DIR, REPORTS_DIR,
)

logger = logging.getLogger(__name__)
EARTH_RADIUS_KM = 6371.0

SCORE_COLUMNS = ["population_score", "commercial_density_score", "economic_score", "coverage_gap_score", "road_accessibility_score", "traffic_congestion_score", "ev_density_score"]
DISTANCE_COLUMNS = ["nearest_existing_station_distance", "nearest_highway_distance", "nearest_traffic_node_distance"]

STATE_EV_PENETRATION = {
    "maharashtra": 1.0, "karnataka": 0.95, "tamilnadu": 0.90, "delhi": 0.85,
    "uttarpradesh": 0.85, "gujarat": 0.80, "rajasthan": 0.65, "kerala": 0.60,
    "telangana": 0.55, "madhyapradesh": 0.50, "andhrapradesh": 0.45, "haryana": 0.40,
    "punjab": 0.35, "odisha": 0.30, "bihar": 0.25, "westbengal": 0.20,
    "chhattisgarh": 0.15, "jharkhand": 0.10, "assam": 0.05
}

STATE_GDP_PER_CAPITA = {
    "goa": 1.0, "sikkim": 0.95, "delhi": 0.90, "chandigarh": 0.85,
    "haryana": 0.80, "telangana": 0.75, "karnataka": 0.70, "gujarat": 0.65,
    "tamilnadu": 0.60, "kerala": 0.55, "maharashtra": 0.50, "uttarakhand": 0.45,
    "punjab": 0.40, "himachalpradesh": 0.35, "andhrapradesh": 0.30, "mizoram": 0.25,
    "arunachalpradesh": 0.20, "rajasthan": 0.15, "westbengal": 0.10, "odisha": 0.08,
    "chhattisgarh": 0.06, "madhyapradesh": 0.04, "assam": 0.03, "uttarpradesh": 0.02,
    "jharkhand": 0.01, "bihar": 0.0
}

_STATE_OVERRIDES = {
    "andamanandnicobar": "Andaman & Nicobar", "andhrapradesh": "Andhra Pradesh",
    "arunachalpradesh": "Arunachal Pradesh", "dadraandnagarhaveli": "Dadra and Nagar Haveli",
    "damananddiu": "Daman and Diu", "gujarat": "Gujarat", "himachalpradesh": "Himachal Pradesh",
    "jammuandkashmir": "Jammu and Kashmir", "madhyapradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra", "nctofdelhi": "Delhi", "tamilnadu": "Tamil Nadu",
    "uttarpradesh": "Uttar Pradesh", "uttarakhand": "Uttarakhand", "westbengal": "West Bengal",
}


def _normalize_name(v) -> str:
    return "" if pd.isna(v) else re.sub(r"[^a-z0-9]", "", " ".join(str(v).replace("&", "and").strip().split()).lower())


def _display_name(v) -> str:
    if pd.isna(v):
        return ""
    text = " ".join(re.sub(r"[^A-Za-z0-9&().,'/\- ]+", " ", re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(v))).strip().split())
    key = _normalize_name(text)
    return _STATE_OVERRIDES.get(key, text.title() if text.isupper() else text) if len(key) >= 2 else ""


def _standardize_coords(df: pd.DataFrame) -> pd.DataFrame:
    """Use the known dataset standards directly instead of fuzzy column searching."""
    if "latitude_num" in df.columns:
        df = df.drop(columns=["latitude", "longitude"], errors="ignore")
        df = df.rename(columns={"latitude_num": "latitude", "longitude_num": "longitude"})
    
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[df["latitude"].between(INDIA_BOUNDS["lat_min"], INDIA_BOUNDS["lat_max"]) & 
            df["longitude"].between(INDIA_BOUNDS["lon_min"], INDIA_BOUNDS["lon_max"])].copy()
    
    df["_dedup_lat"] = df["latitude"].round(6)
    df["_dedup_lon"] = df["longitude"].round(6)
    return df.drop_duplicates(subset=["_dedup_lat", "_dedup_lon"]).drop(columns=["_dedup_lat", "_dedup_lon"]).reset_index(drop=True)



def _nearest_km(ref_df: pd.DataFrame, query: pd.DataFrame) -> np.ndarray:
    if ref_df.empty:
        return np.full(len(query), np.nan)
    tree = KDTree(latlon_to_unit_xyz(ref_df["latitude"].to_numpy(), ref_df["longitude"].to_numpy()))
    d, _ = tree.query(latlon_to_unit_xyz(query["latitude"].to_numpy(), query["longitude"].to_numpy()), k=1)
    return chord_to_great_circle_km(d)


def _minmax(s: pd.Series, invert=False) -> pd.Series:
    v = -s if invert else s
    valid = v.dropna()
    if valid.empty or np.isclose(valid.min(), valid.max()):
        return pd.Series(0.0, index=s.index)
    return ((v - valid.min()) / (valid.max() - valid.min())).fillna(0.0).clip(0.0, 1.0)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False,
                  default=lambda v: v.item() if isinstance(v, (np.integer, np.floating)) else str(v))


def _load_or_download_highways(geom=None) -> pd.DataFrame:
    path = RAW_DIR / "osm_highways.csv"
    if path.exists():
        return _standardize_coords(pd.read_csv(path, low_memory=False))
        
    logger.info("Downloading major highways from Overpass API (this may take a minute)...")
    query_template = """
    [out:json][timeout:180];
    way["highway"~"motorway|trunk|primary"]({min_lat},{min_lon},{max_lat},{max_lon});
    out geom;
    """
    try:
        import requests
        import time
        headers = {"User-Agent": "EVCS-Optimizer/1.0"}
        road_points = set()
        
        # Split India bounding box into 4x4 grid to avoid 406 Not Acceptable limits
        lat_bins = np.linspace(INDIA_BOUNDS["lat_min"], INDIA_BOUNDS["lat_max"], 5)
        lon_bins = np.linspace(INDIA_BOUNDS["lon_min"], INDIA_BOUNDS["lon_max"], 5)
        
        for i in range(4):
            for j in range(4):
                min_l, max_l = lat_bins[i], lat_bins[i+1]
                min_ln, max_ln = lon_bins[j], lon_bins[j+1]
                q = query_template.format(min_lat=min_l, min_lon=min_ln, max_lat=max_l, max_lon=max_ln)
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        resp = requests.post("https://overpass-api.de/api/interpreter", data={"data": q}, headers=headers, timeout=190)
                        if resp.status_code == 200:
                            data = resp.json()
                            for el in data.get("elements", []):
                                for pt in el.get("geometry", []):
                                    road_points.add((round(pt["lat"], 5), round(pt["lon"], 5)))
                            break  # Success, break retry loop
                        elif resp.status_code == 429:
                            time.sleep(10 * (attempt + 1))  # Rate limited, wait longer
                    except requests.exceptions.RequestException:
                        if attempt == max_retries - 1:
                            logger.warning(f"Failed chunk {i},{j} after {max_retries} attempts.")
                        time.sleep(5 * (attempt + 1))
                
                time.sleep(3) # Be nice to Overpass
                
        df = pd.DataFrame(list(road_points), columns=["latitude", "longitude"])
        out_df = _standardize_coords(df)
        
        if geom is not None and not out_df.empty:
            pts_gdf = gpd.GeoDataFrame(out_df, geometry=gpd.points_from_xy(out_df["longitude"], out_df["latitude"]), crs="EPSG:4326")
            out_df = out_df.loc[pts_gdf.intersects(geom).to_numpy()].reset_index(drop=True)
            
        out_df.to_csv(path, index=False)
        return out_df
    except Exception as e:
        logger.warning(f"Failed to download highways: {e}")
        return pd.DataFrame(columns=["latitude", "longitude"])

def _load_or_download_traffic_nodes(geom=None) -> pd.DataFrame:
    path = RAW_DIR / "osm_traffic_nodes.csv"
    if path.exists():
        return _standardize_coords(pd.read_csv(path, low_memory=False))
        
    logger.info("Downloading traffic bottleneck nodes from Overpass API (this may take a minute)...")
    query_template = """
    [out:json][timeout:190];
    node["highway"~"motorway_junction|traffic_signals"]({min_lat},{min_lon},{max_lat},{max_lon});
    out geom;
    """
    try:
        import requests
        import time
        headers = {"User-Agent": "EVCS-Optimizer/1.0"}
        road_points = set()
        
        lat_bins = np.linspace(INDIA_BOUNDS["lat_min"], INDIA_BOUNDS["lat_max"], 5)
        lon_bins = np.linspace(INDIA_BOUNDS["lon_min"], INDIA_BOUNDS["lon_max"], 5)
        
        for i in range(4):
            for j in range(4):
                min_l, max_l = lat_bins[i], lat_bins[i+1]
                min_ln, max_ln = lon_bins[j], lon_bins[j+1]
                q = query_template.format(min_lat=min_l, min_lon=min_ln, max_lat=max_l, max_lon=max_ln)
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        resp = requests.post("https://overpass-api.de/api/interpreter", data={"data": q}, headers=headers, timeout=190)
                        if resp.status_code == 200:
                            data = resp.json()
                            for el in data.get("elements", []):
                                road_points.add((round(el["lat"], 5), round(el["lon"], 5)))
                            break
                        elif resp.status_code == 429:
                            time.sleep(10 * (attempt + 1))
                    except requests.exceptions.RequestException:
                        time.sleep(5 * (attempt + 1))
                time.sleep(3)
                
        df = pd.DataFrame(list(road_points), columns=["latitude", "longitude"])
        out_df = _standardize_coords(df)
        if geom is not None and not out_df.empty:
            pts_gdf = gpd.GeoDataFrame(out_df, geometry=gpd.points_from_xy(out_df["longitude"], out_df["latitude"]), crs="EPSG:4326")
            out_df = out_df.loc[pts_gdf.intersects(geom).to_numpy()].reset_index(drop=True)
            
        out_df.to_csv(path, index=False)
        return out_df
    except Exception as e:
        logger.warning(f"Failed to download traffic nodes: {e}")
        return pd.DataFrame(columns=["latitude", "longitude"])




def run_pipeline(resolution: int = DEFAULT_GRID_RESOLUTION) -> pd.DataFrame:
    for p in (PROCESSED_DIR, CACHE_DIR, REPORTS_DIR):
        p.mkdir(parents=True, exist_ok=True)

    # ── Load boundaries ───────────────────────────────────────────────────────
    adm1 = gpd.read_file(CURRENT_ADM1_GEOJSON).to_crs(epsg=4326)
    adm2 = gpd.read_file(RAW_DIR / "geoboundaries_adm2.geojson").to_crs(epsg=4326)
    geom = adm1.geometry.union_all() if hasattr(adm1.geometry, "union_all") else adm1.geometry.unary_union

    # ── Load & clean chargers ─────────────────────────────────────────────────
    chargers = _standardize_coords(pd.read_csv(CURRENT_BEE_CSV, low_memory=False))
    for c in ("state", "district"):
        chargers[c] = chargers.get(c, pd.Series("", index=chargers.index)).fillna("").map(_display_name)
    chargers["state_key"] = chargers["state"].map(_normalize_name)
    chargers["district_key"] = chargers["district"].map(_normalize_name)

    # ── Load commercial POIs (used for road accessibility + commercial density) ──
    pois = _standardize_coords(pd.read_csv(RAW_DIR / "overture_commercial_pois.csv", low_memory=False))

    # ── Load airports ─────────────────────────────────────────────────────
    airports = _standardize_coords(pd.read_csv(RAW_DIR / "ourairports_india_airports.csv", low_memory=False).rename(columns={"latitude_deg": "latitude", "longitude_deg": "longitude"}))
    logger.info("Loaded %d airports", len(airports))

    # ── Generate candidate grid clipped to India ──────────────────────────────
    b = geom.bounds
    lats = np.linspace(max(b[1], INDIA_BOUNDS["lat_min"]), min(b[3], INDIA_BOUNDS["lat_max"]), resolution)
    lons = np.linspace(max(b[0], INDIA_BOUNDS["lon_min"]), min(b[2], INDIA_BOUNDS["lon_max"]), resolution)
    lat_g, lon_g = np.meshgrid(lats, lons, indexing="ij")
    cands = pd.DataFrame({"latitude": lat_g.ravel(), "longitude": lon_g.ravel()})
    pts_gdf = gpd.GeoDataFrame(cands, geometry=gpd.points_from_xy(cands["longitude"], cands["latitude"]), crs="EPSG:4326")
    candidates = cands.loc[pts_gdf.intersects(geom).to_numpy()].reset_index(drop=True)

    # ── Assign state / district via spatial join ──────────────────────────────
    pgdf = gpd.GeoDataFrame(candidates.copy(), geometry=gpd.points_from_xy(candidates["longitude"], candidates["latitude"]), crs="EPSG:4326")
    candidates["state"] = ""
    candidates["district"] = ""
    
    joined_state = gpd.sjoin(pgdf, adm1[["NAME_1", "geometry"]], how="left", predicate="within")
    candidates["state"] = joined_state[~joined_state.index.duplicated(keep="first")]["NAME_1"].map(_display_name).fillna("").to_numpy()
    
    joined_dist = gpd.sjoin(pgdf, adm2[["shapeName", "geometry"]], how="left", predicate="within")
    candidates["district"] = joined_dist[~joined_dist.index.duplicated(keep="first")]["shapeName"].map(_display_name).fillna("").to_numpy()
    candidates["state_key"] = candidates["state"].map(_normalize_name)
    candidates["district_key"] = candidates["district"].map(_normalize_name)

    # ── Compute spatial distance features ─────────────────────────────────────
    features = candidates.copy()
    features["nearest_existing_station_distance"] = _nearest_km(chargers, features)
    
    highways = _load_or_download_highways(geom)
    logger.info("Loaded %d highway nodes", len(highways))
    features["nearest_highway_distance"] = _nearest_km(highways, features)

    traffic_nodes = _load_or_download_traffic_nodes(geom)
    logger.info("Loaded %d traffic bottleneck nodes", len(traffic_nodes))
    features["nearest_traffic_node_distance"] = _nearest_km(traffic_nodes, features)

    # ── Commercial POI density (count within 5 km radius) ────────────────────
    if not pois.empty:
        poi_xyz = latlon_to_unit_xyz(pois["latitude"].to_numpy(), pois["longitude"].to_numpy())
        q_xyz = latlon_to_unit_xyz(features["latitude"].to_numpy(), features["longitude"].to_numpy())
        r_chord = 2.0 * np.sin(COMMERCIAL_DENSITY_RADIUS_KM / (2.0 * EARTH_RADIUS_KM))
        poi_tree = KDTree(poi_xyz)
        comm_counts = np.array([len(poi_tree.query_ball_point(p, r=r_chord)) for p in q_xyz], dtype=float)
    else:
        comm_counts = np.zeros(len(features), dtype=float)

    # ── WorldPop population sampling ──────────────────────────────────────────
    pop = pd.Series(0.0, index=features.index)
    try:
        import rasterio
        with rasterio.open(RAW_DIR / "worldpop_india_population_density_1km_2020.tif") as src:
            vals = [s[0] if len(s) else np.nan for s in src.sample(list(zip(features["longitude"], features["latitude"])))]
            pop = pd.Series(vals, index=features.index, dtype=float).clip(lower=0).fillna(0.0)
    except Exception as e:
        logger.warning(f"Failed to read population raster: {e}")

    # ── Score columns ─────────────────────────────────────────────────────────
    features["population_score"] = _minmax(pop)
    features["commercial_density_score"] = _minmax(pd.Series(comm_counts, index=features.index))
    # economic_score: proxy for purchasing power
    features["economic_score"] = features["state_key"].map(STATE_GDP_PER_CAPITA).fillna(0.0)
    features["coverage_gap_score"] = _minmax(features["nearest_existing_station_distance"])
    features["road_accessibility_score"] = _minmax(features["nearest_highway_distance"], invert=True)
    features["traffic_congestion_score"] = _minmax(features["nearest_traffic_node_distance"], invert=True)
    features["ev_density_score"] = features["state_key"].map(STATE_EV_PENETRATION).fillna(0.05)
    
    # ── Calculate final demand score (Pure Demand, No Coverage) ──
    features["demand_score"] = (
        features["ev_density_score"].fillna(0) * 0.30 +
        features["commercial_density_score"].fillna(0) * 0.10 +
        features["traffic_congestion_score"].fillna(0) * 0.10 +
        features["economic_score"].fillna(0) * 0.25 +
        features["population_score"].fillna(0) * 0.15 +
        features["road_accessibility_score"].fillna(0) * 0.10
    ).clip(0.0, 1.0)

    # ── Persist spatial indexes for inspection ────────────────────────────────
    with (CACHE_DIR / "spatial_indexes.pkl").open("wb") as fh:
        pickle.dump({"chargers": chargers[["latitude", "longitude"]], "pois": pois}, fh)

    # ── Save output ───────────────────────────────────────────────────────────
    ordered = ["latitude", "longitude", "state", "district", *SCORE_COLUMNS, *DISTANCE_COLUMNS, "demand_score"]
    out = features[[*ordered, *[c for c in features.columns if c not in ordered and c != "geometry"]]]
    out.to_parquet(DEMAND_FEATURES_PATH, index=False)

    # ── Reports ───────────────────────────────────────────────────────────────
    by_state = out["state"].fillna("").replace("", "Unknown").value_counts().to_dict()
    by_district = out["district"].fillna("").replace("", "Unknown").value_counts().head(500).to_dict()
    cols = [c for c in [*SCORE_COLUMNS, *DISTANCE_COLUMNS, "demand_score"] if c in out.columns]
    _write_json(DATASET_SUMMARY_PATH, {"demand_features": {"records": len(out), "by_state": by_state, "by_district": by_district}})
    _write_json(DATA_QUALITY_REPORT_PATH, {"missing_values": out.isna().sum().to_dict()})
    _write_json(FEATURE_STATISTICS_PATH, {"feature_statistics": out[cols].describe().replace({np.nan: None}).to_dict(), "records": len(out)})

    logger.info("Demand features complete: %d rows", len(out))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", type=int, default=DEFAULT_GRID_RESOLUTION)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    run_pipeline(args.resolution)


if __name__ == "__main__":
    main()
