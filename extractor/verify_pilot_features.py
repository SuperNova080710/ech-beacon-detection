#!/usr/bin/env python3
"""Verify processed Feature Extractor outputs for the eight pilot-v2 trials."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from extract_features import FEATURE_COLUMNS

EXPECTED_TRIALS = {
    "beacon-j00-t01",
    "beacon-j10-t01",
    "beacon-j30-t01",
    "beacon-j50-t01",
    "beacon-j70-t01",
    "normal-interactive-burst-t01",
    "normal-irregular-lognormal-t01",
    "normal-mixed-activity-t01",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tag", default="pilot-v2")
    parser.add_argument("--processed-root", default="/data/processed")
    args = parser.parse_args()

    root = Path(args.processed_root) / args.run_tag
    features_path = root / "features.csv"
    labels_path = root / "labels.csv"
    provenance_path = root / "provenance.json"

    features = read_csv(features_path)
    labels = read_csv(labels_path)
    with provenance_path.open("r", encoding="utf-8") as handle:
        provenance = json.load(handle)

    feature_ids = {row["trial_id"] for row in features}
    label_ids = {row["trial_id"] for row in labels}
    if feature_ids != EXPECTED_TRIALS:
        raise AssertionError(f"unexpected feature trial IDs: {sorted(feature_ids)}")
    if label_ids != EXPECTED_TRIALS:
        raise AssertionError(f"unexpected label trial IDs: {sorted(label_ids)}")
    if len(features) != 8 or len(labels) != 8:
        raise AssertionError("pilot output must contain exactly 8 feature/label rows")

    for row in features:
        if set(row) != {"trial_id", *FEATURE_COLUMNS}:
            raise AssertionError(f"{row['trial_id']}: feature schema mismatch")
        for column in FEATURE_COLUMNS:
            raw = row[column]
            if raw == "":
                raise AssertionError(f"{row['trial_id']}: {column} is missing")
            value = float(raw)
            if not math.isfinite(value):
                raise AssertionError(f"{row['trial_id']}: {column} is non-finite")

    for row in labels:
        if row["traffic_class"] == "beacon":
            if row["label"] != "1" or row["jitter_pct"] not in {"0", "10", "30", "50", "70"}:
                raise AssertionError(f"{row['trial_id']}: invalid beacon label metadata")
        elif row["traffic_class"] == "normal":
            if row["label"] != "0" or row["normal_profile"] not in {
                "interactive-burst",
                "irregular-lognormal",
                "mixed-activity",
            }:
                raise AssertionError(f"{row['trial_id']}: invalid normal label metadata")
        else:
            raise AssertionError(f"{row['trial_id']}: unknown traffic class")

    if provenance.get("validation_status") != "pass":
        raise AssertionError("provenance validation_status is not pass")
    if provenance.get("trial_count") != 8:
        raise AssertionError("provenance trial_count is not 8")
    if provenance.get("feature_columns") != FEATURE_COLUMNS:
        raise AssertionError("provenance feature column order mismatch")

    trial_records = provenance.get("trials") or []
    if {row["trial_id"] for row in trial_records} != EXPECTED_TRIALS:
        raise AssertionError("provenance trial IDs mismatch")
    for row in trial_records:
        if row.get("validation_status") != "pass":
            raise AssertionError(f"{row['trial_id']}: validation failed")
        if row.get("flow_count") != 30 or row.get("flow_start_count") != 30:
            raise AssertionError(f"{row['trial_id']}: expected 30 flows/flow starts")
        if row.get("iat_count") != 29:
            raise AssertionError(f"{row['trial_id']}: expected 29 IAT values")
        if float(row.get("total_extraction_ms", 0)) <= 0:
            raise AssertionError(f"{row['trial_id']}: invalid extraction timing")

    print("PASS: pilot-v2 contains exactly 8 feature rows and 8 label rows")
    print("PASS: all 13 features are finite for every pilot trial")
    print("PASS: feature and label trial IDs match one-to-one")
    print("PASS: all pilot trials contain 30 TCP flows and 29 flow-start IAT values")
    print("PASS: provenance validation and extraction timing are complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
