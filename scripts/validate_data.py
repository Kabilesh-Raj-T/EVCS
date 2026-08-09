"""Validate the processed demand feature dataset."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.preprocessing.config import DATA_QUALITY_REPORT_PATH, DEMAND_FEATURES_PATH
from backend.preprocessing.preprocess import DISTANCE_COLUMNS, SCORE_COLUMNS

REQUIRED_COLUMNS = ["latitude", "longitude", "state", "district", *SCORE_COLUMNS, *DISTANCE_COLUMNS]


def validate(path: Path | None = None) -> dict:
    features = pd.read_parquet(path or DEMAND_FEATURES_PATH)
    missing = [c for c in REQUIRED_COLUMNS if c not in features.columns]
    cols = [c for c in [*SCORE_COLUMNS, *DISTANCE_COLUMNS, "demand_score"] if c in features.columns]
    report = {
        "records": len(features),
        "missing_required_columns": missing,
        "missing_values": features.isna().sum().to_dict(),
        "duplicate_coordinates": int(features.duplicated(subset=["latitude", "longitude"]).sum()),
        "out_of_range_scores": {c: int((features[c].dropna().lt(0) | features[c].dropna().gt(1)).sum()) for c in SCORE_COLUMNS if c in features.columns},
        "feature_statistics": features[cols].describe().replace({np.nan: None}).to_dict(),
        "by_state": features["state"].fillna("").replace("", "Unknown").value_counts().to_dict() if "state" in features.columns else {},
    }
    DATA_QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_QUALITY_REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    report = validate(args.path)
    print(f"Validated {report['records']} rows")
    if report["missing_required_columns"]:
        raise SystemExit(f"Missing columns: {report['missing_required_columns']}")


if __name__ == "__main__":
    main()
