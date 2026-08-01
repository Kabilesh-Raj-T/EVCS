import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import folium
import tempfile
import os

import config
import utils
import database
import spatial
import optimization
import visualization

# ----------------------------
# App + logging
# ----------------------------
app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evcsapi")

def region_center(bounds):
    return [
        (bounds["lat_min"] + bounds["lat_max"]) / 2.0,
        (bounds["lon_min"] + bounds["lon_max"]) / 2.0,
    ]

def region_zoom(region_type):
    if region_type == "district":
        return 10
    if region_type == "state":
        return 7
    return 5

def bounds_from_payload(data):
    return {
        "lat_min": float(data.get("lat_min", config.INDIA_DEFAULT_BOUNDS["lat_min"])),
        "lat_max": float(data.get("lat_max", config.INDIA_DEFAULT_BOUNDS["lat_max"])),
        "lon_min": float(data.get("lon_min", config.INDIA_DEFAULT_BOUNDS["lon_min"])),
        "lon_max": float(data.get("lon_max", config.INDIA_DEFAULT_BOUNDS["lon_max"])),
    }

def resolve_region(data):
    region_type = utils.normalize_name(data.get("region_type", ""))
    has_district = bool(utils.payload_text(data.get("district")))
    if region_type == "state" and has_district:
        region_type = "district"

    if not region_type:
        bounds = bounds_from_payload(data)
        bbox_polygon = spatial.make_bbox_polygon(bounds)
        return {
            "type": "custom",
            "name": "Custom bounds",
            "bounds": bounds,
            "geometry": database.polygon.intersection(bbox_polygon),
            "coords": database.existing_coords,
            "map_center": region_center(bounds),
            "zoom": 5,
        }

    if region_type in {"allindia", "india", "country"}:
        return {
            "type": "all_india",
            "name": "All India",
            "bounds": config.INDIA_DEFAULT_BOUNDS,
            "geometry": database.polygon,
            "coords": database.existing_coords,
            "map_center": config.INDIA_CENTER,
            "zoom": 5,
        }

    if region_type == "state":
        state_name = data.get("region_name") or data.get("state")
        state_key = utils.normalize_name(state_name)
        state = database.state_regions.get(state_key)
        if not state:
            raise ValueError(f"Unknown state: {state_name}")

        geometry = state["geometry"] or database.polygon.intersection(spatial.make_bbox_polygon(state["bounds"]))
        state_mask = database.stations["_state_key"] == state_key
        coords = database.stations.loc[state_mask, [database.station_lat_col, database.station_lon_col]].to_numpy(dtype=float)
        if coords.size == 0:
            coords = spatial.station_coords_within_geometry(
                geometry, database.stations, database.station_lat_col, database.station_lon_col
            )
        return {
            "type": "state",
            "name": state["name"],
            "bounds": state["bounds"],
            "geometry": geometry,
            "coords": coords,
            "map_center": region_center(state["bounds"]),
            "zoom": region_zoom("state"),
        }

    if region_type == "district":
        state_name = data.get("region_name") or data.get("state")
        district_name = data.get("district")
        state_key = utils.normalize_name(state_name)
        district_key = utils.normalize_name(district_name)
        state = database.state_regions.get(state_key)
        if not state:
            raise ValueError(f"Unknown state: {state_name}")
        district = state["districts"].get(district_key)
        if not district:
            raise ValueError(f"Unknown district for {state['name']}: {district_name}")

        geometry_source = state["geometry"] or database.polygon
        if district.get("geometry") is not None:
            geometry = district["geometry"]
        else:
            geometry = geometry_source.intersection(spatial.make_bbox_polygon(district["bounds"]))

        district_data = district.get("data")
        if district_data is not None and not district_data.empty:
            coords = district_data[[database.station_lat_col, database.station_lon_col]].to_numpy(dtype=float)
        else:
            coords = spatial.station_coords_within_geometry(
                geometry, database.stations, database.station_lat_col, database.station_lon_col
            )
        return {
            "type": "district",
            "name": f"{district['name']}, {state['name']}",
            "bounds": district["bounds"],
            "geometry": geometry,
            "coords": coords,
            "map_center": region_center(district["bounds"]),
            "zoom": region_zoom("district"),
        }

    raise ValueError(f"Unsupported region_type: {data.get('region_type')}")

# ----------------------------
# Routes
# ----------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "EVCS backend",
        "data_loaded": database.data_loaded,
    })

@app.route("/", methods=["GET"])
def base():
    return jsonify({
        "status": "ok",
        "service": "EVCS backend",
        "endpoints": ["/health", "/regions", "/optimize"],
        "data_loaded": database.data_loaded,
    })

@app.route("/regions", methods=["GET"])
def regions():
    try:
        database.load_data()
        return jsonify(database.REGION_OPTIONS)
    except Exception as e:
        logger.exception("Error serving regions")
        return jsonify({"error": str(e)}), 500

@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        database.load_data()
        data = request.get_json(force=True)
        k = int(data.get("k", 5))
        resolution = int(data.get("resolution", 100))
        optimizer = utils.normalize_name(data.get("optimizer", "greedy"))
        supported_optimizers = {"greedy", "kcenter", "coverage", "weighted", "demand", "demandweighted"}
        if optimizer not in supported_optimizers:
            return jsonify({"error": f"Unsupported optimizer: {data.get('optimizer')}"}), 400
        region = resolve_region(data)
        lat_min = region["bounds"]["lat_min"]
        lat_max = region["bounds"]["lat_max"]
        lon_min = region["bounds"]["lon_min"]
        lon_max = region["bounds"]["lon_max"]

        # Sanity checks
        if resolution <= 0 or resolution > 500:
            return jsonify({"error": "resolution out of range"}), 400
        if k < 0 or k > 1000:
            return jsonify({"error": "k out of range"}), 400
        if lat_min >= lat_max or lon_min >= lon_max:
            return jsonify({"error": "invalid geographic bounds"}), 400

        optimal = []
        weighted_points = []
        if optimizer in {"weighted", "demand", "demandweighted"} and k > 0:
            weighted_points = optimization.weighted_demand_optimizer(region, k, resolution)
            optimal = [(point["lat"], point["lon"]) for point in weighted_points]
        elif k > 0:
            candidates = utils.generate_candidate_points(
                lat_min,
                lat_max,
                lon_min,
                lon_max,
                resolution,
                region["geometry"],
            )
            if candidates.size == 0:
                return jsonify({"error": "No candidate points found"}), 400
            optimal = optimization.k_center_greedy(region["coords"], candidates, k)

        # Make Folium map
        m = folium.Map(location=region["map_center"], zoom_start=region["zoom"])
        visualization.add_region_boundary(m, region, database.india_boundary)
        m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])

        visualization.add_station_heatmap(m, region["coords"])

        weighted_by_coord = {
            (round(point["lat"], 10), round(point["lon"], 10)): point
            for point in weighted_points
        }
        for i, (lat, lon) in enumerate(optimal, start=1):
            weighted_meta = weighted_by_coord.get((round(lat, 10), round(lon, 10)), {})
            popup = f"Suggested #{i}: ({lat:.6f}, {lon:.6f})"
            if "demand_score" in weighted_meta and weighted_meta["demand_score"] is not None:
                popup += f"<br>Demand score: {weighted_meta['demand_score']:.3f}"
                popup += f"<br>Selection score: {weighted_meta['selection_score']:.3f}"
            folium.Marker(
                location=[lat, lon],
                popup=popup,
                tooltip=f"New EV #{i}",
                icon=folium.Icon(color="red", icon="bolt", prefix="fa"),
            ).add_to(m)

        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        m.save(tmpfile.name)
        tmpfile.close()
        
        # Read the file content
        with open(tmpfile.name, "r", encoding="utf-8") as f:
            map_content = f.read()

        # Prepare points list
        points_data = []
        for i, (lat, lon) in enumerate(optimal, start=1):
            point_payload = {"id": i, "lat": lat, "lon": lon}
            weighted_meta = weighted_by_coord.get((round(lat, 10), round(lon, 10)))
            if weighted_meta:
                point_payload.update({
                    "demand_score": weighted_meta.get("demand_score"),
                    "selection_score": weighted_meta.get("selection_score"),
                    "state": weighted_meta.get("state", ""),
                    "district": weighted_meta.get("district", ""),
                })
            points_data.append(point_payload)

        logger.info("Generated optimization map: %s", tmpfile.name)
        
        # Return JSON with map HTML and points
        return jsonify({
            "map_html": map_content,
            "points": points_data,
            "region": {
                "type": region["type"],
                "name": region["name"],
                "bounds": region["bounds"],
            },
            "optimizer": "weighted" if optimizer in {"weighted", "demand", "demandweighted"} else "greedy",
        })

    except Exception as e:
        logger.exception("Error in /optimize")
        return jsonify({"error": str(e)}), 500

# Note: Do not call app.run() here for production. Gunicorn will serve the app.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
