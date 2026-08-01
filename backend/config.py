import os

EARTH_RADIUS_KM = 6371.0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "charging_stations.csv")
GEOJSON_PATH = os.path.join(BASE_DIR, "gadm41_IND_1.json")
ADM2_GEOJSON_PATH = os.path.join(BASE_DIR, "data", "raw", "geoboundaries_adm2.geojson")
DEMAND_FEATURES_PATH = os.path.join(BASE_DIR, "data", "processed", "demand_features.parquet")

INDIA_CENTER = [22.9734, 78.6569]
INDIA_DEFAULT_BOUNDS = {
    "lat_min": 6.7,
    "lat_max": 35.6,
    "lon_min": 68.1,
    "lon_max": 97.5,
}

STATE_DISPLAY_OVERRIDES = {
    "andamanandnicobar": "Andaman & Nicobar",
    "andamannicobar": "Andaman & Nicobar",
    "andhrapradesh": "Andhra Pradesh",
    "arunachalpradesh": "Arunachal Pradesh",
    "dadraandnagarhaveli": "Dadra and Nagar Haveli",
    "damananddiu": "Daman and Diu",
    "delhi": "Delhi",
    "nctofdelhi": "Delhi",
    "himachalpradesh": "Himachal Pradesh",
    "jammuandkashmir": "Jammu and Kashmir",
    "jammukashmir": "Jammu and Kashmir",
    "madhyapradesh": "Madhya Pradesh",
    "tamilnadu": "Tamil Nadu",
    "uttarpradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "uttrakhand": "Uttarakhand",
    "utofdnhanddd": "Dadra and Nagar Haveli and Daman and Diu",
    "westbengal": "West Bengal",
}
