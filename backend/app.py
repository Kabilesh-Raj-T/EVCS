"""Flask REST API for EVCS demand visualization and location optimization."""

import logging

import folium
from flask import Flask, jsonify, request
from flask_cors import CORS
from folium.plugins import HeatMap

import config, database, optimization, spatial, utils

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evcsapi")


def resolve_region(data: dict) -> dict:
    rtype = utils.normalize_name(data.get("region_type", ""))
    if rtype == "state" and str(data.get("district", "")).strip():
        rtype = "district"

    if rtype in {"allindia", "india", "country"}:
        b = config.INDIA_DEFAULT_BOUNDS
        return {"type": "all_india", "name": "All India", "bounds": b, "geometry": database.polygon,
                "coords": database.existing_coords, "map_center": config.INDIA_CENTER, "zoom": 5}

    if rtype == "state":
        name = data.get("region_name") or data.get("state")
        key = utils.normalize_name(name)
        state = database.state_regions.get(key)
        if not state: raise ValueError(f"Unknown state: {name}")
        geom = state["geometry"]
        coords = database.stations.loc[database.stations["_state_key"] == key, ["latitude_num", "longitude_num"]].to_numpy(dtype=float)
        if coords.size == 0:
            coords = spatial.station_coords_within_geometry(geom, database.stations)
        b = state["bounds"]
        return {"type": "state", "name": state["name"], "bounds": b, "geometry": geom, "coords": coords,
                "map_center": [(b["lat_min"]+b["lat_max"])/2, (b["lon_min"]+b["lon_max"])/2], "zoom": 7}

    if rtype == "district":
        s_name = data.get("region_name") or data.get("state")
        d_name = data.get("district")
        s_key, d_key = utils.normalize_name(s_name), utils.normalize_name(d_name)
        state = database.state_regions.get(s_key)
        if not state: raise ValueError(f"Unknown state: {s_name}")
        district = state["districts"].get(d_key)
        if not district: raise ValueError(f"Unknown district for {state['name']}: {d_name}")
        geom = district["geometry"]
        d_data = district.get("data")
        coords = (d_data[["latitude_num", "longitude_num"]].to_numpy(dtype=float)
                  if d_data is not None and not d_data.empty
                  else spatial.station_coords_within_geometry(geom, database.stations))
        b = district["bounds"]
        return {"type": "district", "name": f"{district['name']}, {state['name']}", "bounds": b, "geometry": geom,
                "coords": coords, "map_center": [(b["lat_min"]+b["lat_max"])/2, (b["lon_min"]+b["lon_max"])/2], "zoom": 10}

    raise ValueError(f"Unsupported region_type: {data.get('region_type')}")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "data_loaded": database.data_loaded})


@app.route("/")
def base():
    return jsonify({"status": "ok", "endpoints": ["/health", "/regions", "/optimize"], "data_loaded": database.data_loaded})


@app.route("/regions")
def regions():
    try:
        database.load_data()
        return jsonify(database.REGION_OPTIONS)
    except Exception as e:
        logger.exception("Error serving /regions")
        return jsonify({"error": str(e)}), 500


@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        database.load_data()
        data = request.get_json(force=True)
        k = int(data.get("k", 5))
        resolution = int(data.get("resolution", 100))
        optimizer = utils.normalize_name(data.get("optimizer", "greedy"))

        if optimizer not in {"greedy", "kcenter", "weighted", "demand", "demandweighted"}:
            return jsonify({"error": f"Unsupported optimizer: {data.get('optimizer')}"}), 400

        region = resolve_region(data)
        b = region["bounds"]
        if resolution <= 0 or resolution > 500 or k < 0 or k > 1000 or b["lat_min"] >= b["lat_max"] or b["lon_min"] >= b["lon_max"]:
            return jsonify({"error": "Invalid request parameters"}), 400

        use_weighted = optimizer in {"weighted", "demand", "demandweighted"}
        points_data = []
        if k > 0:
            weight = 0.75 if use_weighted else 0.0
            points_data = optimization.optimize_locations(region, k, resolution, demand_weight=weight)
            if not points_data:
                return jsonify({"error": "No candidate points found"}), 400

        m = folium.Map(location=region["map_center"], zoom_start=region["zoom"])
        m.fit_bounds([[b["lat_min"], b["lon_min"]], [b["lat_max"], b["lon_max"]]])
        if len(region["coords"]) > 0:
            n = len(region["coords"])
            r, bl, op = (6, 5, 0.15) if n > 20000 else ((8, 10, 0.2) if n > 5000 else (12, 18, 0.3))
            HeatMap(region["coords"].tolist(), radius=r, blur=bl, min_opacity=op,
                    gradient={0.05: "cyan", 0.15: "blue", 0.3: "purple", 0.5: "magenta", 0.8: "red"}).add_to(m)

        for i, p in enumerate(points_data, 1):
            p["id"] = i
            lat, lon = p["lat"], p["lon"]
            popup = f"Suggested #{i}: ({lat:.6f}, {lon:.6f})<br>Demand: {p['demand_score']:.3f}  Selection: {p['selection_score']:.3f}"
            folium.Marker([lat, lon], popup=popup, tooltip=f"New EV #{i}",
                          icon=folium.Icon(color="red", icon="bolt", prefix="fa")).add_to(m)

        map_html = m.get_root().render()

        return jsonify({"map_html": map_html, "points": points_data,
                        "region": {"type": region["type"], "name": region["name"], "bounds": b},
                        "optimizer": "weighted" if use_weighted else "greedy"})

    except Exception as e:
        logger.exception("Error in /optimize")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
