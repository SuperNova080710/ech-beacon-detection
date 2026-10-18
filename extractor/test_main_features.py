#!/usr/bin/env python3
"""Offline main-feature verification tests with fabricated CSV/provenance only."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from extract_features import FEATURE_COLUMNS
from verify_main_features import build_catalog, validate


class FullFeatureValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.tag = "main-v1"
        self.processed = self.base / "processed"
        self.raw = self.base / "raw"
        output = self.processed / self.tag
        output.mkdir(parents=True)
        self.features = output / "features.csv"
        self.labels = output / "labels.csv"
        self.provenance = output / "provenance.json"
        self.catalog = build_catalog()
        with self.features.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["trial_id", *FEATURE_COLUMNS])
            writer.writeheader()
            for trial in self.catalog:
                writer.writerow({"trial_id": trial.trial_id,
                                 **{name: "1.0" for name in FEATURE_COLUMNS}})
        with self.labels.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=["trial_id", "traffic_class", "label", "jitter_pct", "normal_profile"]
            )
            writer.writeheader()
            for trial in self.catalog:
                writer.writerow({
                    "trial_id": trial.trial_id,
                    "traffic_class": trial.category,
                    "label": "1" if trial.category == "beacon" else "0",
                    "jitter_pct": trial.value if trial.category == "beacon" else "",
                    "normal_profile": trial.value if trial.category == "normal" else "",
                })
        records = []
        for trial in self.catalog:
            path = self.raw / self.tag / "manifests" / (trial.trial_id + ".json")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"pcap_sha256": "a" * 64}), encoding="utf-8")
            records.append({
                "trial_id": trial.trial_id,
                "validation_status": "pass",
                "validation_errors": [],
                "flow_count": 30,
                "flow_start_count": 30,
                "iat_count": 29,
                "packet_count": 510,
                "total_extraction_ms": 201.0,
                "source_pcap_sha256": "a" * 64,
                "source_manifest": f"/data/raw/{self.tag}/manifests/{trial.trial_id}.json",
                "source_pcap": f"/pcap/{self.tag}/{trial.category}/{trial.trial_id}.pcap",
            })
        self.provenance.write_text(json.dumps({
            "run_tag": self.tag,
            "extractor_schema_version": 1,
            "feature_definition_version": "1.0.0",
            "feature_columns": FEATURE_COLUMNS,
            "trial_count": 200,
            "validation_status": "pass",
            "failed_trials": [],
            "trials": records,
        }), encoding="utf-8")

    def test_exact_synthetic_catalog_passes(self) -> None:
        validate(self.tag, self.processed, self.raw)

    def test_duplicate_feature_trial_rejected(self) -> None:
        lines = self.features.read_text().splitlines(keepends=True)
        lines[-1] = lines[-2]
        self.features.write_text("".join(lines))
        with self.assertRaisesRegex(ValueError, "duplicate trial IDs"):
            validate(self.tag, self.processed, self.raw)

    def test_nonfinite_feature_rejected(self) -> None:
        lines = self.features.read_text().splitlines(keepends=True)
        lines[1] = lines[1].replace("1.0", "NaN", 1)
        self.features.write_text("".join(lines))
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            validate(self.tag, self.processed, self.raw)

    def test_raw_hash_mismatch_rejected(self) -> None:
        first = self.catalog[0]
        path = self.raw / self.tag / "manifests" / (first.trial_id + ".json")
        path.write_text(json.dumps({"pcap_sha256": "b" * 64}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "processed/raw PCAP hash"):
            validate(self.tag, self.processed, self.raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
