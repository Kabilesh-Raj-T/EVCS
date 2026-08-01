import os
import logging
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import box

from config import ADM2_GEOJSON_PATH, INDIA_DEFAULT_BOUNDS
from utils import (
    display_region_name,
    normalize_name,
    merge_geometries,
    bounds_to_dict,
    first_existing_column,
    coordinate_bounds,
    geometry_from_series,
)

logger = logging.getLogger("evcsapi")

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
    return box(bounds["lon_min"], bounds["lat_min"], bounds["lon_max"], bounds["lat_max"])

def station_coords_within_geometry(geometry, stations_df, lat_col, lon_col):
    if stations_df is None or geometry is None or geometry.is_empty:
        return np.empty((0, 2))
    station_points = gpd.GeoDataFrame(
        stations_df,
        geometry=gpd.points_from_xy(stations_df[lon_col], stations_df[lat_col]),
        crs="EPSG:4326",
    )
    mask = station_points.intersects(geometry)
    return stations_df.loc[mask.to_numpy(), [lat_col, lon_col]].to_numpy(dtype=float)
