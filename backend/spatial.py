"""Spatial region building and boundary utilities."""

import logging
import numpy as np
import pandas as pd
import geopandas as gpd

from config import ADM2_GEOJSON_PATH, INDIA_DEFAULT_BOUNDS
from utils import display_region_name, normalize_name

logger = logging.getLogger("evcsapi")


def build_state_regions(india_gdf: gpd.GeoDataFrame) -> dict:
    regions = {}
    for raw_name, group in india_gdf.groupby("NAME_1"):
        name = display_region_name(raw_name)
        key = normalize_name(name)
        if not key:
            continue
        geom = group.geometry.union_all() if hasattr(group.geometry, "union_all") else group.geometry.unary_union
        if key in regions:
            geom = regions[key]["geometry"].union(geom)
        b = list(geom.bounds)
        regions[key] = {"name": name, "bounds": {"lat_min": b[1], "lat_max": b[3], "lon_min": b[0], "lon_max": b[2]}, "geometry": geom, "districts": {}}
    return regions


def load_adm2_boundary() -> gpd.GeoDataFrame:
    adm2 = gpd.read_file(ADM2_GEOJSON_PATH).to_crs(epsg=4326)
    if adm2.empty:
        raise ValueError(f"ADM2 GeoJSON is empty: {ADM2_GEOJSON_PATH}")
    return adm2


def attach_district_boundaries(state_regions: dict, district_gdf: gpd.GeoDataFrame, india_gdf: gpd.GeoDataFrame) -> None:
    centroids = district_gdf[["shapeName", "geometry"]].copy()
    centroids["geometry"] = centroids.geometry.representative_point()
    joined = gpd.sjoin(centroids, india_gdf[["NAME_1", "geometry"]], how="left", predicate="within")
    for idx, row in joined.iterrows():
        s_key = normalize_name(display_region_name(row.get("NAME_1", "")))
        d_name = display_region_name(row.get("shapeName", ""))
        d_key = normalize_name(d_name)
        if not s_key or not d_key or s_key not in state_regions:
            continue
        geom = district_gdf.loc[idx, "geometry"]
        districts = state_regions[s_key]["districts"]
        if d_key in districts:
            geom = districts[d_key]["geometry"].union(geom)
        b = list(geom.bounds)
        districts[d_key] = {"name": d_name, "bounds": {"lat_min": b[1], "lat_max": b[3], "lon_min": b[0], "lon_max": b[2]}, "geometry": geom, "data": pd.DataFrame()}


def serialize_regions(state_regions: dict) -> dict:
    return {
        "default_bounds": INDIA_DEFAULT_BOUNDS,
        "states": [{"name": s["name"], "bounds": s["bounds"],
                     "districts": [{"name": d["name"], "bounds": d["bounds"]} for d in sorted(s["districts"].values(), key=lambda x: x["name"])]}
                   for s in sorted(state_regions.values(), key=lambda x: x["name"])],
    }


def station_coords_within_geometry(geometry, stations: pd.DataFrame) -> np.ndarray:
    pts = gpd.GeoSeries(gpd.points_from_xy(stations["longitude_num"], stations["latitude_num"]), crs="EPSG:4326")
    return stations.loc[pts.intersects(geometry).to_numpy(), ["latitude_num", "longitude_num"]].to_numpy(dtype=float)
