"""Default demand-score weights."""

from __future__ import annotations


DEFAULT_DEMAND_WEIGHTS = {
    "population_score": 0.30,        # WorldPop density
    "commercial_density_score": 0.30, # POI count within 5 km radius
    "coverage_gap_score": 0.30,       # Distance to nearest existing EV station
    "airport_proximity_score": 0.10,  # Inverse distance to nearest airport (urban proxy)
}

