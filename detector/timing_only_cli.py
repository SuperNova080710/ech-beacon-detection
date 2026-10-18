#!/usr/bin/env python3
"""Locked timing-only data split, normal-only calibration, and label-free inference."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from timing_only import (
    DETECTOR_VERSION,
    FEATURE_DEFINITION_VERSION,
    SCORE_FEATURE,
    calibrate_from_normal,
    checked_cv,
    expected_catalog,
    predict_iat_cv,
    validate_full_catalog,
)

FEATURE_COLUMNS = (
    "iat_mean_s", "iat_std_s", "iat_cv", "iat_mad_s",
    "packet_size_mean_bytes", "packet_size_std_bytes", "packet_size_cv",
    "out_in_packet_ratio", "byte_asymmetry", "direction_change_ratio",
    "burst_count", "burst_mean_size", "burst_interval_cv",
)
FEATURE_HEADER = ("trial_id", *FEATURE_COLUMNS)
LABEL_HEADER = ("trial_id", "traffic_class", "label", "jitter_pct", "normal_profile")
SPLIT_FILES = {
    "calibration_features": "calibration_features.csv",
    "calibration_labels": "calibration_labels.csv",
    "test_features": "test_features.csv",
    "test_labels": "test_labels.csv",
}
PREDICTION_HEADER = (
    "trial_id", "iat_cv", "prediction", "detector_version",
    "calibration_fingerprint_sha256",
)


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def canonical_sha(data: object) -> str:
    raw = json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def read_csv(path: Path, expected_header: tuple[str, ...]) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != expected_header:
            raise ValueError(f"CSV schema mismatch: {path}: {reader.fieldnames!r}")
        result = {}
        for row in reader:
            if None in row:
                raise ValueError(f"unexpected extra CSV column: {path}")
            trial_id = row.get("trial_id") or ""
            if not trial_id or trial_id in result:
                raise ValueError(f"missing or duplicate trial_id: {path}: {trial_id!r}")
            if any(row[column] is None for column in expected_header):
                raise ValueError(f"missing CSV cell: {path}, {trial_id}")
            result[trial_id] = row
        return result


def check_features(rows: dict[str, dict[str, str]]) -> None:
    for trial_id, row in rows.items():
        for column in FEATURE_COLUMNS:
            try:
                value = float(row[column])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{trial_id}: invalid {column}") from exc
            if not math.isfinite(value):
                raise ValueError(f"{trial_id}: non-finite {column}")
        checked_cv(row[SCORE_FEATURE])


def check_label(trial_id: str, row: dict[str, str]) -> None:
    if trial_id.startswith("beacon-"):
        expected_jitter = trial_id.split("-")[1][1:]
        if (row["traffic_class"], row["label"], row["jitter_pct"], row["normal_profile"]) != (
            "beacon", "1", str(int(expected_jitter)), "",
        ):
            raise ValueError(f"invalid beacon label metadata: {trial_id}")
    elif trial_id.startswith("normal-"):
        profile = trial_id.removeprefix("normal-").rsplit("-t", 1)[0]
        if (row["traffic_class"], row["label"], row["jitter_pct"], row["normal_profile"]) != (
            "normal", "0", "", profile,
        ):
            raise ValueError(f"invalid normal label metadata: {trial_id}")
    else:
        raise ValueError(f"unexpected trial ID: {trial_id}")


def write_csv(path: Path, header: tuple[str, ...], rows: dict[str, dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for trial_id in sorted(rows):
            writer.writerow(rows[trial_id])


def write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_split_manifest(split_dir: Path) -> dict:
    manifest = read_json(split_dir / "split_manifest.json")
    if manifest.get("detector_version") != DETECTOR_VERSION:
        raise ValueError("split detector version mismatch")
    if manifest.get("feature_definition_version") != FEATURE_DEFINITION_VERSION:
        raise ValueError("split feature version mismatch")
    if manifest.get("counts") != {"calibration": 90, "test": 110, "total": 200}:
        raise ValueError("split expected counts mismatch")
    hashes = manifest.get("file_sha256")
    if not isinstance(hashes, dict) or set(hashes) != set(SPLIT_FILES):
        raise ValueError("invalid split file hash manifest")
    return manifest


def check_hash(split_dir: Path, manifest: dict, name: str) -> Path:
    path = split_dir / SPLIT_FILES[name]
    if digest(path) != manifest["file_sha256"][name]:
        raise ValueError(f"{name} checksum mismatch")
    return path


def split_dataset(processed_dir: Path, out_dir: Path) -> dict:
    """Validate all 200 trial identifiers, then separate without printing test statistics."""
    if out_dir.exists():
        raise ValueError(f"refusing overwrite: {out_dir}")

    feature_file = processed_dir / "features.csv"
    label_file = processed_dir / "labels.csv"
    provenance_file = processed_dir / "provenance.json"
    provenance = read_json(provenance_file)
    if (provenance.get("extractor_schema_version") != 1 or
        provenance.get("feature_definition_version") != FEATURE_DEFINITION_VERSION or
        provenance.get("validation_status") != "pass"):
        raise ValueError("source extractor provenance/schema validation failed")
    tag = provenance.get("run_tag")
    if (not isinstance(tag, str) or not tag or
        tag != processed_dir.name or
        "pilot" in tag.lower() or "capture-check" in tag.lower()):
        raise ValueError("pilot/diagnostic data cannot be used for detector evaluation")
    if provenance.get("trial_count") != 200 or len(provenance.get("trials", [])) != 200:
        raise ValueError("expected 200 validated provenance trial entries")
    trials = provenance["trials"]
    if (len({t.get("trial_id") for t in trials}) != 200 or
        any(t.get("validation_status") != "pass" for t in trials)):
        raise ValueError("invalid or duplicate provenance trials")

    features = read_csv(feature_file, FEATURE_HEADER)
    labels = read_csv(label_file, LABEL_HEADER)
    check_features(features)
    validate_full_catalog(features)
    if set(features) != set(labels) or set(features) != {
        t["trial_id"] for t in trials
    }:
        raise ValueError("feature/label/provenance trial IDs do not match")
    for trial_id, row in labels.items():
        check_label(trial_id, row)

    catalog = expected_catalog()
    result = {}
    out_dir.mkdir(parents=True, exist_ok=False)
    for part in ("calibration", "test"):
        part_ids = {trial_id for trial_id, assignment in catalog.items()
                    if assignment == part}
        part_features = {i: features[i] for i in part_ids}
        part_labels = {i: labels[i] for i in part_ids}
        write_csv(out_dir / f"{part}_features.csv", FEATURE_HEADER, part_features)
        write_csv(out_dir / f"{part}_labels.csv", LABEL_HEADER, part_labels)

    split = {
        "detector_version": DETECTOR_VERSION,
        "feature_definition_version": FEATURE_DEFINITION_VERSION,
        "run_tag": tag,
        "created_at_utc": utc_now(),
        "source_features_sha256": digest(feature_file),
        "source_labels_sha256": digest(label_file),
        "source_provenance_sha256": digest(provenance_file),
        "counts": {"calibration": 90, "test": 110, "total": 200},
        "file_sha256": {
            key: digest(out_dir / filename) for key, filename in SPLIT_FILES.items()
        },
        "paired_beacon_trial_grouping": True,
    }
    write_json(out_dir / "split_manifest.json", split)
    return split


def calibration_core(model: dict) -> dict:
    keys = (
        "detector_version", "feature_definition_version", "score_feature",
        "comparison", "normal_calibration_count", "target_calibration_fpr",
        "threshold", "calibration_fp_count", "calibration_empirical_fpr",
        "normal_calibration_cv_sorted", "calibration_features_sha256",
        "calibration_labels_sha256", "split_manifest_sha256",
    )
    return {key: model[key] for key in keys}


def calibrate_split(split_dir: Path, output: Path) -> dict:
    """Reads only calibration CSVs, never test feature/label rows."""
    if output.exists():
        raise ValueError(f"refusing overwrite: {output}")
    start = perf_counter()
    split = validate_split_manifest(split_dir)
    feature_path = check_hash(split_dir, split, "calibration_features")
    label_path = check_hash(split_dir, split, "calibration_labels")
    features = read_csv(feature_path, FEATURE_HEADER)
    labels = read_csv(label_path, LABEL_HEADER)
    expected = {trial_id for trial_id, assignment in expected_catalog().items()
                if assignment == "calibration"}
    if set(features) != expected or set(labels) != expected:
        raise ValueError("calibration trial IDs do not match predeclared split")
    check_features(features)
    for trial_id, row in labels.items():
        check_label(trial_id, row)
    normal_ids = sorted(
        trial_id for trial_id in expected if trial_id.startswith("normal-")
    )
    if len(normal_ids) != 40:
        raise ValueError("expected 40 calibration normal trial IDs")
    model = calibrate_from_normal(features[i][SCORE_FEATURE] for i in normal_ids)
    model.update({
        "normal_calibration_trial_ids": normal_ids,
        "calibration_features_sha256": digest(feature_path),
        "calibration_labels_sha256": digest(label_path),
        "split_manifest_sha256": digest(split_dir / "split_manifest.json"),
        "calibrated_at_utc": utc_now(),
        "calibration_processing_ms": round((perf_counter() - start) * 1000, 6),
    })
    model["calibration_fingerprint_sha256"] = canonical_sha(calibration_core(model))
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, model)
    return model


def validate_calibration(split_dir: Path, model: dict) -> float:
    if model.get("detector_version") != DETECTOR_VERSION:
        raise ValueError("calibration detector version mismatch")
    if model.get("feature_definition_version") != FEATURE_DEFINITION_VERSION:
        raise ValueError("calibration feature version mismatch")
    if model.get("score_feature") != SCORE_FEATURE or model.get("comparison") != "<":
        raise ValueError("calibration score policy mismatch")
    if model.get("target_calibration_fpr") != 0.05:
        raise ValueError("calibration FPR policy mismatch")
    if model.get("split_manifest_sha256") != digest(split_dir / "split_manifest.json"):
        raise ValueError("calibration split manifest mismatch")
    if model.get("calibration_fingerprint_sha256") != canonical_sha(calibration_core(model)):
        raise ValueError("calibration fingerprint mismatch")
    if model.get("normal_calibration_trial_ids") != sorted(
        trial_id for trial_id, assignment in expected_catalog().items()
        if assignment == "calibration" and trial_id.startswith("normal-")
    ):
        raise ValueError("normal calibration IDs mismatch")
    expected = calibrate_from_normal(model["normal_calibration_cv_sorted"])
    for key in (
        "threshold", "normal_calibration_count", "calibration_fp_count",
        "calibration_empirical_fpr", "normal_calibration_cv_sorted"
    ):
        if model.get(key) != expected[key]:
            raise ValueError(f"calibration order-statistic verification failed: {key}")
    split = validate_split_manifest(split_dir)
    if (model.get("calibration_features_sha256") != split["file_sha256"]["calibration_features"] or
        model.get("calibration_labels_sha256") != split["file_sha256"]["calibration_labels"]):
        raise ValueError("calibration input checksums mismatch")
    return checked_cv(model["threshold"])


def predict_test(split_dir: Path, calibration_file: Path, output: Path) -> dict:
    """No access to test_labels.csv and no label enters the prediction function."""
    if output.exists():
        raise ValueError(f"refusing overwrite: {output}")
    start = perf_counter()
    split = validate_split_manifest(split_dir)
    model = read_json(calibration_file)
    threshold = validate_calibration(split_dir, model)
    test_feature_path = check_hash(split_dir, split, "test_features")
    features = read_csv(test_feature_path, FEATURE_HEADER)
    check_features(features)
    expected = {trial_id for trial_id, assignment in expected_catalog().items()
                if assignment == "test"}
    if set(features) != expected or len(features) != 110:
        raise ValueError("test trial IDs do not match predeclared split")
    result = {}
    fingerprint = model["calibration_fingerprint_sha256"]
    for trial_id, feature_row in features.items():
        result[trial_id] = {
            "trial_id": trial_id,
            "iat_cv": feature_row[SCORE_FEATURE],
            "prediction": predict_iat_cv(feature_row[SCORE_FEATURE], threshold),
            "detector_version": DETECTOR_VERSION,
            "calibration_fingerprint_sha256": fingerprint,
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output, PREDICTION_HEADER, result)
    return {
        "rows": len(result), "threshold": threshold,
        "calibration_fingerprint_sha256": fingerprint,
        "prediction_processing_ms": round((perf_counter() - start) * 1000, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    split_parser = subparsers.add_parser("split")
    split_parser.add_argument("--processed-dir", type=Path, required=True)
    split_parser.add_argument("--out-dir", type=Path, required=True)
    calibration_parser = subparsers.add_parser("calibrate")
    calibration_parser.add_argument("--split-dir", type=Path, required=True)
    calibration_parser.add_argument("--output", type=Path, required=True)
    prediction_parser = subparsers.add_parser("predict")
    prediction_parser.add_argument("--split-dir", type=Path, required=True)
    prediction_parser.add_argument("--calibration", type=Path, required=True)
    prediction_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "split":
            outcome = split_dataset(args.processed_dir, args.out_dir)
            print(f"PASS: split count={outcome['counts']} run_tag={outcome['run_tag']}")
        elif args.command == "calibrate":
            outcome = calibrate_split(args.split_dir, args.output)
            print(
                "PASS: calibration normal_count=40 "
                f"empirical_fpr={outcome['calibration_empirical_fpr']:.6f} "
                f"threshold={outcome['threshold']:.12g}"
            )
        elif args.command == "predict":
            outcome = predict_test(args.split_dir, args.calibration, args.output)
            print(
                f"PASS: held-out predictions={outcome['rows']} "
                f"fingerprint={outcome['calibration_fingerprint_sha256']}"
            )
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
