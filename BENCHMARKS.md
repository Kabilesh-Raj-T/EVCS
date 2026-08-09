# EVCS Benchmarks

Generated using the new 29,651-candidate demand feature dataset (Resolution 300).

## Dataset

| Metric | Value |
|---|---:|
| Existing EV charging stations | 39,640 |
| Demand feature candidate locations | 29,651 |
| Generated all-India candidate pool | 29,651 |
| Geographic coverage | All India |
| States / UTs loaded | 36 |
| District polygons loaded | 733 |

## Algorithm & Data Layer

- **Optimization Engine**: KD-tree accelerated Greedy K-Center & Multi-Objective Weighted Demand Optimizer (`backend/optimization.py`), featuring IDW (Inverse Distance Weighting) interpolation for dynamic point generation and a 1.0 km spatial anti-clustering penalty.
- **Candidate Mesh**: 300 × 300 bounding grid intersected with GADM land polygon geometry.
- **4-Feature Demand Scoring**: `demand_features.parquet` built from population density rasters (WorldPop), commercial POI density (Overture Maps), airport proximity (OurAirports), and charger coverage gaps. (OSM processing completely removed for extreme lean performance).
- **Administrative Boundaries**: India GADM ADM1 state/UT boundaries and 733 ADM2 district polygons.

## Scalability Benchmarks

Runtimes are the median of 5 runs measured with `time.perf_counter()` on the real 39,640-station dataset.

| Candidate Locations | Recommended Stations (k) | Runs | Avg Optimization Time |
|---:|---:|---:|---:|
| 1,000 | 25 | 5 | 0.024 s |
| 5,000 | 25 | 5 | 0.030 s |
| 10,000 | 25 | 5 | 0.044 s |

## Coverage Impact

Evaluated on 10,000 all-India candidate locations before and after adding 25 recommended stations.

| Metric | Before | After | Improvement |
|---|---:|---:|---:|
| Average distance to nearest charger | 14.633 km | 12.396 km | **−15.29%** |
| Maximum distance to nearest charger | 543.052 km | 82.751 km | **−84.76%** |

## KD-Tree vs Naive Nearest-Neighbor

Compares finding the nearest of 39,640 existing stations for 1,000 query locations.
Measured over **10 runs with a warm-up pass** using `time.perf_counter()`. Speedup reported as median/median.

| Method | Median Time | Speedup |
|---|---:|---:|
| Naive Python scan (for-loop over all 39,640 refs) | 1.440 s | 1× |
| KD-tree (build + query, one-shot) | 0.019 s | **~75×** |
| KD-tree (query only — tree built once at startup) | 0.001 s | **~1,090×** |

- **One-shot speedup (~75×)**: fair comparison where both methods start from raw coordinates.
- **Production speedup (~1,090×)**: reflects actual runtime — the KD-tree is built once per
  `k_center_greedy` call and then `tree.query()` is reused for all k placement iterations.
- Maximum distance delta between naive and KD-tree results: **0.000 km** (results are identical).

### Why earlier runs showed 131×

The previous figure used only 3 runs with no warm-up. The naive Python loop has
≈14% timing variance (stdev ≈ 0.17 s on a 1.23 s mean) — a single slow OS-scheduled
run in a 3-sample average inflates the apparent speedup significantly. Ten runs with a
warm-up pass yields a stable **~75× one-shot** and **~1,090× production** figure.

## Resume / Portfolio Bullet

- Built a KD-tree accelerated geospatial site-recommendation system for EV charging across India,
  processing 13,122 demand candidate locations across 39,640 existing stations and 733 district boundaries.
- Accelerated spatial nearest-neighbor search by **~75× over naive linear scans** in a one-shot comparison
  (1.44 s → 0.019 s); production throughput is **~1,090×** faster when the index is reused across placement iterations.
- Reduced maximum charger isolation distance by **84.76%** (543 km → 82 km) and average distance by **15.29%**.
