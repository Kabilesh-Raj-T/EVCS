"""Validate the processed demand feature dataset and refresh data quality reports."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.preprocessing.cache import write_json
from backend.preprocessing.config import DATA_QUALITY_REPORT_PATH, DEMAND_FEATURES_CSV_FALLBACK, DEMAND_FEATURES_PATH
from backend.preprocessing.feature_builder import DISTANCE_COLUMNS, SCORE_COLUMNS, feature_statistics
from backend.preprocessing.spatial_join import coverage_by_region


REQUIRED_COLUMNS = [
    "latitude",
    "longitude",
    "state",
    "district",
    *SCORE_COLUMNS,
    *DISTANCE_COLUMNS,
]


def load_features(path: Path | None = None) -> pd.DataFrame:
    target = path or DEMAND_FEATURES_PATH
    if target.exists():
        return pd.read_parquet(target)
    if DEMAND_FEATURES_CSV_FALLBACK.exists():
        return pd.read_csv(DEMAND_FEATURES_CSV_FALLBACK)
    raise FileNotFoundError(f"No processed demand feature dataset found at {target}")


def validate(path: Path | None = None) -> dict[str, object]:
    features = load_features(path)
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in features.columns]
    out_of_range_scores = {
        col: int((features[col].dropna().lt(0) | features[col].dropna().gt(1)).sum())
        for col in SCORE_COLUMNS
        if col in features.columns
    }
    report = {
        "records": len(features),
        "missing_required_columns": missing_columns,
        "missing_values": features.isna().sum().to_dict(),
        "duplicate_candidate_coordinates": int(features.duplicated(subset=["latitude", "longitude"]).sum()),
        "out_of_range_scores": out_of_range_scores,
        **coverage_by_region(features),
        **feature_statistics(features),
    }
    write_json(DATA_QUALITY_REPORT_PATH, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate processed EVCS demand features.")
    parser.add_argument("--path", type=Path, default=None, help="Optional feature dataset path.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    report = validate(args.path)
    print(f"Validated {report['records']} demand feature rows")
    if report["missing_required_columns"]:
        raise SystemExit(f"Missing required columns: {report['missing_required_columns']}")


if __name__ == "__main__":
    main()
