#!/usr/bin/env python3
"""Offline synthetic end-to-end tests. Never reads pilot or final experiment data."""

import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from timing_only import expected_catalog
from timing_only_cli import (
    FEATURE_COLUMNS,
    FEATURE_HEADER,
    LABEL_HEADER,
    PREDICTION_HEADER,
    calibrate_split,
    digest,
    predict_test,
    read_csv,
    read_json,
    split_dataset,
    write_csv,
    write_json,
)


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.processed = self.base / "experiment-synthetic-fixture"
        self.processed.mkdir()
        catalog = expected_catalog()
        features = {}
        labels = {}
        for i, trial_id in enumerate(sorted(catalog)):
            cv = (i + 1) / 1000.0
            feature = {name: "1.0" for name in FEATURE_COLUMNS}
            feature.update({
                "trial_id": trial_id,
                "iat_cv": str(cv),
                "packet_size_mean_bytes": "400",
                "byte_asymmetry": "-0.2",
                "burst_count": "20",
            })
            features[trial_id] = feature
            if trial_id.startswith("beacon-"):
                jitter = int(trial_id.split("-")[1][1:])
                labels[trial_id] = {
                    "trial_id": trial_id, "traffic_class": "beacon", "label": "1",
                    "jitter_pct": str(jitter), "normal_profile": "",
                }
            else:
                profile = trial_id.removeprefix("normal-").rsplit("-t", 1)[0]
                labels[trial_id] = {
                    "trial_id": trial_id, "traffic_class": "normal", "label": "0",
                    "jitter_pct": "", "normal_profile": profile,
                }
        write_csv(self.processed / "features.csv", FEATURE_HEADER, features)
        write_csv(self.processed / "labels.csv", LABEL_HEADER, labels)
        write_json(self.processed / "provenance.json", {
            "extractor_schema_version": 1,
            "feature_definition_version": "1.0.0",
            "validation_status": "pass",
            "run_tag": self.processed.name,
            "trial_count": 200,
            "trials": [
                {"trial_id": trial_id, "validation_status": "pass"}
                for trial_id in sorted(catalog)
            ],
        })
        self.split_dir = self.base / "splits"

    def prepare(self) -> dict:
        return split_dataset(self.processed, self.split_dir)

    def test_split_counts_and_label_separation(self) -> None:
        manifest = self.prepare()
        self.assertEqual(manifest["counts"], {
            "calibration": 90, "test": 110, "total": 200,
        })
        calibration = read_csv(
            self.split_dir / "calibration_features.csv", FEATURE_HEADER
        )
        held_out = read_csv(self.split_dir / "test_features.csv", FEATURE_HEADER)
        self.assertEqual(len(calibration), 90)
        self.assertEqual(len(held_out), 110)
        self.assertFalse(set(calibration) & set(held_out))
        self.assertNotIn("traffic_class", calibration[next(iter(calibration))])
        for name, filename in (
            ("calibration_features", "calibration_features.csv"),
            ("test_features", "test_features.csv"),
        ):
            self.assertEqual(manifest["file_sha256"][name], digest(self.split_dir / filename))

    def test_calibration_uses_only_calibration_normal(self) -> None:
        self.prepare()
        output = self.base / "calibration.json"
        model = calibrate_split(self.split_dir, output)
        self.assertEqual(model["normal_calibration_count"], 40)
        self.assertLessEqual(model["calibration_empirical_fpr"], 0.05)
        self.assertEqual(
            model["threshold"], sorted(model["normal_calibration_cv_sorted"])[2]
        )
        self.assertEqual(model["normal_calibration_trial_ids"], sorted(
            trial_id for trial_id, partition in expected_catalog().items()
            if trial_id.startswith("normal-") and partition == "calibration"
        ))
        self.assertEqual(model["calibration_fingerprint_sha256"],
                         read_json(output)["calibration_fingerprint_sha256"])

    def test_prediction_does_not_read_test_labels(self) -> None:
        self.prepare()
        model_file = self.base / "calibration.json"
        calibrate_split(self.split_dir, model_file)
        (self.split_dir / "test_labels.csv").unlink()
        output = self.base / "predictions.csv"
        result = predict_test(self.split_dir, model_file, output)
        self.assertEqual(result["rows"], 110)
        rows = read_csv(output, PREDICTION_HEADER)
        self.assertEqual(len(rows), 110)
        self.assertTrue(all(row["prediction"] in ("0", "1") for row in rows.values()))
        self.assertNotIn("label", next(iter(rows.values())))

    def test_prediction_byte_identical(self) -> None:
        self.prepare()
        model_file = self.base / "calibration.json"
        calibrate_split(self.split_dir, model_file)
        a = self.base / "predictions-a.csv"
        b = self.base / "predictions-b.csv"
        predict_test(self.split_dir, model_file, a)
        predict_test(self.split_dir, model_file, b)
        self.assertEqual(digest(a), digest(b))

    def test_bad_calibration_checksum_rejected(self) -> None:
        self.prepare()
        path = self.split_dir / "calibration_features.csv"
        path.write_text(path.read_text() + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            calibrate_split(self.split_dir, self.base / "calibration.json")

    def test_bad_test_checksum_rejected(self) -> None:
        self.prepare()
        model_file = self.base / "calibration.json"
        calibrate_split(self.split_dir, model_file)
        path = self.split_dir / "test_features.csv"
        path.write_text(path.read_text() + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            predict_test(self.split_dir, model_file, self.base / "predictions.csv")

    def test_tampered_threshold_rejected(self) -> None:
        self.prepare()
        model_file = self.base / "calibration.json"
        calibrate_split(self.split_dir, model_file)
        model = read_json(model_file)
        model["threshold"] = 5.0
        write_json(model_file, model)
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            predict_test(self.split_dir, model_file, self.base / "predictions.csv")

    def test_wrong_label_rejected(self) -> None:
        label_path = self.processed / "labels.csv"
        rows = read_csv(label_path, LABEL_HEADER)
        rows["beacon-j00-t01"]["label"] = "0"
        write_csv(label_path, LABEL_HEADER, rows)
        with self.assertRaisesRegex(ValueError, "invalid beacon label"):
            self.prepare()

    def test_pilot_rejected(self) -> None:
        renamed = self.base / "pilot-v2"
        self.processed.rename(renamed)
        provenance_path = renamed / "provenance.json"
        provenance = read_json(provenance_path)
        provenance["run_tag"] = renamed.name
        write_json(provenance_path, provenance)
        with self.assertRaisesRegex(ValueError, "pilot/diagnostic"):
            split_dataset(renamed, self.split_dir)

    def test_provenance_version_mismatch_rejected(self) -> None:
        path = self.processed / "provenance.json"
        prov = read_json(path)
        prov["feature_definition_version"] = "9.9.9"
        write_json(path, prov)
        with self.assertRaisesRegex(ValueError, "schema validation failed"):
            self.prepare()

    def test_split_refuses_overwrite(self) -> None:
        self.prepare()
        with self.assertRaisesRegex(ValueError, "refusing overwrite"):
            self.prepare()

    def test_incomplete_catalog_rejected(self) -> None:
        path = self.processed / "features.csv"
        rows = read_csv(path, FEATURE_HEADER)
        rows.pop(next(iter(rows)))
        write_csv(path, FEATURE_HEADER, rows)
        with self.assertRaisesRegex(ValueError, "catalog mismatch"):
            self.prepare()

    def test_cli_split_and_calibration_and_prediction(self) -> None:
        cli = Path(__file__).with_name("timing_only_cli.py")
        commands = [
            ["split", "--processed-dir", str(self.processed),
             "--out-dir", str(self.split_dir)],
            ["calibrate", "--split-dir", str(self.split_dir),
             "--output", str(self.base / "calibration.json")],
            ["predict", "--split-dir", str(self.split_dir),
             "--calibration", str(self.base / "calibration.json"),
             "--output", str(self.base / "predictions.csv")],
        ]
        for args in commands:
            with self.subTest(command=args[0]):
                completed = subprocess.run(
                    [sys.executable, str(cli), *args], text=True,
                    capture_output=True, check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("PASS:", completed.stdout)
        self.assertTrue((self.base / "predictions.csv").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
