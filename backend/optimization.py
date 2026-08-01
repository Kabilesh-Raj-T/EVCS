import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial import KDTree

from utils import (
    latlon_to_unit_xyz,
    chord_to_great_circle_km,
    distance_km_between_points,
    generate_candidate_points,
)
from database import load_demand_features

logger = logging.getLogger("evcsapi")

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
