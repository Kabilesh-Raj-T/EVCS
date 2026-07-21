"""Merge zone-prefixed OSM extraction CSVs into canonical pipeline inputs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.preprocessing.config import RAW_DIR


LAYERS = [
    "roads",
    "highways",
    "fuel_stations",
    "malls",
    "railway_stations",
    "bus_stations",
    "commercial_pois",
]


def merge_layer(layer: str, raw_dir: Path = RAW_DIR) -> tuple[Path, int]:
    pattern = f"osm_*_zone_{layer}.csv"
    sources = sorted(raw_dir.glob(pattern))
    if not sources:
        raise FileNotFoundError(f"No zone files found for {layer}: {pattern}")

    frames = []
    for path in sources:
        df = pd.read_csv(path, low_memory=False)
        if {"latitude", "longitude"}.issubset(df.columns):
            df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce").round(6)
            df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce").round(6)
            df = df.dropna(subset=["latitude", "longitude"])
        df["osm_zone_source"] = path.stem
        frames.append(df)

    merged = pd.concat(frames, ignore_index=True)
    if {"latitude", "longitude"}.issubset(merged.columns):
        merged = merged.drop_duplicates(subset=["latitude", "longitude"])
    target = raw_dir / f"osm_{layer}.csv"
    merged.to_csv(target, index=False)
    return target, len(merged)


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge zone OSM CSV layers into canonical osm_*.csv files.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args()

    for layer in LAYERS:
        target, rows = merge_layer(layer, args.raw_dir)
        print(f"{target.name}: {rows}")


if __name__ == "__main__":
    main()

