#!/usr/bin/env python3

import math
import unittest

from feature_math import (
    burst_features,
    directionality_features,
    packet_size_features,
    timing_features,
    validate_feature_values,
)


class FeatureMathTests(unittest.TestCase):
    def test_timing_features_constant_iat(self) -> None:
        result = timing_features([0.0, 1.0, 2.0, 3.0])
        self.assertEqual(result["iat_mean_s"], 1.0)
        self.assertEqual(result["iat_std_s"], 0.0)
        self.assertEqual(result["iat_cv"], 0.0)
        self.assertEqual(result["iat_mad_s"], 0.0)

    def test_packet_size_uses_population_std(self) -> None:
        result = packet_size_features([100.0, 200.0, 300.0])
        self.assertEqual(result["packet_size_mean_bytes"], 200.0)
        self.assertAlmostEqual(result["packet_size_std_bytes"], math.sqrt(20000.0 / 3.0))
        self.assertAlmostEqual(
            result["packet_size_cv"],
            math.sqrt(20000.0 / 3.0) / 200.0,
        )

    def test_directionality_formulas(self) -> None:
        result = directionality_features(
            ["out", "in", "in", "out"],
            [100.0, 200.0, 300.0, 400.0],
        )
        self.assertEqual(result["out_in_packet_ratio"], 1.0)
        self.assertEqual(result["byte_asymmetry"], 0.0)
        self.assertAlmostEqual(result["direction_change_ratio"], 2.0 / 3.0)

    def test_burst_threshold_is_inclusive(self) -> None:
        result = burst_features([0.0, 0.2, 1.0, 1.5, 2.3], 0.5)
        self.assertEqual(result["burst_count"], 3)
        self.assertAlmostEqual(result["burst_mean_size"], 5.0 / 3.0)
        self.assertIsNotNone(result["burst_interval_cv"])

    def test_missing_direction_denominator_is_reported(self) -> None:
        result = directionality_features(["out", "out"], [100.0, 100.0])
        errors = validate_feature_values(result)
        self.assertIn("out_in_packet_ratio:missing", errors)

    def test_nonfinite_is_reported(self) -> None:
        errors = validate_feature_values({"x": float("inf")})
        self.assertEqual(errors, ["x:non_finite"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
