#!/usr/bin/env python3
"""Test-only synthetic dataset, never samples or copies pilot experiments."""

from __future__ import annotations

from pathlib import Path

from timing_only import expected_catalog
from timing_only_cli import (
    FEATURE_COLUMNS, FEATURE_HEADER, LABEL_HEADER, write_csv, write_json,
)


def create_fixture(processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True, exist_ok=False)
    features = {}
    labels = {}
    ids = sorted(expected_catalog())
    for i, trial_id in enumerate(ids):
        # Different classes and profiles have varied mock values, not real data.
        is_beacon = trial_id.startswith("beacon-")
        feature = {name: str((i % 19) + 0.25) for name in FEATURE_COLUMNS}
        feature.update({
            "trial_id": trial_id,
            "iat_cv": str(0.07 + (i % 23) * 0.025 + (0 if is_beacon else 0.20)),
            "iat_mean_s": str(0.5 + (i % 13) * 0.11),
            "packet_size_mean_bytes": str(350 + (i % 17) * 9),
            "byte_asymmetry": str(-0.5 + (i % 17) * 0.03),
            "out_in_packet_ratio": str(0.9 + (i % 5) * 0.02),
            "burst_count": str(4 + (i % 20)),
            "burst_mean_size": str(1 + (i % 4)),
            "burst_interval_cv": str(0.1 + (i % 13) * 0.05),
        })
        features[trial_id] = feature
        if is_beacon:
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
    write_csv(processed_dir / "features.csv", FEATURE_HEADER, features)
    write_csv(processed_dir / "labels.csv", LABEL_HEADER, labels)
    write_json(processed_dir / "provenance.json", {
        "extractor_schema_version": 1,
        "feature_definition_version": "1.0.0",
        "validation_status": "pass",
        "run_tag": processed_dir.name,
        "trial_count": 200,
        "trials": [
            {"trial_id": trial_id, "validation_status": "pass"}
            for trial_id in ids
        ],
    })
