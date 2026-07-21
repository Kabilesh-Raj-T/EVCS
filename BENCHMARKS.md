# EVCS Benchmarks

Generated with `python scripts/benchmark_evcs.py` using the existing backend code and dataset. The optimization algorithm was not modified for these benchmarks.

## Project Inspection

| Metric | Measured Value |
|---|---:|
| Existing EV charging stations | 39,495 |
| Demand feature candidate locations | 4,694 |
| Generated all-India candidate pool | 10,508 |
| Geographic coverage | India |
| States / UTs loaded | 38 |
| District polygons loaded | 733 |

## Existing Algorithm And Data Layer

- Optimization algorithm: KD-tree accelerated greedy k-center optimizer in `backend/app.py`.
- Candidate generation: grid-based latitude/longitude candidates filtered by the India polygon.
- Demand-scoring pipeline: processed `demand_features.parquet` built from population, airports, boundaries, and OSM-derived features when available.
- Administrative boundaries: India state/UT boundary plus ADM2 district polygons.

## Synthetic Scalability Benchmarks

Each benchmark used the real existing charging-station dataset and an all-India candidate subset. Each runtime is the average of 3 runs measured with `time.perf_counter()`.

| Candidate Locations Processed | Recommended Stations (k) | Runs | Average Optimization Time |
|---:|---:|---:|---:|
| 1,000 | 25 | 3 | 0.0170 s |
| 5,000 | 25 | 3 | 0.0266 s |
| 10,000 | 25 | 3 | 0.0389 s |

## Real-Data Coverage Impact

Coverage impact was measured on 10,000 generated all-India candidate locations using the real existing station dataset.

Before: existing EV charging stations only.

After: existing EV charging stations plus 25 optimized recommended stations.

| Metric | Before | After |
|---|---:|---:|
| Average distance to nearest charger | 14.7407 km | 12.3821 km |
| Maximum distance to nearest charger | 543.3419 km | 83.7184 km |

Average nearest-charger distance improvement: **16.0006%**.

## KD-Tree Vs Naive Nearest-Neighbor Benchmark

This benchmark compared exact nearest-neighbor distances from the same 1,000 query candidate locations to the same 39,495 existing charging stations.

| Method | Runs | Average Time |
|---|---:|---:|
| Naive nearest-neighbor scan | 3 | 1.8748 s |
| KD-tree nearest-neighbor query | 3 | 0.0138 s |

Measured KD-tree speedup: **135.68x**.

Maximum distance delta between naive and KD-tree results: **0.0 km**.

## Resume Bullets

- Built a KD-tree accelerated EV charging station optimizer that processed 10,000 candidate locations in 0.0389 seconds and generated 25 recommended station sites across India.
- Improved simulated all-India charging coverage by reducing average nearest-charger distance by 16.0% and achieved a 135.68x nearest-neighbor speedup over naive scanning.
