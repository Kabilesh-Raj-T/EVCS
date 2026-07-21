"""Configuration constants for the EVCS data preprocessing layer."""

from __future__ import annotations

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
DEMAND_FEATURES_CSV_FALLBACK = PROCESSED_DIR / "demand_features.csv"

SOURCE_MANIFEST_PATH = REPORTS_DIR / "source_manifest.json"
DATASET_SUMMARY_PATH = REPORTS_DIR / "dataset_summary.json"
DATA_QUALITY_REPORT_PATH = REPORTS_DIR / "data_quality_report.json"
FEATURE_STATISTICS_PATH = REPORTS_DIR / "feature_statistics.json"

INDIA_BOUNDS = {
    "lat_min": 6.7,
    "lat_max": 35.6,
    "lon_min": 68.1,
    "lon_max": 97.5,
}

DEFAULT_GRID_RESOLUTION = 120
DEFAULT_NORMALIZATION_METHOD = "minmax"
COMMERCIAL_DENSITY_RADIUS_KM = 5.0

DATASET_SOURCES = {
    "bee_ev_charging_stations": {
        "name": "BEE EV Public Charging Stations",
        "source": "Bureau of Energy Efficiency / Ministry of Power",
        "url": "https://beeindia.gov.in/WriteReadData/RTF1984/EV_PCS_Data_29277.pdf",
        "license": "Government publication; verify reuse terms before commercial redistribution",
        "coverage": "India",
        "format": "PDF/CSV extracted",
        "required": True,
        "large": False,
    },
    "geoboundaries_adm1": {
        "name": "geoBoundaries India ADM1",
        "source": "geoBoundaries",
        "url": "https://www.geoboundaries.org/countryDownloads.html",
        "license": "CC BY 4.0",
        "coverage": "India states/UTs",
        "format": "GeoJSON",
        "required": True,
        "large": False,
    },
    "geoboundaries_adm2": {
        "name": "geoBoundaries India ADM2",
        "source": "geoBoundaries",
        "url": "https://www.geoboundaries.org/countryDownloads.html",
        "license": "CC BY 4.0",
        "coverage": "India districts",
        "format": "GeoJSON",
        "required": True,
        "large": False,
    },
    "worldpop_india_population_density": {
        "name": "WorldPop India 1km Population Density",
        "source": "WorldPop",
        "url": "https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km/2020/IND/ind_pd_2020_1km.tif",
        "license": "CC BY 4.0",
        "coverage": "India",
        "format": "GeoTIFF",
        "required": True,
        "large": False,
    },
    "vahan_ev_registrations": {
        "name": "VAHAN EV Registrations",
        "source": "VAHAN / data.gov.in exports",
        "url": "https://vahan.parivahan.gov.in/vahan4dashboard/",
        "license": "Government Open Data License where exported from data.gov.in",
        "coverage": "India; state/RTO depending on export",
        "format": "CSV/XLSX",
        "required": False,
        "large": False,
    },
    "geofabrik_osm_india": {
        "name": "OpenStreetMap India",
        "source": "Geofabrik",
        "url": "https://download.geofabrik.de/asia/india-latest.osm.pbf",
        "license": "ODbL 1.0",
        "coverage": "India",
        "format": "PBF",
        "required": True,
        "large": True,
    },
    "ourairports_india": {
        "name": "OurAirports India Airports",
        "source": "OurAirports",
        "url": "https://ourairports.com/countries/IN/airports.csv",
        "license": "Public domain",
        "coverage": "India",
        "format": "CSV",
        "required": True,
        "large": False,
    },
    "ghsl_urban_centres": {
        "name": "GHSL Urban Centre Database",
        "source": "European Commission GHSL",
        "url": "https://human-settlement.emergency.copernicus.eu/ghs_ucdb_2024.php",
        "license": "Copernicus/European Commission open terms; verify attribution",
        "coverage": "Global including India",
        "format": "GPKG/CSV",
        "required": True,
        "large": True,
    },
    "tourism_placeholder": {
        "name": "Tourism datasets placeholder",
        "source": "Ministry of Tourism / ASI",
        "url": "https://data.tourism.gov.in/tourismdata",
        "license": "Varies",
        "coverage": "India",
        "format": "CSV/PDF",
        "required": False,
        "large": False,
    },
    "cea_utilization_placeholder": {
        "name": "CEA charger utilization reports placeholder",
        "source": "Central Electricity Authority",
        "url": "https://cea.nic.in/electric-vehicle-charging-reports/?lang=en",
        "license": "Government publication; verify reuse terms",
        "coverage": "India",
        "format": "PDF/XLSX",
        "required": False,
        "large": False,
    },
    "bhuvan_land_use_placeholder": {
        "name": "Bhuvan land-use placeholder",
        "source": "ISRO Bhuvan / NRSC",
        "url": "https://bhuvan.nrsc.gov.in/",
        "license": "Varies; verify before commercial use",
        "coverage": "India",
        "format": "Raster/vector",
        "required": False,
        "large": True,
    },
    "official_highways_placeholder": {
        "name": "Official highway datasets placeholder",
        "source": "MoRTH / NHAI",
        "url": "https://morth.nic.in/",
        "license": "Varies",
        "coverage": "India",
        "format": "PDF/GIS services",
        "required": False,
        "large": False,
    },
}
