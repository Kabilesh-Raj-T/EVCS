"""Preprocess geometries into a cache file."""

import os
import pickle
import geopandas as gpd

from backend import config
from backend.spatial import attach_district_boundaries, build_state_regions, load_adm2_boundary, serialize_regions
from backend.utils import merge_geometries

def main():
    print(f"Loading primary boundaries from: {config.GEOJSON_PATH}")
    india_boundary = gpd.read_file(config.GEOJSON_PATH).to_crs(epsg=4326)
    
    print("Merging geometries...")
    polygon = merge_geometries(india_boundary)
    
    print("Building state regions...")
    state_regions = build_state_regions(india_boundary)
    
    print(f"Loading ADM2 boundaries from: {config.ADM2_GEOJSON_PATH}")
    adm2_boundary = load_adm2_boundary()
    
    print("Attaching district boundaries...")
    attach_district_boundaries(state_regions, adm2_boundary, india_boundary)
    
    print("Serializing region options...")
    REGION_OPTIONS = serialize_regions(state_regions)
    
    cache = {
        "india_boundary": india_boundary,
        "polygon": polygon,
        "state_regions": state_regions,
        "REGION_OPTIONS": REGION_OPTIONS
    }
    
    os.makedirs(os.path.dirname(config.PREPROCESSED_GEOMETRIES_PATH), exist_ok=True)
    with open(config.PREPROCESSED_GEOMETRIES_PATH, "wb") as f:
        pickle.dump(cache, f)
        
    print(f"Success! Cached geometries written to: {config.PREPROCESSED_GEOMETRIES_PATH}")

if __name__ == "__main__":
    main()
