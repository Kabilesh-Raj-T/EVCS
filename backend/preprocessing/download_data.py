"""Download helpers and source manifest generation for the data layer."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse

import requests

from .cache import ensure_directories, write_json
from .config import CURRENT_ADM1_GEOJSON, CURRENT_BEE_CSV, DATASET_SOURCES, RAW_DIR, SOURCE_MANIFEST_PATH


logger = logging.getLogger(__name__)


def filename_from_url(url: str, dataset_key: str) -> str:
    """Infer a stable local filename from a source URL."""

    parsed = urlparse(url)
    name = Path(parsed.path).name
    return name or f"{dataset_key}.download"


def download_file(url: str, target: Path, timeout: int = 60) -> Path:
    """Download a URL to a local target path."""

    target.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with target.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
    return target


def write_source_manifest() -> dict[str, object]:
    """Write source metadata and local availability to reports/source_manifest.json."""

    ensure_directories()
    manifest: dict[str, object] = {"datasets": {}}
    for key, meta in DATASET_SOURCES.items():
        local_matches = local_files_for_dataset(key)
        if key == "bee_ev_charging_stations" and CURRENT_BEE_CSV.exists():
            local_matches.append(CURRENT_BEE_CSV)
        if key == "geoboundaries_adm1" and CURRENT_ADM1_GEOJSON.exists():
            local_matches.append(CURRENT_ADM1_GEOJSON)
        manifest["datasets"][key] = {
            **meta,
            "local_files": [str(path) for path in local_matches],
            "available_locally": bool(local_matches),
        }
    write_json(SOURCE_MANIFEST_PATH, manifest)
    return manifest


def download_configured_sources(include_large: bool = False) -> dict[str, object]:
    """Download configured direct URLs where practical and refresh the manifest."""

    ensure_directories()
    results: dict[str, object] = {}
    for key, meta in DATASET_SOURCES.items():
        local_matches = local_files_for_dataset(key)
        if meta.get("large") and not include_large:
            results[key] = {"status": "skipped_large", "url": meta["url"]}
            continue
        if "placeholder" in key or not meta.get("required"):
            results[key] = {"status": "placeholder", "url": meta["url"]}
            continue

        url = str(meta["url"])
        target = RAW_DIR / f"{key}_{filename_from_url(url, key)}"
        try:
            if target.exists() or local_matches:
                results[key] = {"status": "exists", "path": str(target if target.exists() else local_matches[0])}
            else:
                download_file(url, target)
                results[key] = {"status": "downloaded", "path": str(target)}
        except Exception as exc:
            logger.exception("Failed to download %s", key)
            results[key] = {"status": "failed", "error": str(exc), "url": url}

    manifest = write_source_manifest()
    manifest["download_results"] = results
    write_json(SOURCE_MANIFEST_PATH, manifest)
    return manifest


def local_files_for_dataset(key: str) -> list[Path]:
    """Return known local files for a dataset key."""

    if key == "worldpop_india_population_density":
        return sorted(RAW_DIR.glob("*worldpop*.tif"))
    if key == "geoboundaries_adm2":
        return sorted(RAW_DIR.glob("*adm2*.geojson"))
    if key == "ourairports_india":
        return sorted(RAW_DIR.glob("*airports*.csv"))
    if key == "geofabrik_osm_india":
        pbf_files = [
            path
            for path in sorted(RAW_DIR.glob("*.osm.pbf"))
            if path.suffix != ".corrupt"
        ]
        osm_layers = sorted(RAW_DIR.glob("osm_*.csv"))
        return pbf_files + osm_layers
    return [path for path in sorted(RAW_DIR.glob(f"*{key}*")) if path.suffix != ".partial"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Download source data and write the EVCS source manifest.")
    parser.add_argument("--include-large", action="store_true", help="Also attempt large raster/PBF/GHSL downloads.")
    parser.add_argument("--manifest-only", action="store_true", help="Only write source_manifest.json.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.manifest_only:
        write_source_manifest()
    else:
        download_configured_sources(include_large=args.include_large)


if __name__ == "__main__":
    main()
