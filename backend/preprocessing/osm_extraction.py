"""Extract demand-relevant OpenStreetMap layers from a Geofabrik PBF file."""

from __future__ import annotations

import argparse
import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, MultiLineString

from .cache import ensure_directories
from .config import RAW_DIR


logger = logging.getLogger(__name__)

GEOFABRIK_INDIA_PBF_URL = "https://download.geofabrik.de/asia/india-latest.osm.pbf"
DEFAULT_PBF_PATH = RAW_DIR / "geofabrik_india-latest.osm.pbf"

ROAD_HIGHWAY_VALUES = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "motorway_link",
    "trunk_link",
    "primary_link",
    "secondary_link",
    "tertiary_link",
    "unclassified",
}

NATIONAL_HIGHWAY_VALUES = {
    "motorway",
    "trunk",
    "primary",
    "motorway_link",
    "trunk_link",
    "primary_link",
}


@dataclass(frozen=True)
class OsmLayerPaths:
    """Output paths for extracted OSM layer CSV files."""

    roads: Path = RAW_DIR / "osm_roads.csv"
    highways: Path = RAW_DIR / "osm_highways.csv"
    fuel_stations: Path = RAW_DIR / "osm_fuel_stations.csv"
    malls: Path = RAW_DIR / "osm_malls.csv"
    railway_stations: Path = RAW_DIR / "osm_railway_stations.csv"
    bus_stations: Path = RAW_DIR / "osm_bus_stations.csv"
    commercial_pois: Path = RAW_DIR / "osm_commercial_pois.csv"


def layer_paths(prefix: str = "osm", output_dir: Path = RAW_DIR) -> OsmLayerPaths:
    """Create OSM layer paths for a prefix such as osm_southern_zone."""

    return OsmLayerPaths(
        roads=output_dir / f"{prefix}_roads.csv",
        highways=output_dir / f"{prefix}_highways.csv",
        fuel_stations=output_dir / f"{prefix}_fuel_stations.csv",
        malls=output_dir / f"{prefix}_malls.csv",
        railway_stations=output_dir / f"{prefix}_railway_stations.csv",
        bus_stations=output_dir / f"{prefix}_bus_stations.csv",
        commercial_pois=output_dir / f"{prefix}_commercial_pois.csv",
    )


def find_osm_pbf() -> Path | None:
    """Return the first local OSM PBF file in raw data."""

    matches = sorted(RAW_DIR.glob("*.osm.pbf")) + sorted(RAW_DIR.glob("*.pbf"))
    return matches[0] if matches else None


def ensure_osm_pbf(download: bool = False, pbf_path: Path | None = None) -> Path:
    """Resolve or optionally download the India Geofabrik PBF."""

    ensure_directories()
    target = pbf_path or find_osm_pbf() or DEFAULT_PBF_PATH
    if target.exists() and is_complete_pbf(target):
        return target

    if target.exists() and not download:
        raise FileNotFoundError(
            f"OSM PBF exists but appears incomplete: {target} "
            f"({target.stat().st_size:,} bytes). Run with --download-osm to resume it."
        )

    if not download:
        raise FileNotFoundError(
            f"No OSM PBF found in {RAW_DIR}. Download {GEOFABRIK_INDIA_PBF_URL} "
            "or run with --download-osm."
        )

    logger.info("Downloading Geofabrik India PBF. This is a large file: %s", GEOFABRIK_INDIA_PBF_URL)
    resume_download(GEOFABRIK_INDIA_PBF_URL, target)
    return target


def remote_content_length(url: str) -> int | None:
    """Return remote content length when the server provides it."""

    try:
        response = requests.head(url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        length = response.headers.get("Content-Length")
        return int(length) if length else None
    except Exception:
        logger.warning("Could not determine remote size for %s", url)
        return None


def is_complete_pbf(path: Path) -> bool:
    """Check whether a local PBF looks complete enough to parse."""

    if not path.exists() or path.stat().st_size == 0:
        return False
    if path.name == DEFAULT_PBF_PATH.name:
        expected = remote_content_length(GEOFABRIK_INDIA_PBF_URL)
        if expected is not None:
            return path.stat().st_size >= expected
    return True


def resume_download(url: str, target: Path, chunk_size: int = 1024 * 1024) -> Path:
    """Download a large file with HTTP Range resume support."""

    target.parent.mkdir(parents=True, exist_ok=True)
    existing_size = target.stat().st_size if target.exists() else 0
    headers = {"Range": f"bytes={existing_size}-"} if existing_size else {}
    mode = "ab" if existing_size else "wb"
    logger.info("Starting download at byte offset %d", existing_size)

    with requests.get(url, stream=True, timeout=120, headers=headers) as response:
        if existing_size and response.status_code == 200:
            logger.warning("Server ignored Range header; restarting download from zero")
            mode = "wb"
        response.raise_for_status()
        with target.open(mode) as fh:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    fh.write(chunk)

    if not is_complete_pbf(target):
        raise RuntimeError(f"Download did not complete: {target}")
    return target


def read_osm_layer(pbf_path: Path, layer: str, columns: list[str] | None = None) -> gpd.GeoDataFrame:
    """Read one GDAL OSM layer from a PBF file using pyogrio."""

    import pyogrio

    logger.info("Reading OSM layer %s from %s", layer, pbf_path)
    gdf = pyogrio.read_dataframe(pbf_path, layer=layer, columns=columns)
    if gdf.empty:
        return gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs="EPSG:4326")
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    return gdf.to_crs(epsg=4326)


def tag_series(gdf: gpd.GeoDataFrame, key: str) -> pd.Series:
    """Return an OSM tag as a lower-case string series, including other_tags fallback."""

    values = pd.Series("", index=gdf.index, dtype=str)
    if key in gdf.columns:
        values = gdf[key].fillna("").astype(str)

    if "other_tags" in gdf.columns:
        pattern = f'"{key}"=>'
        other = gdf["other_tags"].fillna("").astype(str)
        extracted = other.str.extract(f'"{key}"=>"?([^",]+)"?', expand=False).fillna("")
        values = values.mask(values.eq("") & other.str.contains(pattern, regex=False), extracted)

    return values.str.lower().str.strip()


def contains_any(series: pd.Series, values: Iterable[str]) -> pd.Series:
    """Return a boolean mask where a string series equals one of the supplied values."""

    allowed = {value.lower() for value in values}
    return series.fillna("").astype(str).str.lower().isin(allowed)


def text_contains_any(gdf: gpd.GeoDataFrame, words: Iterable[str]) -> pd.Series:
    """Search common text/tag columns for any keyword."""

    haystack = pd.Series("", index=gdf.index, dtype=str)
    for col in ["name", "amenity", "shop", "building", "tourism", "other_tags"]:
        if col in gdf.columns:
            haystack = haystack + " " + gdf[col].fillna("").astype(str).str.lower()
    pattern = "|".join(words)
    return haystack.str.contains(pattern, regex=True, na=False)


def representative_points(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Convert geometries to representative point latitude/longitude rows."""

    if gdf.empty:
        return pd.DataFrame(columns=["latitude", "longitude"])
    points = gdf.copy()
    points["geometry"] = points.geometry.representative_point()
    out = pd.DataFrame(
        {
            "latitude": points.geometry.y.astype(float),
            "longitude": points.geometry.x.astype(float),
        }
    )
    for col in ["name", "amenity", "shop", "building", "railway", "highway", "public_transport", "other_tags"]:
        if col in points.columns:
            out[col] = points[col].fillna("").astype(str).to_numpy()
    return out.drop_duplicates(subset=["latitude", "longitude"]).reset_index(drop=True)


def sample_lines_to_points(gdf: gpd.GeoDataFrame, spacing_km: float = 5.0) -> pd.DataFrame:
    """Sample line geometries into representative points for nearest-distance indexes."""

    if gdf.empty:
        return pd.DataFrame(columns=["latitude", "longitude"])

    projected = gdf.to_crs(epsg=3857)
    rows: list[dict[str, object]] = []
    spacing_m = spacing_km * 1000.0

    for _, row in projected.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        lines = list(geom.geoms) if isinstance(geom, MultiLineString) else [geom]
        for line in lines:
            if not isinstance(line, LineString) or line.length == 0:
                continue
            distances = np.arange(0.0, line.length, spacing_m)
            if len(distances) == 0 or distances[-1] != line.length:
                distances = np.append(distances, line.length)
            for distance in distances:
                point = line.interpolate(float(distance))
                rows.append(
                    {
                        "geometry": point,
                        "highway": row.get("highway", ""),
                        "name": row.get("name", ""),
                    }
                )

    if not rows:
        return pd.DataFrame(columns=["latitude", "longitude"])

    sampled = gpd.GeoDataFrame(rows, geometry="geometry", crs=projected.crs).to_crs(epsg=4326)
    out = pd.DataFrame(
        {
            "latitude": sampled.geometry.y.astype(float),
            "longitude": sampled.geometry.x.astype(float),
            "highway": sampled.get("highway", "").astype(str),
            "name": sampled.get("name", "").astype(str),
        }
    )
    out["latitude"] = out["latitude"].round(6)
    out["longitude"] = out["longitude"].round(6)
    return out.drop_duplicates(subset=["latitude", "longitude"]).reset_index(drop=True)


def write_layer(df: pd.DataFrame, path: Path) -> None:
    """Write one extracted OSM layer to CSV."""

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Wrote %d rows to %s", len(df), path)


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between two lat/lon points."""

    lat1, lon1 = np.radians(a)
    lat2, lon2 = np.radians(b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return float(6371.0 * 2.0 * np.arcsin(np.sqrt(h)))


def interpolate_latlon(a: tuple[float, float], b: tuple[float, float], fraction: float) -> tuple[float, float]:
    """Linearly interpolate between nearby lat/lon points."""

    return (a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction)


def sample_way_coords(coords: list[tuple[float, float]], spacing_km: float) -> list[tuple[float, float]]:
    """Sample an OSM way coordinate sequence at an approximate kilometer interval."""

    if len(coords) < 2:
        return coords
    sampled = [coords[0]]
    carry = 0.0
    last = coords[0]
    for current in coords[1:]:
        segment = haversine_km(last, current)
        if segment <= 0:
            last = current
            continue
        distance_to_next = spacing_km - carry
        while distance_to_next <= segment:
            fraction = distance_to_next / segment
            sampled_point = interpolate_latlon(last, current, fraction)
            sampled.append(sampled_point)
            last = sampled_point
            segment = haversine_km(last, current)
            distance_to_next = spacing_km
        carry += segment
        if carry >= spacing_km:
            carry = 0.0
        last = current
    sampled.append(coords[-1])
    return sampled


def row_from_point(lat: float, lon: float, tags: dict[str, str] | None = None) -> dict[str, object]:
    """Create a normalized point row."""

    tags = tags or {}
    return {
        "latitude": round(float(lat), 6),
        "longitude": round(float(lon), 6),
        "name": tags.get("name", ""),
        "amenity": tags.get("amenity", ""),
        "shop": tags.get("shop", ""),
        "railway": tags.get("railway", ""),
        "highway": tags.get("highway", ""),
        "public_transport": tags.get("public_transport", ""),
    }


def is_fuel(tags: dict[str, str]) -> bool:
    return tags.get("amenity") == "fuel"


def is_mall(tags: dict[str, str]) -> bool:
    name = tags.get("name", "").lower()
    return tags.get("shop") == "mall" or "mall" in name or "shopping centre" in name or "shopping center" in name


def is_railway_station(tags: dict[str, str]) -> bool:
    return tags.get("railway") in {"station", "halt"} or (
        tags.get("public_transport") == "station" and "rail" in tags.get("name", "").lower()
    )


def is_bus_station(tags: dict[str, str]) -> bool:
    return tags.get("amenity") == "bus_station" or tags.get("highway") == "bus_stop" or (
        tags.get("public_transport") in {"station", "platform"} and "bus" in tags.get("name", "").lower()
    )


def is_commercial(tags: dict[str, str]) -> bool:
    return bool(tags.get("shop")) or tags.get("amenity") in {
        "marketplace",
        "restaurant",
        "cafe",
        "fuel",
        "bank",
        "atm",
        "cinema",
        "fast_food",
        "pharmacy",
    } or is_mall(tags)


def append_poi_rows(rows: dict[str, list[dict[str, object]]], lat: float, lon: float, tags: dict[str, str]) -> None:
    """Append a point to relevant POI output collections."""

    point = row_from_point(lat, lon, tags)
    if is_fuel(tags):
        rows["fuel_stations"].append(point)
    if is_mall(tags):
        rows["malls"].append(point)
    if is_railway_station(tags):
        rows["railway_stations"].append(point)
    if is_bus_station(tags):
        rows["bus_stations"].append(point)
    if is_commercial(tags):
        rows["commercial_pois"].append(point)


def dataframe_from_rows(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Build a de-duplicated point dataframe from extracted rows."""

    if not rows:
        return pd.DataFrame(columns=["latitude", "longitude"])
    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset=["latitude", "longitude"]).reset_index(drop=True)


def extract_osm_layers_osmium(
    pbf_path: Path,
    output_paths: OsmLayerPaths | None = None,
    road_spacing_km: float = 5.0,
    skip_roads: bool = False,
    only_roads: bool = False,
) -> dict[str, int]:
    """Extract OSM layers using pyosmium streaming."""

    import osmium
    from osmium import filter as osm_filter

    output_paths = output_paths or OsmLayerPaths()
    fieldnames = ["latitude", "longitude", "name", "amenity", "shop", "railway", "highway", "public_transport"]
    all_outputs = {
        "roads": output_paths.roads,
        "highways": output_paths.highways,
        "fuel_stations": output_paths.fuel_stations,
        "malls": output_paths.malls,
        "railway_stations": output_paths.railway_stations,
        "bus_stations": output_paths.bus_stations,
        "commercial_pois": output_paths.commercial_pois,
    }
    if only_roads:
        outputs = {key: all_outputs[key] for key in ("roads", "highways")}
    elif skip_roads:
        outputs = {key: value for key, value in all_outputs.items() if key not in {"roads", "highways"}}
    else:
        outputs = all_outputs
    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    files = {key: path.open("w", newline="", encoding="utf-8") for key, path in outputs.items()}
    writers = {key: csv.DictWriter(fh, fieldnames=fieldnames) for key, fh in files.items()}
    for writer in writers.values():
        writer.writeheader()
    counts = {key: 0 for key in outputs}

    def write(key: str, row: dict[str, object]) -> None:
        writers[key].writerow({field: row.get(field, "") for field in fieldnames})
        counts[key] += 1

    def append_pois(lat: float, lon: float, tags: dict[str, str]) -> None:
        point = row_from_point(lat, lon, tags)
        if is_fuel(tags):
            if "fuel_stations" in writers:
                write("fuel_stations", point)
        if is_mall(tags):
            if "malls" in writers:
                write("malls", point)
        if is_railway_station(tags):
            if "railway_stations" in writers:
                write("railway_stations", point)
        if is_bus_station(tags):
            if "bus_stations" in writers:
                write("bus_stations", point)
        if is_commercial(tags):
            if "commercial_pois" in writers:
                write("commercial_pois", point)

    def obj_coords(obj) -> list[tuple[float, float]]:
        if isinstance(obj, osmium.osm.Node):
            return [(obj.location.lat, obj.location.lon)] if obj.location.valid() else []
        return [(node.lat, node.lon) for node in obj.nodes if node.location.valid()]

    try:
        if not only_roads:
            logger.info("Extracting OSM POIs from %s", pbf_path)
            poi_processor = (
                osmium.FileProcessor(str(pbf_path), entities=osmium.osm.NODE | osmium.osm.WAY)
                .with_locations()
                .with_filter(osm_filter.KeyFilter("amenity", "shop", "railway", "public_transport"))
            )
            for idx, obj in enumerate(poi_processor, start=1):
                if idx % 500_000 == 0:
                    logger.info("Processed %d tagged POI objects", idx)
                    for fh in files.values():
                        fh.flush()
                tags = {tag.k: tag.v for tag in obj.tags}
                coords = obj_coords(obj)
                if not coords:
                    continue
                if isinstance(obj, osmium.osm.Node):
                    append_pois(coords[0][0], coords[0][1], tags)
                else:
                    arr = np.asarray(coords, dtype=float)
                    append_pois(float(arr[:, 0].mean()), float(arr[:, 1].mean()), tags)

            logger.info("Extracting OSM bus stops from %s", pbf_path)
            bus_processor = (
                osmium.FileProcessor(str(pbf_path), entities=osmium.osm.NODE | osmium.osm.WAY)
                .with_locations()
                .with_filter(osm_filter.TagFilter(("highway", "bus_stop")))
            )
            for obj in bus_processor:
                tags = {tag.k: tag.v for tag in obj.tags}
                coords = obj_coords(obj)
                if not coords:
                    continue
                if isinstance(obj, osmium.osm.Node):
                    append_pois(coords[0][0], coords[0][1], tags)
                else:
                    arr = np.asarray(coords, dtype=float)
                    append_pois(float(arr[:, 0].mean()), float(arr[:, 1].mean()), tags)

        if not skip_roads:
            logger.info("Extracting OSM roads/highways from %s", pbf_path)
            road_tags = tuple(("highway", value) for value in ROAD_HIGHWAY_VALUES)
            road_processor = (
                osmium.FileProcessor(str(pbf_path), entities=osmium.osm.NODE | osmium.osm.WAY)
                .with_locations()
                .with_filter(osm_filter.TagFilter(*road_tags))
            )
            for idx, way in enumerate(road_processor, start=1):
                if idx % 500_000 == 0:
                    logger.info("Processed %d road ways", idx)
                    for fh in files.values():
                        fh.flush()
                tags = {tag.k: tag.v for tag in way.tags}
                coords = obj_coords(way)
                if not coords:
                    continue
                highway = tags.get("highway", "")
                sampled = sample_way_coords(coords, road_spacing_km)
                if highway in ROAD_HIGHWAY_VALUES:
                    for lat, lon in sampled:
                        write("roads", row_from_point(lat, lon, tags))
                if highway in NATIONAL_HIGHWAY_VALUES:
                    for lat, lon in sampled:
                        write("highways", row_from_point(lat, lon, tags))
    finally:
        for fh in files.values():
            fh.close()

    logger.info("OSM extraction counts: %s", counts)
    return counts


def extract_osm_layers(
    pbf_path: Path,
    output_paths: OsmLayerPaths | None = None,
    road_spacing_km: float = 5.0,
    skip_roads: bool = False,
    only_roads: bool = False,
) -> dict[str, int]:
    """Extract roads, highways, fuel, malls, railway stations, and bus stands."""

    try:
        import osmium  # noqa: F401

        return extract_osm_layers_osmium(
            pbf_path,
            output_paths,
            road_spacing_km,
            skip_roads=skip_roads,
            only_roads=only_roads,
        )
    except ImportError:
        logger.warning("osmium is not installed; falling back to pyogrio extraction")

    output_paths = output_paths or OsmLayerPaths()
    points = read_osm_layer(pbf_path, "points")
    multipolygons = read_osm_layer(pbf_path, "multipolygons")
    lines = read_osm_layer(pbf_path, "lines")

    highway_values = tag_series(lines, "highway")
    road_lines = lines[contains_any(highway_values, ROAD_HIGHWAY_VALUES)].copy()
    highway_lines = lines[contains_any(highway_values, NATIONAL_HIGHWAY_VALUES)].copy()

    point_like = pd.concat(
        [
            representative_points(points),
            representative_points(multipolygons),
        ],
        ignore_index=True,
    ).drop_duplicates(subset=["latitude", "longitude"])
    point_gdf = gpd.GeoDataFrame(
        point_like,
        geometry=gpd.points_from_xy(point_like["longitude"], point_like["latitude"]),
        crs="EPSG:4326",
    )

    amenity = tag_series(point_gdf, "amenity")
    shop = tag_series(point_gdf, "shop")
    railway = tag_series(point_gdf, "railway")
    highway = tag_series(point_gdf, "highway")
    public_transport = tag_series(point_gdf, "public_transport")

    fuel = point_like[amenity.eq("fuel")].copy()
    malls = point_like[shop.eq("mall") | text_contains_any(point_gdf, ["mall", "shopping centre", "shopping center"])].copy()
    railway_stations = point_like[
        railway.isin(["station", "halt"])
        | (public_transport.eq("station") & text_contains_any(point_gdf, ["railway", "train", "metro"]))
    ].copy()
    bus_stations = point_like[
        amenity.eq("bus_station")
        | highway.eq("bus_stop")
        | (public_transport.isin(["station", "platform"]) & text_contains_any(point_gdf, ["bus"]))
    ].copy()
    commercial = point_like[
        shop.ne("")
        | amenity.isin(["marketplace", "restaurant", "cafe", "fuel", "bank", "atm", "cinema"])
        | point_like.index.isin(malls.index)
    ].copy()

    roads = sample_lines_to_points(road_lines, spacing_km=road_spacing_km)
    highways = sample_lines_to_points(highway_lines, spacing_km=road_spacing_km)

    write_layer(roads, output_paths.roads)
    write_layer(highways, output_paths.highways)
    write_layer(fuel, output_paths.fuel_stations)
    write_layer(malls, output_paths.malls)
    write_layer(railway_stations, output_paths.railway_stations)
    write_layer(bus_stations, output_paths.bus_stations)
    write_layer(commercial, output_paths.commercial_pois)

    return {
        "roads": len(roads),
        "highways": len(highways),
        "fuel_stations": len(fuel),
        "malls": len(malls),
        "railway_stations": len(railway_stations),
        "bus_stations": len(bus_stations),
        "commercial_pois": len(commercial),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract OSM demand layers from Geofabrik India PBF.")
    parser.add_argument("--pbf", type=Path, default=None, help="Path to a local .osm.pbf file.")
    parser.add_argument("--download-osm", action="store_true", help="Download india-latest.osm.pbf if missing.")
    parser.add_argument("--road-spacing-km", type=float, default=5.0, help="Road/highway line sampling interval.")
    parser.add_argument("--skip-roads", action="store_true", help="Extract only OSM POI layers, skipping roads/highways.")
    parser.add_argument("--only-roads", action="store_true", help="Extract only roads/highways, skipping POI layers.")
    parser.add_argument("--output-prefix", default="osm", help="Output CSV prefix, e.g. osm_southern_zone.")
    parser.add_argument("--output-dir", type=Path, default=RAW_DIR, help="Directory for extracted layer CSV files.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        pbf_path = ensure_osm_pbf(download=args.download_osm, pbf_path=args.pbf)
        counts = extract_osm_layers(
            pbf_path,
            output_paths=layer_paths(args.output_prefix, args.output_dir),
            road_spacing_km=args.road_spacing_km,
            skip_roads=args.skip_roads,
            only_roads=args.only_roads,
        )
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    for layer, count in counts.items():
        print(f"{layer}: {count}")


if __name__ == "__main__":
    main()
