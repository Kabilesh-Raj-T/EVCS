"""Build demand-aware feature columns for candidate EV charging locations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from backend.scoring.demand_scoring import compute_demand_score

from .cache import SpatialIndex, build_spatial_index, query_nearest_distance_km, save_pickle
from .config import COMMERCIAL_DENSITY_RADIUS_KM, DEFAULT_NORMALIZATION_METHOD
from .feature_normalization import normalize_features, normalize_series


logger = logging.getLogger(__name__)


@dataclass
class SourceDatasets:
    """Cleaned datasets used to construct the demand feature table."""

    existing_chargers: pd.DataFrame
    airports: pd.DataFrame = field(default_factory=pd.DataFrame)
    roads: pd.DataFrame = field(default_factory=pd.DataFrame)
    highways: pd.DataFrame = field(default_factory=pd.DataFrame)
    fuel_stations: pd.DataFrame = field(default_factory=pd.DataFrame)
    railway_stations: pd.DataFrame = field(default_factory=pd.DataFrame)
    bus_stations: pd.DataFrame = field(default_factory=pd.DataFrame)
    commercial_pois: pd.DataFrame = field(default_factory=pd.DataFrame)
    city_centres: pd.DataFrame = field(default_factory=pd.DataFrame)
    ev_registrations: pd.DataFrame = field(default_factory=pd.DataFrame)
    worldpop_raster: Path | None = None


DISTANCE_COLUMNS = [
    "nearest_existing_station_distance",
    "nearest_road_distance",
    "nearest_highway_distance",
    "nearest_city_distance",
    "nearest_airport_distance",
    "nearest_fuel_station_distance",
    "nearest_bus_station_distance",
    "nearest_railway_station_distance",
]

SCORE_COLUMNS = [
    "population_score",
    "ev_registration_score",
    "road_accessibility_score",
    "commercial_density_score",
    "transport_hub_score",
    "tourism_score",
    "charger_load_score",
]


def _empty_distance(length: int) -> np.ndarray:
    return np.full(length, np.nan, dtype=float)


def _nearest(indexes: dict[str, SpatialIndex], key: str, candidates: pd.DataFrame) -> np.ndarray:
    index = indexes.get(key)
    if index is None or index.is_empty:
        return _empty_distance(len(candidates))
    return query_nearest_distance_km(index, candidates, "latitude", "longitude")


def _count_within_radius(index: SpatialIndex, candidates: pd.DataFrame, radius_km: float) -> np.ndarray:
    if index.is_empty or candidates.empty:
        return np.zeros(len(candidates), dtype=float)
    query_coords = candidates[["latitude", "longitude"]].to_numpy(dtype=float)
    from .cache import chord_to_great_circle_km, latlon_to_unit_xyz

    query_xyz = latlon_to_unit_xyz(query_coords)
    radius_chord = 2.0 * np.sin(radius_km / (2.0 * 6371.0))
    counts = np.array([len(index.tree.query_ball_point(point, r=radius_chord)) for point in query_xyz], dtype=float)
    return counts


def _osm_coverage_mask(candidates: pd.DataFrame, datasets: SourceDatasets) -> pd.Series:
    """Return candidate rows covered by the currently loaded OSM extract layers."""

    osm_layers = [
        datasets.roads,
        datasets.highways,
        datasets.fuel_stations,
        datasets.railway_stations,
        datasets.bus_stations,
        datasets.commercial_pois,
    ]
    frames = [
        df[["latitude", "longitude"]]
        for df in osm_layers
        if not df.empty and {"latitude", "longitude"}.issubset(df.columns)
    ]
    if not frames:
        return pd.Series(False, index=candidates.index)

    coords = pd.concat(frames, ignore_index=True)
    lat_min = float(coords["latitude"].min())
    lat_max = float(coords["latitude"].max())
    lon_min = float(coords["longitude"].min())
    lon_max = float(coords["longitude"].max())
    return (
        candidates["latitude"].between(lat_min, lat_max)
        & candidates["longitude"].between(lon_min, lon_max)
    )


def _extract_population(candidates: pd.DataFrame, raster_path: Path | None) -> pd.Series:
    if raster_path is None or not raster_path.exists():
        logger.warning("WorldPop raster is missing; population_score will be zero")
        return pd.Series(np.zeros(len(candidates)), index=candidates.index, dtype=float)

    try:
        import rasterio
    except ImportError:
        logger.warning("rasterio is not installed; population_score will be zero")
        return pd.Series(np.zeros(len(candidates)), index=candidates.index, dtype=float)

    coords = list(zip(candidates["longitude"], candidates["latitude"]))
    with rasterio.open(raster_path) as src:
        values = [sample[0] if len(sample) else np.nan for sample in src.sample(coords)]
        nodata = src.nodata
    series = pd.Series(values, index=candidates.index, dtype=float)
    if nodata is not None:
        series = series.replace(nodata, np.nan)
    return series.clip(lower=0).fillna(0.0)


def _join_ev_registrations(candidates: pd.DataFrame, registrations: pd.DataFrame) -> pd.Series:
    if registrations.empty:
        logger.warning("VAHAN registration data is missing; ev_registration_score will be zero")
        return pd.Series(np.zeros(len(candidates)), index=candidates.index, dtype=float)

    value_col = _registration_value_column(registrations)
    if value_col is None:
        logger.warning("VAHAN registration data has no numeric value column")
        return pd.Series(np.zeros(len(candidates)), index=candidates.index, dtype=float)

    regs = registrations.copy()
    state_col = _first_existing(regs, ["state", "State", "state_name", "State Name"])
    district_col = _first_existing(regs, ["district", "District", "district_name", "RTO", "rto"])
    if state_col is None:
        logger.warning("VAHAN registration data has no state column")
        return pd.Series(np.zeros(len(candidates)), index=candidates.index, dtype=float)

    from .clean_data import normalize_name

    regs["state_key"] = regs[state_col].map(normalize_name)
    grouped_cols = ["state_key"]
    if district_col is not None:
        regs["district_key"] = regs[district_col].map(normalize_name)
        grouped_cols.append("district_key")

    lookup = regs.groupby(grouped_cols)[value_col].sum().reset_index()
    merged = candidates.merge(lookup, how="left", on=grouped_cols)
    if merged[value_col].isna().all() and "district_key" in grouped_cols:
        state_lookup = regs.groupby("state_key")[value_col].sum().reset_index()
        merged = candidates.merge(state_lookup, how="left", on="state_key")
    return pd.to_numeric(merged[value_col], errors="coerce").fillna(0.0)


def _registration_value_column(df: pd.DataFrame) -> str | None:
    preferred = ["ev_count", "registrations", "registered_vehicles", "vehicle_count", "count", "total"]
    for col in preferred:
        if col in df.columns and pd.to_numeric(df[col], errors="coerce").notna().any():
            return col
    numeric_cols = [col for col in df.columns if pd.to_numeric(df[col], errors="coerce").notna().any()]
    return numeric_cols[-1] if numeric_cols else None


def _first_existing(df: pd.DataFrame, cols: list[str]) -> str | None:
    return next((col for col in cols if col in df.columns), None)


class DemandFeatureBuilder:
    """Build normalized demand features and demand scores for candidate points."""

    def __init__(self, normalization_method: str = DEFAULT_NORMALIZATION_METHOD):
        self.normalization_method = normalization_method

    def build(self, candidates: pd.DataFrame, datasets: SourceDatasets) -> pd.DataFrame:
        """Build the complete demand feature dataframe."""

        if candidates.empty:
            raise ValueError("Cannot build demand features from an empty candidate set")

        features = candidates.copy().reset_index(drop=True)
        indexes = self._build_indexes(datasets)
        osm_covered = _osm_coverage_mask(features, datasets)
        features["osm_coverage_available"] = osm_covered.astype(bool)

        features["nearest_existing_station_distance"] = _nearest(indexes, "existing_chargers", features)
        features["nearest_road_distance"] = _nearest(indexes, "roads", features)
        features["nearest_highway_distance"] = _nearest(indexes, "highways", features)
        features["nearest_city_distance"] = _nearest(indexes, "city_centres", features)
        features["nearest_airport_distance"] = _nearest(indexes, "airports", features)
        features["nearest_fuel_station_distance"] = _nearest(indexes, "fuel_stations", features)
        features["nearest_bus_station_distance"] = _nearest(indexes, "bus_stations", features)
        features["nearest_railway_station_distance"] = _nearest(indexes, "railway_stations", features)
        osm_distance_cols = [
            "nearest_road_distance",
            "nearest_highway_distance",
            "nearest_fuel_station_distance",
            "nearest_bus_station_distance",
            "nearest_railway_station_distance",
        ]
        features.loc[~osm_covered, osm_distance_cols] = np.nan

        population_raw = _extract_population(features, datasets.worldpop_raster)
        ev_raw = _join_ev_registrations(features, datasets.ev_registrations)
        commercial_raw = _count_within_radius(indexes["commercial_pois"], features, COMMERCIAL_DENSITY_RADIUS_KM)
        commercial_raw = np.where(osm_covered.to_numpy(), commercial_raw, 0.0)

        features["population_score"] = normalize_series(population_raw, self.normalization_method)
        features["ev_registration_score"] = normalize_series(ev_raw, self.normalization_method)
        features["commercial_density_score"] = normalize_series(pd.Series(commercial_raw), self.normalization_method)

        road_distance = pd.concat(
            [features["nearest_road_distance"], features["nearest_highway_distance"]],
            axis=1,
        ).min(axis=1, skipna=True)
        features["road_accessibility_score"] = normalize_series(road_distance, self.normalization_method, invert=True)
        transport_distance = pd.concat(
            [
                features["nearest_airport_distance"],
                features["nearest_bus_station_distance"],
                features["nearest_railway_station_distance"],
            ],
            axis=1,
        ).min(axis=1, skipna=True)
        features["transport_hub_score"] = normalize_series(transport_distance, self.normalization_method, invert=True)

        features["tourism_score"] = 0.0
        features["charger_load_score"] = 0.0

        features[SCORE_COLUMNS] = normalize_features(
            features,
            SCORE_COLUMNS,
            method=self.normalization_method,
        )[SCORE_COLUMNS]
        features["demand_score"] = compute_demand_score(features)

        ordered_columns = [
            "latitude",
            "longitude",
            "state",
            "district",
            *SCORE_COLUMNS,
            *DISTANCE_COLUMNS,
            "demand_score",
        ]
        passthrough = [col for col in features.columns if col not in ordered_columns and col != "geometry"]
        return features[[*ordered_columns, *passthrough]]

    def _build_indexes(self, datasets: SourceDatasets) -> dict[str, SpatialIndex]:
        indexes = {
            "existing_chargers": build_spatial_index(datasets.existing_chargers, name="existing_chargers"),
            "roads": build_spatial_index(datasets.roads, name="road_network"),
            "highways": build_spatial_index(datasets.highways, name="highways"),
            "fuel_stations": build_spatial_index(datasets.fuel_stations, name="fuel_stations"),
            "railway_stations": build_spatial_index(datasets.railway_stations, name="railway_stations"),
            "bus_stations": build_spatial_index(datasets.bus_stations, name="bus_stations"),
            "airports": build_spatial_index(datasets.airports, name="airports"),
            "commercial_pois": build_spatial_index(datasets.commercial_pois, name="commercial_pois"),
            "city_centres": build_spatial_index(datasets.city_centres, name="city_centres"),
        }
        save_pickle("spatial_indexes", indexes)
        return indexes


def geodataframe_to_points(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Convert point or linear GeoDataFrame features to representative lat/lon points."""

    if gdf.empty:
        return pd.DataFrame(columns=["latitude", "longitude"])
    projected = gdf.to_crs(epsg=4326).copy()
    projected["geometry"] = projected.geometry.representative_point()
    projected["longitude"] = projected.geometry.x
    projected["latitude"] = projected.geometry.y
    return pd.DataFrame(projected.drop(columns="geometry"))


def feature_statistics(features: pd.DataFrame) -> dict[str, Any]:
    """Return summary statistics for generated feature columns."""

    cols = [col for col in [*SCORE_COLUMNS, *DISTANCE_COLUMNS, "demand_score"] if col in features.columns]
    stats = features[cols].describe().replace({np.nan: None}).to_dict()
    return {"feature_statistics": stats, "records": len(features)}
