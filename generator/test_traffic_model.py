#!/usr/bin/env python3

import unittest
from pathlib import Path

from traffic_model import beacon_plan, load_config, normal_plan, payload_sequence


class TrafficModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(Path(__file__).with_name("config.json"))

    def test_beacon_zero_jitter_is_exactly_one_second(self):
        plan = beacon_plan(self.config, 0, 1)
        self.assertEqual(len(plan["scheduled_intervals_s"]), 29)
        self.assertTrue(all(value == 1.0 for value in plan["scheduled_intervals_s"]))

    def test_beacon_jitter_levels_share_normalized_vector_and_payloads(self):
        plans = [beacon_plan(self.config, jitter, 7) for jitter in (0, 10, 30, 50, 70)]
        normalized = plans[0]["normalized_jitter"]
        payloads = plans[0]["payload_profile_sequence"]
        for plan in plans[1:]:
            self.assertEqual(plan["normalized_jitter"], normalized)
            self.assertEqual(plan["payload_profile_sequence"], payloads)

    def test_beacon_jitter_ranges(self):
        base = float(self.config["beacon"]["base_interval_s"])
        for jitter in (0, 10, 30, 50, 70):
            plan = beacon_plan(self.config, jitter, 20)
            ratio = jitter / 100.0
            low = base * (1.0 - ratio)
            high = base * (1.0 + ratio)
            self.assertTrue(all(low <= value <= high for value in plan["scheduled_intervals_s"]))

    def test_beacon_plan_is_deterministic(self):
        self.assertEqual(beacon_plan(self.config, 50, 3), beacon_plan(self.config, 50, 3))

    def test_normal_plans_are_deterministic_and_have_29_intervals(self):
        for name in self.config["normal"]["profiles"]:
            first = normal_plan(self.config, name, 1)
            second = normal_plan(self.config, name, 1)
            self.assertEqual(first, second)
            self.assertEqual(len(first["scheduled_intervals_s"]), 29)

    def test_interactive_burst_intervals_fit_declared_ranges(self):
        profile = self.config["normal"]["profiles"]["interactive-burst"]
        plan = normal_plan(self.config, "interactive-burst", 1)
        for value in plan["scheduled_intervals_s"]:
            short = float(profile["intra_min_s"]) <= value <= float(profile["intra_max_s"])
            idle = float(profile["idle_min_s"]) <= value <= float(profile["idle_max_s"])
            self.assertTrue(short or idle)

    def test_lognormal_is_clipped(self):
        profile = self.config["normal"]["profiles"]["irregular-lognormal"]
        plan = normal_plan(self.config, "irregular-lognormal", 30)
        self.assertTrue(
            all(
                float(profile["clip_min_s"]) <= value <= float(profile["clip_max_s"])
                for value in plan["scheduled_intervals_s"]
            )
        )

    def test_mixed_activity_uses_only_declared_ranges(self):
        profile = self.config["normal"]["profiles"]["mixed-activity"]
        plan = normal_plan(self.config, "mixed-activity", 1)
        for value in plan["scheduled_intervals_s"]:
            short = float(profile["short_min_s"]) <= value <= float(profile["short_max_s"])
            idle = float(profile["idle_min_s"]) <= value <= float(profile["idle_max_s"])
            self.assertTrue(short or idle)

    def test_payload_sequence_uses_valid_profiles(self):
        sequence = payload_sequence(self.config, 1234, 100)
        self.assertEqual(len(sequence), 100)
        self.assertTrue(set(sequence).issubset({"small", "medium", "large"}))

    def test_payload_files_match_declared_response_sizes(self):
        payload_dir = Path(__file__).with_name("payloads")
        for name, profile in self.config["payload_profiles"].items():
            self.assertEqual((payload_dir / f"{name}.bin").stat().st_size, int(profile["response_bytes"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
