#!/usr/bin/env python3
"""Offline model and CLI tests, using exclusively generated synthetic fixtures."""

from __future__ import annotations

import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from multi_feature import (
    CALIBRATION_COUNT, calibrate_threshold, classify, predict_score, scaler_fit,
    train, vector,
)
from multi_feature_cli import (
    PREDICTION_COLUMNS, predict_test, train_calibration, validate_model,
)
from synthetic_fixture import create_fixture
from timing_only_cli import (
    FEATURE_COLUMNS, FEATURE_HEADER, digest, read_csv, read_json, split_dataset,
    write_json,
)


class MultiFeatureMathTests(unittest.TestCase):
    def test_training_is_deterministic(self) -> None:
        rows = []
        labels = []
        for i in range(CALIBRATION_COUNT):
            row = {name: 1.0 for name in FEATURE_COLUMNS}
            row["iat_cv"] = 0.1 + (i % 40) * 0.03
            row["packet_size_cv"] = 1.0 + (i % 5) * 0.07
            rows.append(row)
            labels.append(0 if i < 40 else 1)
        first = train(rows, labels)
        second = train(rows, labels)
        self.assertEqual(first, second)
        self.assertEqual(len(first["weights"]), 13)
        self.assertTrue(math.isfinite(first["training_regularized_loss"]))

    def test_zero_variance_feature_scale(self) -> None:
        constant = [[5.0] * len(FEATURE_COLUMNS)] * 90
        means, scales = scaler_fit(constant)
        self.assertEqual(means, [5.0] * 13)
        self.assertEqual(scales, [1.0] * 13)

    def test_strict_score_boundary(self) -> None:
        self.assertEqual(classify(1.1, 1.0), 1)
        self.assertEqual(classify(1.0, 1.0), 0)
        self.assertEqual(classify(0.9, 1.0), 0)

    def test_third_largest_threshold(self) -> None:
        output = calibrate_threshold([float(n) for n in range(40)])
        self.assertEqual(output["threshold"], 37)
        self.assertEqual(output["calibration_fp_count"], 2)
        self.assertEqual(output["calibration_empirical_fpr"], 0.05)

    def test_tied_scores_are_conservative(self) -> None:
        output = calibrate_threshold([0.7, 0.7, 0.7] + [0.2] * 37)
        self.assertEqual(output["threshold"], 0.7)
        self.assertEqual(output["calibration_fp_count"], 0)

    def test_wrong_score_count_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calibrate_threshold([0.2] * 39)

    def test_nonfinite_input_rejected(self) -> None:
        for val in (None, "nan", float("inf"), "abc"):
            sample = {name: 0.5 for name in FEATURE_COLUMNS}
            sample["iat_cv"] = val
            with self.subTest(val=val), self.assertRaises(ValueError):
                vector(sample)

    def test_bad_training_size_or_labels_rejected(self) -> None:
        rows = [{name: 1.0 for name in FEATURE_COLUMNS}] * 89
        with self.assertRaisesRegex(ValueError, "90 calibration"):
            train(rows, [0] * 89)
        with self.assertRaisesRegex(ValueError, "40 normal"):
            train(rows + [rows[0]], [0] * 90)

    def test_nonfinite_threshold_rejected(self) -> None:
        with self.assertRaises(ValueError):
            classify(0.1, math.inf)


class MultiFeaturePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.processed = self.base / "synthetic-200-model-test"
        create_fixture(self.processed)
        self.split = self.base / "split"
        split_dataset(self.processed, self.split)

    def test_end_to_end_train_and_predict(self) -> None:
        model_file = self.base / "calibration.json"
        model = train_calibration(self.split, model_file)
        self.assertEqual(model["training_count"], 90)
        self.assertEqual(model["training_normal_count"], 40)
        self.assertEqual(model["training_beacon_count"], 50)
        self.assertEqual(model["feature_columns"], list(FEATURE_COLUMNS))
        self.assertLessEqual(model["calibration_empirical_fpr"], 0.05)
        self.assertTrue(math.isfinite(model["threshold"]))
        predict_path = self.base / "predictions.csv"
        output = predict_test(self.split, model_file, predict_path)
        self.assertEqual(output["rows"], 110)
        rows = read_csv(predict_path, PREDICTION_COLUMNS)
        self.assertEqual(len(rows), 110)
        self.assertFalse("label" in next(iter(rows.values())))

    def test_predict_ignores_test_labels(self) -> None:
        model_path = self.base / "calibration.json"
        train_calibration(self.split, model_path)
        (self.split / "test_labels.csv").unlink()
        result = predict_test(self.split, model_path, self.base / "predictions.csv")
        self.assertEqual(result["rows"], 110)

    def test_train_is_byte_identical_except_clock_metrics(self) -> None:
        first = self.base / "a.json"
        second = self.base / "b.json"
        model_a = train_calibration(self.split, first)
        model_b = train_calibration(self.split, second)
        self.assertEqual(model_a["calibration_fingerprint_sha256"],
                         model_b["calibration_fingerprint_sha256"])
        self.assertEqual(model_a["weights"], model_b["weights"])
        self.assertEqual(model_a["scaler_mean"], model_b["scaler_mean"])
        self.assertEqual(model_a["scaler_scale"], model_b["scaler_scale"])
        self.assertEqual(model_a["threshold"], model_b["threshold"])

    def test_predictions_are_byte_identical(self) -> None:
        model_path = self.base / "calibration.json"
        train_calibration(self.split, model_path)
        a = self.base / "a.csv"
        b = self.base / "b.csv"
        predict_test(self.split, model_path, a)
        predict_test(self.split, model_path, b)
        self.assertEqual(digest(a), digest(b))

    def test_tampered_model_rejected(self) -> None:
        model_path = self.base / "calibration.json"
        train_calibration(self.split, model_path)
        model = read_json(model_path)
        model["weights"][0] = 99999.0
        write_json(model_path, model)
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            predict_test(self.split, model_path, self.base / "predictions.csv")

    def test_tampered_calibration_checksum_rejected(self) -> None:
        model_path = self.base / "calibration.json"
        train_calibration(self.split, model_path)
        path = self.split / "calibration_features.csv"
        path.write_text(path.read_text() + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            validate_model(self.split, read_json(model_path))

    def test_tampered_test_checksum_rejected(self) -> None:
        model_path = self.base / "calibration.json"
        train_calibration(self.split, model_path)
        path = self.split / "test_features.csv"
        path.write_text(path.read_text() + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            predict_test(self.split, model_path, self.base / "predictions.csv")

    def test_refuses_overwriting_model(self) -> None:
        model_path = self.base / "calibration.json"
        train_calibration(self.split, model_path)
        with self.assertRaisesRegex(ValueError, "refusing overwrite"):
            train_calibration(self.split, model_path)

    def test_no_test_data_used_to_fit(self) -> None:
        model_path = self.base / "calibration.json"
        initial_model = train_calibration(self.split, model_path)
        # Removing both test files cannot change the fitted model: training
        # reads only calibration artifacts, and never the held-out partition.
        (self.split / "test_features.csv").unlink()
        (self.split / "test_labels.csv").unlink()
        second_model = train_calibration(self.split, self.base / "second.json")
        self.assertEqual(initial_model["calibration_fingerprint_sha256"],
                         second_model["calibration_fingerprint_sha256"])

    def test_cli_train_and_predict(self) -> None:
        cli = Path(__file__).with_name("multi_feature_cli.py")
        jobs = [
            ["train", "--split-dir", str(self.split), "--output",
             str(self.base / "calibration.json")],
            ["predict", "--split-dir", str(self.split),
             "--calibration", str(self.base / "calibration.json"),
             "--output", str(self.base / "predictions.csv")],
        ]
        for args in jobs:
            with self.subTest(command=args[0]):
                completed = subprocess.run(
                    [sys.executable, str(cli), *args],
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("PASS:", completed.stdout)

    def test_schema_version_rejected(self) -> None:
        model_path = self.base / "calibration.json"
        train_calibration(self.split, model_path)
        model = read_json(model_path)
        model["feature_definition_version"] = "2.0.0"
        write_json(model_path, model)
        with self.assertRaisesRegex(ValueError, "version/feature schema"):
            predict_test(self.split, model_path, self.base / "predictions.csv")


if __name__ == "__main__":
    unittest.main(verbosity=2)
