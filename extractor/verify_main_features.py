#!/usr/bin/env python3
"""Validate all 200 main-experiment processed samples (no detector metrics)."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "generator"))
from experiment_plan import build_catalog, validate_run_tag  # noqa: E402
from extract_features import FEATURE_COLUMNS  # noqa: E402


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def csv_rows(path: Path, names: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == names, f"{path.name}: column/order mismatch")
        rows = list(reader)
    require(all(None not in row and set(row) == set(names) for row in rows),
            f"{path.name}: malformed rows")
    return rows


def validate(tag: str, processed_root: Path, raw_root: Path) -> None:
    validate_run_tag(tag)
    catalog = {trial.trial_id: trial for trial in build_catalog()}
    root = processed_root / tag
    fpath = root / "features.csv"
    lpath = root / "labels.csv"
    ppath = root / "provenance.json"
    feature_rows = csv_rows(fpath, ["trial_id", *FEATURE_COLUMNS])
    label_rows = csv_rows(lpath, ["trial_id", "traffic_class", "label", "jitter_pct", "normal_profile"])
    require(len(feature_rows) == len(label_rows) == 200, "expected 200 feature and label rows")

    for rows, name in ((feature_rows, "features"), (label_rows, "labels")):
        ids = [row["trial_id"] for row in rows]
        require(len(ids) == len(set(ids)) == 200 and set(ids) == set(catalog),
                f"{name}: missing, extra, or duplicate trial IDs")
    for row in feature_rows:
        for column in FEATURE_COLUMNS:
            require(row[column] != "", f"{row['trial_id']}: missing {column}")
            try:
                value = float(row[column])
            except ValueError as exc:
                raise ValueError(f"{row['trial_id']}: invalid {column}") from exc
            require(math.isfinite(value), f"{row['trial_id']}: nonfinite {column}")
        require(float(row["iat_cv"]) >= 0, f"{row['trial_id']}: negative CV")
    for row in label_rows:
        trial = catalog[row["trial_id"]]
        require(row["traffic_class"] == trial.category and
                row["label"] == ("1" if trial.category == "beacon" else "0"),
                f"{trial.trial_id}: class/label mismatch")
        require(row["jitter_pct"] == (trial.value if trial.category == "beacon" else ""),
                f"{trial.trial_id}: jitter label mismatch")
        require(row["normal_profile"] == (trial.value if trial.category == "normal" else ""),
                f"{trial.trial_id}: normal profile mismatch")

    with ppath.open("r", encoding="utf-8") as handle:
        provenance = json.load(handle)
    require(provenance.get("run_tag") == tag and
            provenance.get("extractor_schema_version") == 1 and
            provenance.get("feature_definition_version") == "1.0.0" and
            provenance.get("feature_columns") == FEATURE_COLUMNS and
            provenance.get("trial_count") == 200 and
            provenance.get("validation_status") == "pass" and
            provenance.get("failed_trials") == [],
            "extractor provenance/schema/count mismatch")
    records = provenance.get("trials", [])
    require(len(records) == 200 and
            len({r.get("trial_id") for r in records}) == 200 and
            {r.get("trial_id") for r in records} == set(catalog),
            "provenance trial IDs mismatch")
    for row in records:
        trial_id = row["trial_id"]
        with (raw_root / tag / "manifests" / f"{trial_id}.json").open(
            "r", encoding="utf-8"
        ) as handle:
            raw = json.load(handle)
        require(row.get("validation_status") == "pass" and
                not row.get("validation_errors") and
                row.get("flow_count") == 30 and
                row.get("flow_start_count") == 30 and
                row.get("iat_count") == 29 and
                isinstance(row.get("packet_count"), int) and row["packet_count"] > 0 and
                float(row.get("total_extraction_ms", -1)) > 0,
                f"{trial_id}: invalid flow/provenance metrics")
        require(row.get("source_pcap_sha256") == raw.get("pcap_sha256"),
                f"{trial_id}: processed/raw PCAP hash mismatch")
        require(row.get("source_manifest") == f"/data/raw/{tag}/manifests/{trial_id}.json",
                f"{trial_id}: raw manifest provenance mismatch")
        require(row.get("source_pcap") ==
                f"/pcap/{tag}/{catalog[trial_id].category}/{trial_id}.pcap",
                f"{trial_id}: source PCAP provenance mismatch")

    print(f"PASS: main experiment {tag}: 200 processed feature rows and 200 label rows")
    print("PASS: 13 finite features, feature/label separation, exact trial catalog")
    print("PASS: 30 TCP flows and 29 IAT per trial, raw PCAP SHA-256 provenance")
    print("PASS: extractor schema 1.0.0, all trials validated, no detector tuning performed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tag", required=True)
    parser.add_argument("--processed-root", type=Path, default=Path("/data/processed"))
    parser.add_argument("--raw-root", type=Path, default=Path("/data/raw"))
    args = parser.parse_args()
    try:
        validate(args.run_tag, args.processed_root, args.raw_root)
        return 0
    except (AssertionError, ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
