from flask import Flask, render_template
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from geopy.distance import geodesic
import folium
from folium.plugins import HeatMap

app = Flask(__name__)

@app.route('/')
def index():
    # Load and clean dataset
    filename = 'ev-charging-stations-india.csv'
    df = pd.read_csv(filename)
    df = df.dropna(subset=["lattitude", "longitude"])
    # The provided script has a bug here, it should be latitude, not lattitude
    # I will assume the original script intended to use the correct column name.
    # However, I must first check the CSV header.
    # I will correct this in the next step after verifying the CSV.
    # For now, I will stick to the user's script.
    df["lattitude"] = df["lattitude"].astype(str).str.replace(",", "").astype(float)
    df["longitude"] = df["longitude"].astype(str).str.replace(",", "").astype(float)

    # Filter Tamil Nadu stations
    df["state"] = df["state"].astype(str).str.strip().str.lower()
    tn_df = df[df["state"] == "tamil nadu"].copy()

    # KDTree for existing locations
    existing_coords = tn_df[["lattitude", "longitude"]].values
    existing_tree = KDTree(existing_coords)

    # Very tight Tamil Nadu land-only bounding box
    LAT_MIN, LAT_MAX = 9.2, 12.9
    LON_MIN, LON_MAX = 76.9, 79.9

    # Ultra-strict land point filter (no coastlines, no borders)
    def is_valid_land_point(lat, lon):
        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            return False
        if lat < 9.4 and lon < 77.5:
            return False  # Deep south coastal
        if lat < 10.2 and lon > 79.5:
            return False  # Southeast coast
        if lat > 12.7 and lon > 79.7:
            return False  # Coastal spill near Pondy
        if lat > 12.6 and lon < 77.1:
            return False  # Western hill border
        return True

    # Generate land-locked candidate points
    def generate_candidate_points(resolution=70):
        lat_range = np.linspace(LAT_MIN, LAT_MAX, resolution)
        lon_range = np.linspace(LON_MIN, LON_MAX, resolution)
        return [(lat, lon) for lat in lat_range for lon in lon_range if is_valid_land_point(lat, lon)]

    # Greedy max-distance placement algorithm
    def find_optimal_locations(num_new_stations, existing_tree, existing_coords):
        candidates = generate_candidate_points()
        selected = []

        for i in range(num_new_stations):
            best_point = None
            best_dist = -1

            for point in candidates:
                if point in selected:
                    continue  # Skip duplicates

                dist_existing, idx = existing_tree.query(point)
                geo_dist = geodesic(point, existing_coords[idx]).km

                if selected:
                    geo_dist = min(geo_dist, min(geodesic(point, sel).km for sel in selected))

                if geo_dist > best_dist:
                    best_dist = geo_dist
                    best_point = point

            if best_point:
                selected.append(best_point)
                existing_coords = np.vstack([existing_coords, best_point])
                existing_tree = KDTree(existing_coords)
                print(f"✅ Placing station #{len(selected)} at {best_point}, min dist: {best_dist:.2f} km")
            else:
                print("⚠️ No valid point found on this iteration.")

        return selected

    # Set number of new stations to place
    num_new = 5

    # Run location optimizer
    optimal_points = find_optimal_locations(num_new, existing_tree, existing_coords)

    # Create map
    tn_map = folium.Map(location=[10.75, 78.0], zoom_start=7)

    # Heatmap of current stations
    HeatMap(tn_df[["lattitude", "longitude"]].values.tolist(), radius=8, blur=12).add_to(tn_map)

    # Add new suggested station markers
    for i, point in enumerate(optimal_points):
        folium.Marker(
            location=point,
            popup=f"Suggested Station #{i+1}: {point}",
            tooltip=f"New EV #{i+1}",
            icon=folium.Icon(color="red", icon="bolt", prefix="fa")
        ).add_to(tn_map)

    return render_template('index.html', map_html=tn_map._repr_html_())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
