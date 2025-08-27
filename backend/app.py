import os
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from geopy.distance import geodesic
import folium
from folium.plugins import HeatMap
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def find_optimal_locations_optimized(num_new_stations, existing_tree, existing_coords, lat_min, lat_max, lon_min, lon_max):

    def is_valid_land_point(lat, lon):
        if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
            return False
        if lat < 9.4 and lon < 77.5:
            return False
        if lat < 10.2 and lon > 79.5:
            return False
        if lat > 12.7 and lon > 79.7:
            return False
        if lat > 12.6 and lon < 77.1:
            return False
        return True

    def generate_candidate_points(resolution=70):
        lat_range = np.linspace(lat_min, lat_max, resolution)
        lon_range = np.linspace(lon_min, lon_max, resolution)
        return [(lat, lon) for lat in lat_range for lon in lon_range if is_valid_land_point(lat, lon)]

    candidate_points = np.array(generate_candidate_points())
    if len(candidate_points) == 0:
        print("⚠️ No valid candidate points were generated. Check your filters.")
        return []

    print(f"✅ Generated {len(candidate_points)} valid candidate land points.")

    _, indices = existing_tree.query(candidate_points)

    min_distances = np.array([
        geodesic(candidate_points[i], existing_coords[indices[i]]).km
        for i in range(len(candidate_points))
    ])

    selected_points = []

    for i in range(num_new_stations):
        best_point_idx = np.argmax(min_distances)
        new_station_point = tuple(candidate_points[best_point_idx])
        best_dist = min_distances[best_point_idx]

        if best_dist < 0:
             print("⚠️ No more valid points found. Stopping early.")
             break

        selected_points.append(new_station_point)
        print(f"✅ Placing station #{len(selected_points)} at {new_station_point}, min dist: {best_dist:.2f} km")

        min_distances[best_point_idx] = -1

        distances_to_new = np.array([
            geodesic(candidate, new_station_point).km for candidate in candidate_points
        ])

        min_distances = np.minimum(min_distances, distances_to_new)

    return selected_points

@app.route('/api/process', methods=['POST'])
def process_data():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        lat_min = float(request.form.get('lat_min', 9.2))
        lat_max = float(request.form.get('lat_max', 12.9))
        lon_min = float(request.form.get('lon_min', 76.9))
        lon_max = float(request.form.get('lon_max', 79.9))
        num_new = int(request.form.get('num_new', 5))

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        df = pd.read_csv(filepath)
        df = df.dropna(subset=["lattitude", "longitude"])
        df["lattitude"] = df["lattitude"].astype(str).str.replace(",", "").astype(float)
        df["longitude"] = df["longitude"].astype(str).str.replace(",", "").astype(float)

        df["state"] = df["state"].astype(str).str.strip().str.lower()
        tn_df = df[df["state"] == "tamil nadu"].copy()

        existing_coords = tn_df[["lattitude", "longitude"]].values
        if len(existing_coords) == 0:
            return jsonify({'error': 'No existing stations found for Tamil Nadu in the provided file.'}), 400

        existing_tree = KDTree(existing_coords)

        optimal_points = find_optimal_locations_optimized(num_new, existing_tree, existing_coords, lat_min, lat_max, lon_min, lon_max)

        tn_map = folium.Map(location=[(lat_min + lat_max) / 2, (lon_min + lon_max) / 2], zoom_start=7)
        HeatMap(tn_df[["lattitude", "longitude"]].values.tolist(), radius=8, blur=12).add_to(tn_map)

        for i, point in enumerate(optimal_points):
            folium.Marker(
                location=point,
                popup=f"Suggested Station #{i+1}: {point}",
                tooltip=f"New EV #{i+1}",
                icon=folium.Icon(color="red", icon="bolt", prefix="fa")
            ).add_to(tn_map)

        map_html = tn_map._repr_html_()
        return jsonify({'map_html': map_html})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
