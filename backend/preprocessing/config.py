"""Configuration constants for the EVCS data preprocessing layer."""

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
REPORTS_DIR = PROJECT_ROOT / "reports"

CURRENT_BEE_CSV = BACKEND_DIR / "charging_stations.csv"
CURRENT_ADM1_GEOJSON = BACKEND_DIR / "gadm41_IND_1.json"

DEMAND_FEATURES_PATH = PROCESSED_DIR / "demand_features.parquet"

SOURCE_MANIFEST_PATH = REPORTS_DIR / "source_manifest.json"
DATASET_SUMMARY_PATH = REPORTS_DIR / "dataset_summary.json"
DATA_QUALITY_REPORT_PATH = REPORTS_DIR / "data_quality_report.json"
FEATURE_STATISTICS_PATH = REPORTS_DIR / "feature_statistics.json"

INDIA_BOUNDS = {"lat_min": 6.7, "lat_max": 35.6, "lon_min": 68.1, "lon_max": 97.5}
DEFAULT_GRID_RESOLUTION = 200
DEFAULT_NORMALIZATION_METHOD = "minmax"
COMMERCIAL_DENSITY_RADIUS_KM = 5.0

DATASET_SOURCES = {
    "bee_ev_charging_stations": {"name": "BEE EV Stations", "source": "BEE", "url": "https://beeindia.gov.in", "required": True},
    "geoboundaries_adm1": {"name": "geoBoundaries ADM1", "source": "geoBoundaries", "url": "https://www.geoboundaries.org", "required": True},
    "geoboundaries_adm2": {"name": "geoBoundaries ADM2", "source": "geoBoundaries", "url": "https://www.geoboundaries.org", "required": True},
    "worldpop_india_population_density": {"name": "WorldPop Population", "source": "WorldPop", "url": "https://data.worldpop.org", "required": True},
    "overture_commercial_pois": {"name": "Overture Maps Commercial POIs", "source": "Overture Maps", "url": "https://overturemaps.org", "required": True},
    "ourairports_india": {"name": "OurAirports India", "source": "OurAirports", "url": "https://ourairports.com", "required": False},
}
