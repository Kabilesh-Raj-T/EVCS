from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import KDTree

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import app as evcs_app  # noqa: E402


BENCHMARK_COUNTS = [1_000, 5_000, 10_000]
RUNS = 3
K = 25
KD_TREE_COMPARISON_CANDIDATES = 1_000


def evenly_sample(points: np.ndarray, count: int) -> np.ndarray:
    if len(points) < count:
        raise ValueError(f"Need {count} candidates, only generated {len(points)}")
    indices = np.linspace(0, len(points) - 1, count, dtype=int)
    return points[indices]


def nearest_distances_kdtree(reference_coords: np.ndarray, query_coords: np.ndarray) -> np.ndarray:
    ref_xyz = evcs_app.latlon_to_unit_xyz(reference_coords[:, 0], reference_coords[:, 1])
    query_xyz = evcs_app.latlon_to_unit_xyz(query_coords[:, 0], query_coords[:, 1])
    tree = KDTree(ref_xyz)
    chord_dist, _ = tree.query(query_xyz, k=1)
    return evcs_app.chord_to_great_circle_km(chord_dist)


def nearest_distances_naive(reference_coords: np.ndarray, query_coords: np.ndarray) -> np.ndarray:
    ref_xyz = evcs_app.latlon_to_unit_xyz(reference_coords[:, 0], reference_coords[:, 1])
    query_xyz = evcs_app.latlon_to_unit_xyz(query_coords[:, 0], query_coords[:, 1])
    min_chord = np.empty(len(query_xyz), dtype=float)
    for idx, point in enumerate(query_xyz):
        min_chord[idx] = np.linalg.norm(ref_xyz - point, axis=1).min()
    return evcs_app.chord_to_great_circle_km(min_chord)


def time_call(func, *args):
    started = time.perf_counter()
    result = func(*args)
    return result, time.perf_counter() - started


def main() -> None:
    evcs_app.load_data()
    all_india = evcs_app.resolve_region({"region_type": "all_india"})

    dense_candidates = evcs_app.generate_candidate_points(
        all_india["bounds"]["lat_min"],
        all_india["bounds"]["lat_max"],
        all_india["bounds"]["lon_min"],
        all_india["bounds"]["lon_max"],
        180,
        all_india["geometry"],
    )

    demand_features = evcs_app.load_demand_features()
    state_count = len(evcs_app.REGION_OPTIONS.get("states", []))
    district_count = sum(len(state.get("districts", [])) for state in evcs_app.REGION_OPTIONS.get("states", []))

    runtime_results = []
    for count in BENCHMARK_COUNTS:
        candidates = evenly_sample(dense_candidates, count)
        elapsed = []
        selected_count = 0
        for _ in range(RUNS):
            selected, duration = time_call(evcs_app.k_center_greedy, evcs_app.existing_coords, candidates, K)
            elapsed.append(duration)
            selected_count = len(selected)
        runtime_results.append(
            {
                "candidate_locations_processed": count,
                "recommended_stations_k": K,
                "runs": RUNS,
                "average_seconds": statistics.fmean(elapsed),
                "individual_seconds": elapsed,
                "selected_count": selected_count,
            }
        )

    impact_candidates = evenly_sample(dense_candidates, 10_000)
    optimized_locations = np.asarray(
        evcs_app.k_center_greedy(evcs_app.existing_coords, impact_candidates, K),
        dtype=float,
    )
    before_distances = nearest_distances_kdtree(evcs_app.existing_coords, impact_candidates)
    after_reference = np.vstack([evcs_app.existing_coords, optimized_locations])
    after_distances = nearest_distances_kdtree(after_reference, impact_candidates)
    avg_before = float(np.mean(before_distances))
    avg_after = float(np.mean(after_distances))
    max_before = float(np.max(before_distances))
    max_after = float(np.max(after_distances))
    avg_improvement_pct = ((avg_before - avg_after) / avg_before) * 100.0

    kd_candidates = evenly_sample(dense_candidates, KD_TREE_COMPARISON_CANDIDATES)
    naive_times = []
    kdtree_times = []
    max_distance_delta_km = None
    for _ in range(RUNS):
        naive_distances, naive_duration = time_call(nearest_distances_naive, evcs_app.existing_coords, kd_candidates)
        kd_distances, kd_duration = time_call(nearest_distances_kdtree, evcs_app.existing_coords, kd_candidates)
        naive_times.append(naive_duration)
        kdtree_times.append(kd_duration)
        max_distance_delta_km = float(np.max(np.abs(naive_distances - kd_distances)))

    kd_speedup = statistics.fmean(naive_times) / statistics.fmean(kdtree_times)

    results = {
        "dataset": {
            "existing_charging_stations": int(len(evcs_app.existing_coords)),
            "demand_feature_candidate_locations": int(len(demand_features)),
            "generated_candidate_pool": int(len(dense_candidates)),
            "states_or_uts": state_count,
            "districts": district_count,
            "covered_region": "India",
        },
        "algorithm": {
            "optimization": "KD-tree accelerated greedy k-center",
            "demand_pipeline": "Processed demand_features.parquet from population, airports, boundaries, and OSM-derived features when available",
        },
        "runtime_benchmarks": runtime_results,
        "coverage_impact": {
            "evaluation_candidate_locations": int(len(impact_candidates)),
            "recommended_stations_k": K,
            "average_nearest_charger_km_before": avg_before,
            "average_nearest_charger_km_after": avg_after,
            "maximum_nearest_charger_km_before": max_before,
            "maximum_nearest_charger_km_after": max_after,
            "average_distance_improvement_pct": avg_improvement_pct,
        },
        "kdtree_vs_naive": {
            "query_candidate_locations": KD_TREE_COMPARISON_CANDIDATES,
            "reference_existing_stations": int(len(evcs_app.existing_coords)),
            "runs": RUNS,
            "naive_average_seconds": statistics.fmean(naive_times),
            "kdtree_average_seconds": statistics.fmean(kdtree_times),
            "speedup_x": kd_speedup,
            "max_distance_delta_km": max_distance_delta_km,
        },
    }

    output = ROOT / "reports" / "benchmark_results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
