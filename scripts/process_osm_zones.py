"""Download and extract OSM layers for India Geofabrik zones."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "backend" / "data" / "raw"

ZONES = {
    "northern_zone": "https://download.geofabrik.de/asia/india/northern-zone-latest.osm.pbf",
    "central_zone": "https://download.geofabrik.de/asia/india/central-zone-latest.osm.pbf",
    "eastern_zone": "https://download.geofabrik.de/asia/india/eastern-zone-latest.osm.pbf",
    "north_eastern_zone": "https://download.geofabrik.de/asia/india/north-eastern-zone-latest.osm.pbf",
    "southern_zone": "https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf",
    "western_zone": "https://download.geofabrik.de/asia/india/western-zone-latest.osm.pbf",
}


def download_with_resume(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    remote = int(requests.head(url, allow_redirects=True, timeout=30).headers["Content-Length"])
    local = target.stat().st_size if target.exists() else 0
    if local == remote:
        print(f"{target.name}: already downloaded ({local:,} bytes)")
        return
    if local > remote:
        target.unlink()
        local = 0

    headers = {"Range": f"bytes={local}-"} if local else {}
    mode = "ab" if local else "wb"
    print(f"{target.name}: downloading from byte {local:,} of {remote:,}")
    with requests.get(url, headers=headers, stream=True, timeout=120) as response:
        if local and response.status_code == 200:
            print(f"{target.name}: server ignored range; restarting")
            mode = "wb"
        response.raise_for_status()
        with target.open(mode) as fh:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    fh.write(chunk)

    final = target.stat().st_size
    if final != remote:
        raise RuntimeError(f"{target.name}: size mismatch, expected {remote}, got {final}")
    print(f"{target.name}: download complete")


def run_extraction(zone: str, pbf_path: Path, road_spacing_km: float, skip_existing: bool) -> None:
    prefix = f"osm_{zone}"
    expected = [
        RAW_DIR / f"{prefix}_{layer}.csv"
        for layer in [
            "roads",
            "highways",
            "fuel_stations",
            "malls",
            "railway_stations",
            "bus_stations",
            "commercial_pois",
        ]
    ]
    if skip_existing and all(path.exists() and path.stat().st_size > 80 for path in expected):
        print(f"{zone}: extracted files already present")
        return

    env = {"PYTHONDONTWRITEBYTECODE": "1"}
    print(f"{zone}: extracting POIs")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "extract_osm.py"),
            "--pbf",
            str(pbf_path),
            "--skip-roads",
            "--output-prefix",
            prefix,
        ],
        cwd=ROOT,
        check=True,
        env={**env, **dict()},
    )

    print(f"{zone}: extracting roads/highways")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "extract_osm.py"),
            "--pbf",
            str(pbf_path),
            "--only-roads",
            "--road-spacing-km",
            str(road_spacing_km),
            "--output-prefix",
            prefix,
        ],
        cwd=ROOT,
        check=True,
        env={**env, **dict()},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Geofabrik India zone PBFs into OSM layer CSVs.")
    parser.add_argument("--zones", nargs="*", default=list(ZONES), choices=list(ZONES))
    parser.add_argument("--road-spacing-km", type=float, default=10.0)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    for zone in args.zones:
        url = ZONES[zone]
        pbf_path = RAW_DIR / f"geofabrik_{zone.replace('_', '-')}-latest.osm.pbf"
        download_with_resume(url, pbf_path)
        run_extraction(zone, pbf_path, args.road_spacing_km, args.skip_existing)


if __name__ == "__main__":
    main()

