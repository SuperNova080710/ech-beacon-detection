#!/usr/bin/env python3
"""Frozen v1 timing-only beacon baseline; no labels enter inference."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable

DETECTOR_VERSION = "1.0.0"
FEATURE_DEFINITION_VERSION = "1.0.0"
SCORE_FEATURE = "iat_cv"
TARGET_CALIBRATION_FPR = 0.05
NORMAL_CALIBRATION_COUNT = 40

BEACON_JITTER_LEVELS = (0, 10, 30, 50, 70)
NORMAL_CONFIG = {
    "interactive-burst": (40, 16),
    "irregular-lognormal": (30, 12),
    "mixed-activity": (30, 12),
}
_BEACON_ID = re.compile(r"beacon-j(00|10|30|50|70)-t(\d{2})\Z")
_NORMAL_ID = re.compile(
    r"normal-(interactive-burst|irregular-lognormal|mixed-activity)-t(\d{2})\Z"
)


def checked_cv(value: object) -> float:
    """Reject missing, negative and non-finite CV instead of imputing a value."""
    if isinstance(value, bool) or value is None:
        raise ValueError("iat_cv must be a finite non-negative number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("iat_cv must be a finite non-negative number") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise ValueError("iat_cv must be a finite non-negative number")
    return parsed


def predict_iat_cv(iat_cv: object, threshold: object) -> int:
    """No label, jitter, profile or trial ID is supplied to the predictor."""
    score = checked_cv(iat_cv)
    cutoff = checked_cv(threshold)
    return int(score < cutoff)


def calibrate_from_normal(normal_cv: Iterable[object]) -> dict[str, object]:
    """The strict x_(3) rule bounds *calibration* FPR to 2/40."""
    values = [checked_cv(item) for item in normal_cv]
    if len(values) != NORMAL_CALIBRATION_COUNT:
        raise ValueError(
            f"expected exactly {NORMAL_CALIBRATION_COUNT} normal calibration CVs, "
            f"got {len(values)}"
        )
    ordered = sorted(values)
    threshold = ordered[2]
    false_positives = sum(value < threshold for value in values)
    assert false_positives <= 2
    return {
        "detector_version": DETECTOR_VERSION,
        "feature_definition_version": FEATURE_DEFINITION_VERSION,
        "score_feature": SCORE_FEATURE,
        "comparison": "<",
        "target_calibration_fpr": TARGET_CALIBRATION_FPR,
        "normal_calibration_count": len(values),
        "threshold": threshold,
        "calibration_fp_count": false_positives,
        "calibration_empirical_fpr": false_positives / len(values),
        "normal_calibration_cv_sorted": ordered,
    }


def expected_catalog() -> dict[str, str]:
    """Exactly 200 predeclared trial IDs; one partition per entire beacon trial."""
    result: dict[str, str] = {}
    for jitter in BEACON_JITTER_LEVELS:
        for trial in range(1, 21):
            result[f"beacon-j{jitter:02d}-t{trial:02d}"] = (
                "calibration" if trial <= 10 else "test"
            )
    for profile, (max_trial, calib_max) in NORMAL_CONFIG.items():
        for trial in range(1, max_trial + 1):
            result[f"normal-{profile}-t{trial:02d}"] = (
                "calibration" if trial <= calib_max else "test"
            )
    return result


def partition_for_trial(trial_id: str) -> str:
    """Only dataset partitioning uses IDs; prediction never uses identifiers."""
    if not isinstance(trial_id, str):
        raise ValueError("trial_id must be a string")
    beacon_match = _BEACON_ID.fullmatch(trial_id)
    if beacon_match:
        trial = int(beacon_match.group(2))
        if not 1 <= trial <= 20:
            raise ValueError("beacon trial outside 1..20")
        return "calibration" if trial <= 10 else "test"
    normal_match = _NORMAL_ID.fullmatch(trial_id)
    if normal_match:
        profile = normal_match.group(1)
        trial = int(normal_match.group(2))
        max_trial, calibration_max = NORMAL_CONFIG[profile]
        if not 1 <= trial <= max_trial:
            raise ValueError("normal trial outside configured range")
        return "calibration" if trial <= calibration_max else "test"
    raise ValueError(f"unexpected trial_id: {trial_id!r}")


def validate_full_catalog(trial_ids: Iterable[str]) -> dict[str, int]:
    """Fail closed on missing, extra or duplicate trial IDs."""
    provided = list(trial_ids)
    expected = expected_catalog()
    if len(provided) != len(set(provided)):
        raise ValueError("duplicate trial_id")
    missing = set(expected) - set(provided)
    extra = set(provided) - set(expected)
    if missing or extra:
        raise ValueError(
            f"dataset catalog mismatch: missing={len(missing)}, extra={len(extra)}"
        )
    if len(provided) != 200:
        raise ValueError(f"expected exactly 200 trials, got {len(provided)}")
    calibration = sum(part == "calibration" for part in expected.values())
    test = sum(part == "test" for part in expected.values())
    assert (calibration, test) == (90, 110)
    return {"total": 200, "calibration": calibration, "test": test}
