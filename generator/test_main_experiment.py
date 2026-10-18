#!/usr/bin/env python3
"""Dry-run catalog and isolated raw-verifier regression tests for main experiment."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from experiment_plan import build_catalog, select_batch, validate_run_tag
from traffic_model import beacon_plan, load_config, normal_plan
from verify_main import paths_for, verify_one


class ExperimentPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()
        cls.catalog = build_catalog(cls.config)

    def test_exact_200_unique_trials(self) -> None:
        self.assertEqual(len(self.catalog), 200)
        self.assertEqual(len({x.trial_id for x in self.catalog}), 200)
        self.assertEqual(Counter(x.category for x in self.catalog),
                         {"beacon": 100, "normal": 100})
        self.assertEqual([t.index for t in self.catalog], list(range(1, 201)))

    def test_plan_boundaries(self) -> None:
        self.assertEqual(self.catalog[0].trial_id, "beacon-j00-t01")
        self.assertEqual(self.catalog[19].trial_id, "beacon-j00-t20")
        self.assertEqual(self.catalog[20].trial_id, "beacon-j10-t01")
        self.assertEqual(self.catalog[99].trial_id, "beacon-j70-t20")
        self.assertEqual(self.catalog[100].trial_id, "normal-interactive-burst-t01")
        self.assertEqual(self.catalog[139].trial_id, "normal-interactive-burst-t40")
        self.assertEqual(self.catalog[140].trial_id, "normal-irregular-lognormal-t01")
        self.assertEqual(self.catalog[169].trial_id, "normal-irregular-lognormal-t30")
        self.assertEqual(self.catalog[170].trial_id, "normal-mixed-activity-t01")
        self.assertEqual(self.catalog[199].trial_id, "normal-mixed-activity-t30")

    def test_paired_beacon_plan(self) -> None:
        for number in (1, 10, 20):
            plans = [beacon_plan(self.config, j, number) for j in (0, 10, 30, 50, 70)]
            self.assertTrue(all(p["normalized_jitter"] == plans[0]["normalized_jitter"]
                                for p in plans))
            self.assertTrue(all(p["payload_profile_sequence"] == plans[0]["payload_profile_sequence"]
                                for p in plans))

    def test_disallowed_tags(self) -> None:
        for tag in ("pilot-v2", "capture-check-v1", "main-v0", "main-v1-pilot",
                    "../main-v1", "main-v1-test", "main-v1/escape", ""):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                validate_run_tag(tag)
        self.assertEqual(validate_run_tag("main-v1"), "main-v1")
        self.assertEqual(validate_run_tag("main-v2"), "main-v2")

    def test_invalid_batches(self) -> None:
        for start, end in ((0, 10), (10, 9), (1, 201), (201, 201)):
            with self.subTest(start=start,end=end), self.assertRaises(ValueError):
                select_batch(self.catalog, start, end)

    def test_boundary_batch(self) -> None:
        batch = select_batch(self.catalog, 98, 102)
        self.assertEqual(len(batch), 5)
        self.assertEqual(batch[2].trial_id, "beacon-j70-t20")
        self.assertEqual(batch[3].trial_id, "normal-interactive-burst-t01")

    def test_plan_cli_tsv(self) -> None:
        program = Path(__file__).with_name("experiment_plan.py")
        completed = subprocess.run([
            sys.executable, str(program), "--start", "99", "--end", "101",
            "--format", "tsv", "--run-tag", "main-v1",
        ], capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rows = completed.stdout.strip().splitlines()
        self.assertEqual(len(rows), 3)
        self.assertTrue(rows[-1].startswith("101\tnormal\tinteractive-burst\t1\t"))

    def test_shell_dry_run_does_not_require_docker(self) -> None:
        script = Path(__file__).resolve().parent.parent / "scripts" / "run-main-experiment.sh"
        completed = subprocess.run(
            ["bash", str(script)],
            env={**os.environ, "RUN_TAG": "main-v1", "START": "1", "END": "2", "EXECUTE": "0"},
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("DRY RUN ONLY", completed.stdout)


class RawVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.raw = Path(self.temp.name) / "raw"
        self.pcap = Path(self.temp.name) / "pcap"
        self.tag = "main-v1"
        self.trial = build_catalog()[0]
        self.config = load_config()
        self.manifest_path, self.csv_path, self.pcap_path = paths_for(
            self.trial, self.tag, self.raw, self.pcap,
        )
        for path in (self.manifest_path, self.csv_path, self.pcap_path):
            path.parent.mkdir(parents=True, exist_ok=True)
        expected = beacon_plan(self.config, 0, 1)
        manifest = {
            **expected,
            "pcap_filename": f"artifacts/pcap/{self.tag}/beacon/{self.trial.trial_id}.pcap",
            "pcap_bytes": 5,
            "pcap_clienthello": {
                "timestamps_epoch": [str(i) for i in range(30)],
                "outer_sni": [self.config["public_name"]] * 30,
            },
        }
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.pcap_path.write_bytes(b"12345")
        with self.csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=("index", "success", "payload_profile"))
            writer.writeheader()
            for i, profile in enumerate(expected["payload_profile_sequence"], 1):
                writer.writerow({"index": i, "success": True, "payload_profile": profile})

    @patch("verify_main.parse_clienthello")
    @patch("verify_main.verify_common")
    def test_consistent_single_trial(self, common, hello) -> None:
        hello.return_value = (
            [str(i) for i in range(30)], [self.config["public_name"]] * 30
        )
        result = verify_one(self.trial, self.tag, self.raw, self.pcap, self.config)
        self.assertEqual(result["trial_id"], self.trial.trial_id)
        common.assert_called_once()
        hello.assert_called_once()

    @patch("verify_main.parse_clienthello")
    @patch("verify_main.verify_common")
    def test_modified_manifest_is_rejected(self, common, hello) -> None:
        doc = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        doc["scheduled_intervals_s"][0] = 0.5
        self.manifest_path.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "deterministic generator field"):
            verify_one(self.trial, self.tag, self.raw, self.pcap, self.config)
        common.assert_not_called()

    def test_missing_pcap_rejected(self) -> None:
        self.pcap_path.unlink()
        with self.assertRaisesRegex(ValueError, "missing PCAP"):
            verify_one(self.trial, self.tag, self.raw, self.pcap, self.config)


if __name__ == "__main__":
    unittest.main(verbosity=2)
