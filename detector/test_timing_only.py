#!/usr/bin/env python3
"""Self-contained tests using invented values, never pilot/final experiment data."""

import math
import unittest
from collections import Counter

from timing_only import (
    BEACON_JITTER_LEVELS,
    calibrate_from_normal,
    checked_cv,
    expected_catalog,
    partition_for_trial,
    predict_iat_cv,
    validate_full_catalog,
)


class TimingOnlyTests(unittest.TestCase):
    def test_strict_boundary(self) -> None:
        self.assertEqual(predict_iat_cv(0.09, 0.1), 1)
        self.assertEqual(predict_iat_cv(0.1, 0.1), 0)
        self.assertEqual(predict_iat_cv(0.11, 0.1), 0)

    def test_normal_calibration_third_order_statistic(self) -> None:
        values = [number / 100 for number in range(1, 41)]
        result = calibrate_from_normal(reversed(values))
        self.assertAlmostEqual(result["threshold"], 0.03)
        self.assertEqual(result["calibration_fp_count"], 2)
        self.assertAlmostEqual(result["calibration_empirical_fpr"], 0.05)

    def test_ties_are_conservative(self) -> None:
        values = [0.1, 0.1, 0.1] + [float(number) for number in range(1, 38)]
        result = calibrate_from_normal(values)
        self.assertEqual(result["threshold"], 0.1)
        self.assertEqual(result["calibration_fp_count"], 0)

    def test_wrong_calibration_count_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calibrate_from_normal([0.2] * 39)

    def test_invalid_cv_rejected(self) -> None:
        for value in (None, "", True, math.nan, math.inf, -0.01):
            with self.subTest(value=value), self.assertRaises(ValueError):
                checked_cv(value)

    def test_paired_jitter_partition_is_identical(self) -> None:
        for trial in range(1, 21):
            assignments = {
                partition_for_trial(f"beacon-j{jitter:02d}-t{trial:02d}")
                for jitter in BEACON_JITTER_LEVELS
            }
            self.assertEqual(len(assignments), 1)

    def test_catalog_expected_counts(self) -> None:
        catalog = expected_catalog()
        self.assertEqual(len(catalog), 200)
        self.assertEqual(Counter(catalog.values()), {"calibration": 90, "test": 110})
        self.assertEqual(validate_full_catalog(catalog), {
            "total": 200,
            "calibration": 90,
            "test": 110,
        })
        normal_calibration = [
            trial_id for trial_id, partition in catalog.items()
            if trial_id.startswith("normal-") and partition == "calibration"
        ]
        self.assertEqual(len(normal_calibration), 40)

    def test_invalid_trial_range_rejected(self) -> None:
        for trial_id in ("beacon-j10-t21", "normal-mixed-activity-t31",
                         "beacon-j99-t01", "normal-interactive-burst-t00"):
            with self.subTest(trial_id=trial_id), self.assertRaises(ValueError):
                partition_for_trial(trial_id)

    def test_missing_and_duplicate_trial_rejected(self) -> None:
        ids = list(expected_catalog())
        with self.assertRaises(ValueError):
            validate_full_catalog(ids[:-1])
        with self.assertRaises(ValueError):
            validate_full_catalog(ids[:-1] + [ids[0]])

    def test_prediction_does_not_require_metadata(self) -> None:
        self.assertEqual(predict_iat_cv("0.07", "0.08"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
