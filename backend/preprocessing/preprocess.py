"""End-to-end preprocessing pipeline for demand-aware EVCS optimization."""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

from .cache import ensure_directories, write_json
from .clean_data import display_name, normalize_name, read_table, standardize_point_dataset
from .config import (
    CURRENT_BEE_CSV,
    DATA_QUALITY_REPORT_PATH,
    DATASET_SUMMARY_PATH,
    DEFAULT_GRID_RESOLUTION,
    DEFAULT_NORMALIZATION_METHOD,
    DEMAND_FEATURES_CSV_FALLBACK,
    DEMAND_FEATURES_PATH,
    FEATURE_STATISTICS_PATH,
    INDIA_BOUNDS,
    RAW_DIR,
)
from .download_data import write_source_manifest
from .feature_builder import DemandFeatureBuilder, SourceDatasets, feature_statistics, geodataframe_to_points
from .spatial_join import (
    assign_administrative_regions,
    coverage_by_region,
    india_geometry,
    load_boundary,
    points_to_gdf,
)


logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Runtime configuration for the preprocessing pipeline."""

    grid_resolution: int = DEFAULT_GRID_RESOLUTION
    normalization_method: str = DEFAULT_NORMALIZATION_METHOD
    output_path: Path = DEMAND_FEATURES_PATH
    raw_dir: Path = RAW_DIR


def run_pipeline(config: PipelineConfig | None = None) -> pd.DataFrame:
    """Run the complete preprocessing and feature-engineering workflow."""

    config = config or PipelineConfig()
    ensure_directories()
    write_source_manifest()

    reports: dict[str, Any] = {"cleaning": {}, "missing_sources": [], "notes": []}

    adm1 = load_boundary("adm1")
    adm2 = load_boundary("adm2")
    if adm2 is None:
        reports["notes"].append("ADM2 boundary is missing; district assignment falls back to nearest BEE station district.")

    chargers, charger_report = load_existing_chargers()
    reports["cleaning"]["existing_chargers"] = charger_report

    datasets = SourceDatasets(
        existing_chargers=chargers,
        airports=load_optional_points("ourairports", ["*airports*.csv", "*ourairports*.csv"], reports),
        roads=load_osm_points("roads", reports),
        highways=load_osm_points("highways", reports),
        fuel_stations=load_osm_points("fuel_stations", reports),
        railway_stations=load_osm_points("railway_stations", reports),
        bus_stations=load_osm_points("bus_stations", reports),
        commercial_pois=load_osm_points("commercial_pois", reports),
        city_centres=load_city_centres(reports),
        ev_registrations=load_ev_registrations(reports),
        worldpop_raster=find_first_file(["*worldpop*.tif", "*population*density*.tif", "*ppp*.tif", "*.tif"]),
    )
    if datasets.worldpop_raster is None:
        reports["missing_sources"].append("worldpop_india_population_density")

    candidates = build_candidate_grid(adm1, config.grid_resolution)
    candidates = assign_administrative_regions(candidates, adm1, adm2)
    candidates = fill_missing_districts_from_chargers(candidates, chargers)

    builder = DemandFeatureBuilder(normalization_method=config.normalization_method)
    features = builder.build(candidates, datasets)
    write_features(features, config.output_path)
    write_reports(features, datasets, reports)
    logger.info("Demand feature dataset complete: %d rows", len(features))
    return features


def load_existing_chargers() -> tuple[pd.DataFrame, dict[str, object]]:
    """Load and clean the current BEE charging station dataset."""

    if not CURRENT_BEE_CSV.exists():
        raise FileNotFoundError(f"BEE charging station CSV not found: {CURRENT_BEE_CSV}")
    df = pd.read_csv(CURRENT_BEE_CSV, low_memory=False)
    cleaned, report = standardize_point_dataset(df, "bee_ev_charging_stations")
    for col in ("state", "district"):
        if col not in cleaned.columns:
            cleaned[col] = ""
        cleaned[col] = cleaned[col].fillna("").map(display_name)
    cleaned["state_key"] = cleaned["state"].map(normalize_name)
    cleaned["district_key"] = cleaned["district"].map(normalize_name)
    return cleaned, report


def build_candidate_grid(adm1: gpd.GeoDataFrame | None, resolution: int) -> pd.DataFrame:
    """Create candidate grid-cell centroids inside the India boundary."""

    if resolution <= 0 or resolution > 1000:
        raise ValueError("grid_resolution must be between 1 and 1000")

    geometry = india_geometry(adm1)
    min_lon, min_lat, max_lon, max_lat = geometry.bounds
    min_lat = max(float(min_lat), INDIA_BOUNDS["lat_min"])
    max_lat = min(float(max_lat), INDIA_BOUNDS["lat_max"])
    min_lon = max(float(min_lon), INDIA_BOUNDS["lon_min"])
    max_lon = min(float(max_lon), INDIA_BOUNDS["lon_max"])

    lat_vals = np.linspace(min_lat, max_lat, resolution)
    lon_vals = np.linspace(min_lon, max_lon, resolution)
    lat_grid, lon_grid = np.meshgrid(lat_vals, lon_vals, indexing="ij")
    candidates = pd.DataFrame({"latitude": lat_grid.ravel(), "longitude": lon_grid.ravel()})
    candidate_gdf = points_to_gdf(candidates)
    mask = candidate_gdf.intersects(geometry)
    out = candidates.loc[mask.to_numpy()].reset_index(drop=True)
    logger.info("Generated %d candidate grid cells at resolution %d", len(out), resolution)
    if out.empty:
        raise ValueError("No candidate grid points generated inside India boundary")
    return out


def fill_missing_districts_from_chargers(candidates: pd.DataFrame, chargers: pd.DataFrame) -> pd.DataFrame:
    """Approximate district assignment from nearest BEE station where ADM2 is absent."""

    if "district" not in candidates.columns or candidates["district"].fillna("").astype(str).str.len().gt(0).all():
        return candidates
    if chargers.empty or "district" not in chargers.columns:
        return candidates

    from .cache import build_spatial_index

    out = candidates.copy()
    missing = out["district"].fillna("").astype(str).str.len() == 0
    if not missing.any():
        return out
    index = build_spatial_index(chargers, name="district_fallback")
    if index.is_empty:
        return out

    from .cache import latlon_to_unit_xyz

    query_xyz = latlon_to_unit_xyz(out.loc[missing, ["latitude", "longitude"]].to_numpy(dtype=float))
    _, nearest_idx = index.tree.query(query_xyz, k=1)
    nearest = chargers.iloc[nearest_idx]
    out.loc[missing, "district"] = nearest["district"].map(display_name).to_numpy()
    out.loc[missing, "district_key"] = out.loc[missing, "district"].map(normalize_name)
    return out


def load_optional_points(dataset_key: str, patterns: list[str], reports: dict[str, Any]) -> pd.DataFrame:
    """Load a point dataset if a matching file exists under backend/data/raw."""

    path = find_first_file(patterns)
    if path is None:
        reports["missing_sources"].append(dataset_key)
        return pd.DataFrame(columns=["latitude", "longitude"])
    try:
        df = read_table(path)
        if isinstance(df, gpd.GeoDataFrame):
            df = geodataframe_to_points(df)
        cleaned, report = standardize_point_dataset(pd.DataFrame(df), dataset_key)
        reports["cleaning"][dataset_key] = report
        return cleaned
    except Exception as exc:
        logger.exception("Could not load %s from %s", dataset_key, path)
        reports["missing_sources"].append(dataset_key)
        reports["cleaning"][dataset_key] = {"error": str(exc), "path": str(path)}
        return pd.DataFrame(columns=["latitude", "longitude"])


def load_osm_points(layer_name: str, reports: dict[str, Any]) -> pd.DataFrame:
    """Load pre-extracted OpenStreetMap layers from raw files."""

    patterns_by_layer = {
        "roads": ["osm_roads.csv", "*osm*roads*.geojson", "*osm*roads*.gpkg", "*roads*.csv"],
        "highways": ["osm_highways.csv", "*osm*highways*.geojson", "*osm*highways*.gpkg", "*highways*.csv"],
        "fuel_stations": ["osm_fuel_stations.csv", "*osm*fuel*.geojson", "*fuel*.csv", "*petrol*.csv"],
        "railway_stations": ["osm_railway_stations.csv", "*osm*rail*.geojson", "*railway*.csv", "*rail*.csv"],
        "bus_stations": ["osm_bus_stations.csv", "*osm*bus*.geojson", "*bus*.csv"],
        "commercial_pois": ["osm_commercial_pois.csv", "*osm*commercial*.geojson", "*commercial*.csv", "*mall*.csv", "*poi*.csv"],
    }
    df = load_optional_points(f"osm_{layer_name}", patterns_by_layer[layer_name], reports)
    if df.empty:
        reports["notes"].append(
            f"OSM {layer_name} layer not found. Extract it from Geofabrik PBF into a CSV/GeoJSON/GPKG first."
        )
    return df


def load_city_centres(reports: dict[str, Any]) -> pd.DataFrame:
    """Load GHSL urban centres when available, otherwise derive city centres from BEE cities."""

    ghsl = load_optional_points("ghsl_urban_centres", ["*ghsl*.gpkg", "*ghsl*.geojson", "*urban*cent*.csv"], reports)
    if not ghsl.empty:
        return ghsl

    try:
        chargers, _ = load_existing_chargers()
        if "city_village" not in chargers.columns:
            reports["missing_sources"].append("city_centres")
            return pd.DataFrame(columns=["latitude", "longitude"])
        grouped = (
            chargers.dropna(subset=["city_village"])
            .groupby(["state", "district", "city_village"], dropna=True)[["latitude", "longitude"]]
            .mean()
            .reset_index()
        )
        reports["notes"].append("GHSL urban centres missing; city centres approximated from BEE city/village centroids.")
        return grouped
    except Exception as exc:
        reports["missing_sources"].append("city_centres")
        reports["cleaning"]["city_centres"] = {"error": str(exc)}
        return pd.DataFrame(columns=["latitude", "longitude"])


def load_ev_registrations(reports: dict[str, Any]) -> pd.DataFrame:
    """Load VAHAN EV registration exports if present."""

    path = find_first_file(["*vahan*.csv", "*registration*.csv", "*ev*register*.xlsx"])
    if path is None:
        reports["missing_sources"].append("vahan_ev_registrations")
        return pd.DataFrame()
    try:
        df = read_table(path)
        reports["cleaning"]["vahan_ev_registrations"] = {
            "dataset": "vahan_ev_registrations",
            "records": len(df),
            "missing_values": df.isna().sum().to_dict(),
        }
        return pd.DataFrame(df)
    except Exception as exc:
        logger.exception("Could not load VAHAN registration data from %s", path)
        reports["missing_sources"].append("vahan_ev_registrations")
        reports["cleaning"]["vahan_ev_registrations"] = {"error": str(exc), "path": str(path)}
        return pd.DataFrame()


def find_first_file(patterns: list[str]) -> Path | None:
    """Return the first raw file matching any of the supplied glob patterns."""

    for pattern in patterns:
        matches = sorted(RAW_DIR.glob(pattern))
        if matches:
            return matches[0]
    return None


def write_features(features: pd.DataFrame, output_path: Path) -> None:
    """Write the demand feature dataset as Parquet, with CSV fallback for local diagnostics."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        features.to_parquet(output_path, index=False)
        logger.info("Wrote demand feature parquet: %s", output_path)
    except Exception as exc:
        logger.exception("Could not write Parquet; writing CSV fallback")
        features.to_csv(DEMAND_FEATURES_CSV_FALLBACK, index=False)
        raise RuntimeError(
            f"Failed to write {output_path}. Install pyarrow or fastparquet. "
            f"CSV fallback written to {DEMAND_FEATURES_CSV_FALLBACK}."
        ) from exc


def write_reports(features: pd.DataFrame, datasets: SourceDatasets, reports: dict[str, Any]) -> None:
    """Generate dataset summary, data quality, and feature statistics reports."""

    dataset_summary = {
        "demand_features": {
            "records": len(features),
            "columns": list(features.columns),
            **coverage_by_region(features),
        },
        "sources": {
            "existing_chargers": _dataset_record_summary(datasets.existing_chargers),
            "airports": _dataset_record_summary(datasets.airports),
            "roads": _dataset_record_summary(datasets.roads),
            "highways": _dataset_record_summary(datasets.highways),
            "fuel_stations": _dataset_record_summary(datasets.fuel_stations),
            "railway_stations": _dataset_record_summary(datasets.railway_stations),
            "bus_stations": _dataset_record_summary(datasets.bus_stations),
            "commercial_pois": _dataset_record_summary(datasets.commercial_pois),
            "city_centres": _dataset_record_summary(datasets.city_centres),
            "ev_registrations": _dataset_record_summary(datasets.ev_registrations),
            "worldpop_raster": {"available": datasets.worldpop_raster is not None, "path": str(datasets.worldpop_raster or "")},
        },
    }

    quality_report = {
        **reports,
        "missing_values": features.isna().sum().to_dict(),
        "duplicate_candidate_coordinates": int(features.duplicated(subset=["latitude", "longitude"]).sum()),
        **coverage_by_region(features),
    }

    write_json(DATASET_SUMMARY_PATH, dataset_summary)
    write_json(DATA_QUALITY_REPORT_PATH, quality_report)
    write_json(FEATURE_STATISTICS_PATH, feature_statistics(features))


def _dataset_record_summary(df: pd.DataFrame) -> dict[str, object]:
    return {
        "records": int(len(df)),
        "columns": list(df.columns),
        "missing_values": df.isna().sum().to_dict() if not df.empty else {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EVCS preprocessing and demand feature generation.")
    parser.add_argument("--resolution", type=int, default=DEFAULT_GRID_RESOLUTION, help="Candidate grid resolution per axis.")
    parser.add_argument(
        "--normalization",
        choices=["minmax", "zscore", "robust"],
        default=DEFAULT_NORMALIZATION_METHOD,
        help="0-1 normalization method.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run_pipeline(PipelineConfig(grid_resolution=args.resolution, normalization_method=args.normalization))


if __name__ == "__main__":
    main()
