"""Greedy K-Center and Weighted Demand optimization for EVCS placement."""

import logging
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import KDTree

from database import load_demand_features
from utils import chord_to_great_circle_km, generate_candidate_points, latlon_to_unit_xyz

logger = logging.getLogger("evcsapi")

def _norm(arr: np.ndarray) -> np.ndarray:
    mn, mx = np.nanmin(arr), np.nanmax(arr)
    return np.zeros(len(arr)) if np.isclose(mn, mx) or not np.isfinite(mx) else np.clip((arr - mn) / (mx - mn), 0, 1)

def _core_optimizer(coords: np.ndarray, existing_coords: np.ndarray, demand: np.ndarray, k: int, demand_weight: float) -> tuple[list[int], list[float], np.ndarray]:
    cand_xyz = latlon_to_unit_xyz(coords[:, 0], coords[:, 1])
    if existing_coords.size == 0:
        min_dists = np.full(len(coords), np.inf)
    else:
        d, _ = KDTree(latlon_to_unit_xyz(existing_coords[:, 0], existing_coords[:, 1])).query(cand_xyz)
        min_dists = chord_to_great_circle_km(d)

    selected_indices = []
    selected_scores = []
    selected_set = set()
    coverage_weight = 1.0 - demand_weight
    
    for _ in range(k):
        coverage = _norm(min_dists) if np.isfinite(min_dists).any() else np.ones(len(coords))
        score = (demand_weight * demand + coverage_weight * coverage) if np.nanmax(demand) > 0 else coverage
        
        # Prevent picking the same point twice
        if selected_indices:
            score[selected_indices] = -np.inf
            
        # Prevent exact stacking but allow dense neighborhoods by penalizing within 1.0 km
        score[min_dists < 1.0] -= 1000.0
            
        best_idx = int(np.argmax(score))
        if best_idx in selected_set: 
            break
            
        selected_indices.append(best_idx)
        selected_scores.append(float(score[best_idx]))
        selected_set.add(best_idx)
        chord = np.linalg.norm(cand_xyz - cand_xyz[best_idx], axis=1)
        min_dists = np.minimum(min_dists, chord_to_great_circle_km(chord))
        
    return selected_indices, selected_scores, min_dists

def optimize_locations(region: dict, k: int, resolution: int, demand_weight: float = 0.85) -> list:
    """Iteratively select k locations balancing demand and dynamically updated coverage."""
    if k <= 0:
        return []

    features = load_demand_features()
    pts = gpd.GeoDataFrame(features, geometry=gpd.points_from_xy(features["longitude"], features["latitude"]), crs="EPSG:4326")
    cands = features.loc[pts.intersects(region["geometry"]).to_numpy()].copy()

    if len(cands) < max(20, k * 4):
        b = region["bounds"]
        gen = generate_candidate_points(b["lat_min"], b["lat_max"], b["lon_min"], b["lon_max"], resolution, region["geometry"])
        if gen.size > 0:
            dists, idxs = KDTree(latlon_to_unit_xyz(features["latitude"].to_numpy(), features["longitude"].to_numpy())).query(latlon_to_unit_xyz(gen[:, 0], gen[:, 1]), k=3)
            
            # Inverse distance weighting for smooth demand scores
            dists = np.maximum(dists, 1e-7)  # prevent division by zero
            weights = 1.0 / (dists ** 2)
            interpolated_demand = np.sum(weights * features["demand_score"].to_numpy()[idxs], axis=1) / np.sum(weights, axis=1)
            
            extra = pd.DataFrame({"latitude": gen[:, 0], "longitude": gen[:, 1],
                                  "demand_score": interpolated_demand,
                                  "state": features.iloc[idxs[:, 0]]["state"].to_numpy(),
                                  "district": features.iloc[idxs[:, 0]]["district"].to_numpy()})
            cands = pd.concat([cands, extra], ignore_index=True)

    if cands.empty:
        return []

    coords = cands[["latitude", "longitude"]].to_numpy(dtype=float)
    demand = _norm(cands["demand_score"].to_numpy(dtype=float))
    
    selected_indices, selected_scores, _ = _core_optimizer(coords, region["coords"], demand, k, demand_weight)
    
    selected = []
    for idx, s_score in zip(selected_indices, selected_scores):
        row = cands.iloc[idx]
        selected.append({"lat": float(coords[idx, 0]), "lon": float(coords[idx, 1]),
                         "demand_score": float(row["demand_score"]), "selection_score": s_score,
                         "state": row["state"], "district": row["district"]})
                         
    return selected
