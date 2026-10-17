#!/usr/bin/env python3
"""Deterministic traffic-plan generation for the T10 Native ECH experiment."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path(__file__).with_name("config.json")
PAYLOAD_ORDER = ("small", "medium", "large")


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if int(config["request_count"]) < 2:
        raise ValueError("request_count must be >= 2")

    payloads = config["payload_profiles"]
    if tuple(payloads.keys()) != PAYLOAD_ORDER:
        raise ValueError(f"payload profile order must be {PAYLOAD_ORDER}")

    probability_sum = sum(float(payloads[name]["probability"]) for name in PAYLOAD_ORDER)
    if not math.isclose(probability_sum, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("payload probabilities must sum to 1.0")


def _round(value: float) -> float:
    return round(value, 9)


def _uniform(rng: random.Random, low: float, high: float) -> float:
    return low + (high - low) * rng.random()


def _randint(rng: random.Random, low: int, high: int) -> int:
    return low + int(rng.random() * (high - low + 1))


def _standard_normal(rng: random.Random) -> float:
    """Box-Muller transform using only Random.random() for reproducibility."""
    u1 = max(rng.random(), 1e-15)
    u2 = rng.random()
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def payload_sequence(config: dict[str, Any], seed: int, count: int) -> list[str]:
    rng = random.Random(seed)
    thresholds: list[tuple[float, str]] = []
    cumulative = 0.0
    for name in PAYLOAD_ORDER:
        cumulative += float(config["payload_profiles"][name]["probability"])
        thresholds.append((cumulative, name))

    result: list[str] = []
    for _ in range(count):
        value = rng.random()
        selected = PAYLOAD_ORDER[-1]
        for threshold, name in thresholds:
            if value < threshold:
                selected = name
                break
        result.append(selected)
    return result


def beacon_plan(config: dict[str, Any], jitter_pct: int, trial: int) -> dict[str, Any]:
    beacon = config["beacon"]
    allowed = [int(value) for value in beacon["jitter_pct"]]
    if jitter_pct not in allowed:
        raise ValueError(f"jitter_pct must be one of {allowed}")
    if not 1 <= trial <= int(beacon["trials_per_level"]):
        raise ValueError("beacon trial is outside configured range")

    request_count = int(config["request_count"])
    timing_seed = int(beacon["timing_seed_base"]) + trial
    payload_seed = int(beacon["payload_seed_base"]) + trial
    timing_rng = random.Random(timing_seed)

    normalized = [_round(2.0 * timing_rng.random() - 1.0) for _ in range(request_count - 1)]
    jitter_ratio = jitter_pct / 100.0
    base_interval = float(beacon["base_interval_s"])
    intervals = [_round(base_interval * (1.0 + jitter_ratio * value)) for value in normalized]

    return {
        "trial_id": f"beacon-j{jitter_pct:02d}-t{trial:02d}",
        "traffic_class": "beacon",
        "normal_profile": None,
        "trial_number": trial,
        "jitter_pct": jitter_pct,
        "base_interval_s": base_interval,
        "request_count": request_count,
        "timing_seed": timing_seed,
        "payload_seed": payload_seed,
        "normalized_jitter": normalized,
        "scheduled_intervals_s": intervals,
        "payload_profile_sequence": payload_sequence(config, payload_seed, request_count),
    }


def _interactive_burst_intervals(rng: random.Random, profile: dict[str, Any], count: int) -> list[float]:
    intervals: list[float] = []
    remaining = _randint(rng, int(profile["burst_size_min"]), int(profile["burst_size_max"]))

    for _ in range(count - 1):
        if remaining > 1:
            value = _uniform(rng, float(profile["intra_min_s"]), float(profile["intra_max_s"]))
            remaining -= 1
        else:
            value = _uniform(rng, float(profile["idle_min_s"]), float(profile["idle_max_s"]))
            remaining = _randint(rng, int(profile["burst_size_min"]), int(profile["burst_size_max"]))
        intervals.append(_round(value))
    return intervals


def _lognormal_intervals(rng: random.Random, profile: dict[str, Any], count: int) -> list[float]:
    result: list[float] = []
    mu = float(profile["mu"])
    sigma = float(profile["sigma"])
    low = float(profile["clip_min_s"])
    high = float(profile["clip_max_s"])

    for _ in range(count - 1):
        value = math.exp(mu + sigma * _standard_normal(rng))
        result.append(_round(min(high, max(low, value))))
    return result


def _mixed_intervals(rng: random.Random, profile: dict[str, Any], count: int) -> list[float]:
    result: list[float] = []
    short_probability = float(profile["short_probability"])

    for _ in range(count - 1):
        if rng.random() < short_probability:
            value = _uniform(rng, float(profile["short_min_s"]), float(profile["short_max_s"]))
        else:
            value = _uniform(rng, float(profile["idle_min_s"]), float(profile["idle_max_s"]))
        result.append(_round(value))
    return result


def normal_plan(config: dict[str, Any], profile_name: str, trial: int) -> dict[str, Any]:
    normal = config["normal"]
    profiles = normal["profiles"]
    if profile_name not in profiles:
        raise ValueError(f"unknown normal profile: {profile_name}")

    profile = profiles[profile_name]
    if not 1 <= trial <= int(profile["samples"]):
        raise ValueError("normal trial is outside configured profile range")

    request_count = int(config["request_count"])
    seed_offset = int(profile["seed_offset"])
    timing_seed = int(normal["timing_seed_base"]) + seed_offset + trial
    payload_seed = int(normal["payload_seed_base"]) + seed_offset + trial
    rng = random.Random(timing_seed)

    if profile_name == "interactive-burst":
        intervals = _interactive_burst_intervals(rng, profile, request_count)
    elif profile_name == "irregular-lognormal":
        intervals = _lognormal_intervals(rng, profile, request_count)
    elif profile_name == "mixed-activity":
        intervals = _mixed_intervals(rng, profile, request_count)
    else:
        raise ValueError(f"unsupported normal profile: {profile_name}")

    return {
        "trial_id": f"normal-{profile_name}-t{trial:02d}",
        "traffic_class": "normal",
        "normal_profile": profile_name,
        "trial_number": trial,
        "jitter_pct": None,
        "base_interval_s": None,
        "request_count": request_count,
        "timing_seed": timing_seed,
        "payload_seed": payload_seed,
        "normalized_jitter": None,
        "scheduled_intervals_s": intervals,
        "payload_profile_sequence": payload_sequence(config, payload_seed, request_count),
    }


def scheduled_offsets(intervals: list[float]) -> list[float]:
    offsets = [0.0]
    cumulative = 0.0
    for interval in intervals:
        cumulative += interval
        offsets.append(_round(cumulative))
    return offsets
