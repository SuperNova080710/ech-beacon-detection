#!/usr/bin/env python3
"""Train the frozen multi-feature model and predict without reading test labels."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from time import perf_counter

from multi_feature import (
    CALIBRATION_COUNT,
    EPOCHS,
    FEATURE_DEFINITION_VERSION,
    L2_LAMBDA,
    LEARNING_RATE,
    MODEL_VERSION,
    NORMAL_CALIBRATION_COUNT,
    calibrate_threshold,
    classify,
    predict_score,
    train,
)
from timing_only import expected_catalog
from timing_only_cli import (
    FEATURE_COLUMNS,
    FEATURE_HEADER,
    LABEL_HEADER,
    canonical_sha,
    check_features,
    check_hash,
    check_label,
    digest,
    read_csv,
    read_json,
    utc_now,
    validate_split_manifest,
    write_csv,
    write_json,
)

PREDICTION_COLUMNS = (
    "trial_id",
    "multi_feature_logit",
    "prediction",
    "detector_version",
    "calibration_fingerprint_sha256",
)

MODEL_FINGERPRINT_FIELDS = (
    "model_version",
    "feature_definition_version",
    "feature_columns",
    "optimizer",
    "learning_rate",
    "epochs",
    "l2_lambda",
    "score",
    "comparison",
    "training_count",
    "training_normal_count",
    "training_beacon_count",
    "scaler_mean",
    "scaler_scale",
    "weights",
    "intercept",
    "training_regularized_loss",
    "threshold",
    "calibration_normal_logits_desc",
    "calibration_fp_count",
    "calibration_empirical_fpr",
    "target_calibration_fpr",
    "calibration_trial_ids",
    "calibration_features_sha256",
    "calibration_labels_sha256",
    "split_manifest_sha256",
)


def fingerprint_core(model: dict) -> dict:
    return {key: model[key] for key in MODEL_FINGERPRINT_FIELDS}


def frozen_params_ok(model: dict) -> None:
    if (model.get("model_version") != MODEL_VERSION or
        model.get("feature_definition_version") != FEATURE_DEFINITION_VERSION or
        model.get("feature_columns") != list(FEATURE_COLUMNS)):
        raise ValueError("model or extractor version/feature schema mismatch")
    expected = {
        "learning_rate": LEARNING_RATE,
        "epochs": EPOCHS,
        "l2_lambda": L2_LAMBDA,
        "optimizer": "deterministic_full_batch_gradient_descent",
        "score": "linear_logit",
        "comparison": ">",
        "training_count": CALIBRATION_COUNT,
        "training_normal_count": 40,
        "training_beacon_count": 50,
        "target_calibration_fpr": 0.05,
    }
    for key, value in expected.items():
        if model.get(key) != value:
            raise ValueError(f"frozen policy mismatch: {key}")
    for key in ("scaler_mean", "scaler_scale", "weights"):
        values = model.get(key)
        if (not isinstance(values, list) or len(values) != len(FEATURE_COLUMNS) or
            any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                not math.isfinite(v) for v in values)):
            raise ValueError(f"invalid model numeric vector: {key}")
    if any(scale <= 0 for scale in model["scaler_scale"]):
        raise ValueError("non-positive scaler value")
    for key in ("intercept", "training_regularized_loss", "threshold"):
        value = model.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"invalid model numeric scalar: {key}")
    if model["training_regularized_loss"] < 0:
        raise ValueError("negative training loss")


def validate_model(split_dir: Path, model: dict) -> None:
    frozen_params_ok(model)
    if model.get("calibration_fingerprint_sha256") != canonical_sha(fingerprint_core(model)):
        raise ValueError("calibration fingerprint mismatch")
    manifest = validate_split_manifest(split_dir)
    # Re-hash the current calibration inputs rather than trusting manifest text alone.
    check_hash(split_dir, manifest, "calibration_features")
    check_hash(split_dir, manifest, "calibration_labels")
    if model.get("split_manifest_sha256") != digest(split_dir / "split_manifest.json"):
        raise ValueError("calibration split checksum mismatch")
    for file_key, model_key in (
        ("calibration_features", "calibration_features_sha256"),
        ("calibration_labels", "calibration_labels_sha256"),
    ):
        if model.get(model_key) != manifest["file_sha256"][file_key]:
            raise ValueError(f"{file_key} checksum mismatch")
    expected_ids = sorted(
        trial_id for trial_id, part in expected_catalog().items()
        if part == "calibration"
    )
    if model.get("calibration_trial_ids") != expected_ids:
        raise ValueError("calibration membership mismatch")
    scores = model.get("calibration_normal_logits_desc")
    if (not isinstance(scores, list) or
        len(scores) != NORMAL_CALIBRATION_COUNT or
        any(isinstance(s, bool) or not isinstance(s, (int, float)) or not math.isfinite(s)
            for s in scores)):
        raise ValueError("invalid calibration normal scores")
    expected_threshold = calibrate_threshold(scores)
    for key in (
        "threshold", "calibration_normal_logits_desc", "calibration_fp_count",
        "calibration_empirical_fpr",
    ):
        if model.get(key) != expected_threshold[key]:
            raise ValueError(f"threshold calibration rule mismatch: {key}")


def train_calibration(split_dir: Path, output_path: Path) -> dict:
    """Uses calibration-only training features/labels and normal logits for threshold."""
    if output_path.exists():
        raise ValueError(f"refusing overwrite: {output_path}")
    started = perf_counter()
    manifest = validate_split_manifest(split_dir)
    feature_file = check_hash(split_dir, manifest, "calibration_features")
    label_file = check_hash(split_dir, manifest, "calibration_labels")
    features = read_csv(feature_file, FEATURE_HEADER)
    labels = read_csv(label_file, LABEL_HEADER)
    calibration_ids = sorted(
        trial_id for trial_id, part in expected_catalog().items()
        if part == "calibration"
    )
    if set(features) != set(calibration_ids) or set(labels) != set(calibration_ids):
        raise ValueError("calibration membership mismatch")
    check_features(features)
    for trial_id in calibration_ids:
        check_label(trial_id, labels[trial_id])
    numeric_labels = [int(labels[i]["label"]) for i in calibration_ids]
    model = train([features[i] for i in calibration_ids], numeric_labels)
    normal_ids = [i for i in calibration_ids if i.startswith("normal-")]
    normal_logits = [predict_score(features[i], model) for i in normal_ids]
    model.update(calibrate_threshold(normal_logits))
    model.update({
        "calibration_trial_ids": calibration_ids,
        "calibration_features_sha256": digest(feature_file),
        "calibration_labels_sha256": digest(label_file),
        "split_manifest_sha256": digest(split_dir / "split_manifest.json"),
    })
    model["calibration_fingerprint_sha256"] = canonical_sha(fingerprint_core(model))
    model["calibrated_at_utc"] = utc_now()
    model["training_and_calibration_ms"] = round(
        (perf_counter() - started) * 1000, 6
    )
    validate_model(split_dir, model)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(output_path, model)
    return model


def predict_test(split_dir: Path, model_path: Path, output_path: Path) -> dict:
    """Read test_features.csv only; never reads test_labels.csv."""
    if output_path.exists():
        raise ValueError(f"refusing overwrite: {output_path}")
    start = perf_counter()
    manifest = validate_split_manifest(split_dir)
    model = read_json(model_path)
    validate_model(split_dir, model)
    feature_file = check_hash(split_dir, manifest, "test_features")
    rows = read_csv(feature_file, FEATURE_HEADER)
    expected_ids = sorted(
        trial_id for trial_id, part in expected_catalog().items()
        if part == "test"
    )
    if set(rows) != set(expected_ids):
        raise ValueError("test membership mismatch")
    check_features(rows)
    predictions = {}
    for trial_id in expected_ids:
        score = predict_score(rows[trial_id], model)
        predictions[trial_id] = {
            "trial_id": trial_id,
            "multi_feature_logit": score,
            "prediction": classify(score, float(model["threshold"])),
            "detector_version": MODEL_VERSION,
            "calibration_fingerprint_sha256": model["calibration_fingerprint_sha256"],
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(output_path, PREDICTION_COLUMNS, predictions)
    return {
        "rows": len(predictions),
        "fingerprint": model["calibration_fingerprint_sha256"],
        "prediction_processing_ms": round((perf_counter() - start) * 1000, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    train_parser = subs.add_parser("train")
    train_parser.add_argument("--split-dir", type=Path, required=True)
    train_parser.add_argument("--output", type=Path, required=True)
    predict_parser = subs.add_parser("predict")
    predict_parser.add_argument("--split-dir", type=Path, required=True)
    predict_parser.add_argument("--calibration", type=Path, required=True)
    predict_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "train":
            model = train_calibration(args.split_dir, args.output)
            print("PASS: 90-sample calibration trained; "
                  f"normal_count=40, in_sample_fpr={model['calibration_empirical_fpr']:.6f}")
            print(f"CALIBRATION_FINGERPRINT={model['calibration_fingerprint_sha256']}")
        else:
            output = predict_test(args.split_dir, args.calibration, args.output)
            print(f"PASS: held-out predictions={output['rows']}")
            print(f"CALIBRATION_FINGERPRINT={output['fingerprint']}")
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
