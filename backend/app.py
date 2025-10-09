from flask import Flask, request, jsonify
from flask_cors import CORS
import folium
from folium.plugins import HeatMap
import pandas as pd
import json
import numpy as np
from sklearn.cluster import KMeans

app = Flask(__name__)
CORS(app)

@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.json
        k = data.get('k', 5)
        resolution = data.get('resolution', 100)
        lat_min = data.get('lat_min', 8.0)
        lat_max = data.get('lat_max', 13.5)
        lon_min = data.get('lon_min', 76.0)
        lon_max = data.get('lon_max', 80.5)
        
        stations_df = pd.read_csv('backend/stations.csv')
        
        filtered_stations = stations_df[
            (stations_df['latitude'] >= lat_min) &
            (stations_df['latitude'] <= lat_max) &
            (stations_df['longitude'] >= lon_min) &
            (stations_df['longitude'] <= lon_max)
        ]
        
        center_lat = (lat_min + lat_max) / 2
        center_lon = (lon_min + lon_max) / 2
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=7,
            tiles='OpenStreetMap'
        )
        
        try:
            with open('backend/tamilnadu.geojson', 'r') as f:
                tn_geojson = json.load(f)
            folium.GeoJson(
                tn_geojson,
                name='Tamil Nadu Boundary',
                style_function=lambda x: {
                    'fillColor': 'transparent',
                    'color': 'blue',
                    'weight': 2
                }
            ).add_to(m)
        except:
            pass
        
        if len(filtered_stations) > 0:
            heat_data = [[row['latitude'], row['longitude']] 
                        for _, row in filtered_stations.iterrows()]
            HeatMap(heat_data, radius=15, blur=25, max_zoom=13).add_to(m)
            
            if len(filtered_stations) >= k:
                coords = filtered_stations[['latitude', 'longitude']].values
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans.fit(coords)
                new_stations = kmeans.cluster_centers_
            else:
                lat_grid = np.linspace(lat_min, lat_max, resolution)
                lon_grid = np.linspace(lon_min, lon_max, resolution)
                grid_points = []
                for lat in lat_grid:
                    for lon in lon_grid:
                        min_dist = min([
                            np.sqrt((lat - s_lat)**2 + (lon - s_lon)**2)
                            for s_lat, s_lon in zip(
                                filtered_stations['latitude'],
                                filtered_stations['longitude']
                            )
                        ]) if len(filtered_stations) > 0 else float('inf')
                        grid_points.append((lat, lon, min_dist))
                
                grid_points.sort(key=lambda x: x[2], reverse=True)
                new_stations = np.array([[p[0], p[1]] for p in grid_points[:k]])
            
            for lat, lon in new_stations:
                folium.Marker(
                    location=[lat, lon],
                    popup='Suggested New Station',
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(m)
        else:
            lat_grid = np.linspace(lat_min, lat_max, k)
            lon_grid = np.linspace(lon_min, lon_max, k)
            for i in range(min(k, len(lat_grid))):
                folium.Marker(
                    location=[lat_grid[i], center_lon],
                    popup='Suggested New Station',
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(m)
        
        html_string = m._repr_html_()
        
        return html_string, 200, {'Content-Type': 'text/html'}
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
