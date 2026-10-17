#!/usr/bin/env python3
"""Pure feature calculations for trial-level encrypted traffic metadata."""

from __future__ import annotations

import math
import statistics
from typing import Iterable


def _values(items: Iterable[float]) -> list[float]:
    values = [float(item) for item in items]
    if not values:
        raise ValueError("at least one value is required")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("all values must be finite")
    return values


def population_mean_std_cv(items: Iterable[float]) -> tuple[float, float, float | None]:
    values = _values(items)
    mean = statistics.fmean(values)
    std = statistics.pstdev(values)
    cv = std / mean if mean != 0 else None
    return mean, std, cv


def raw_mad(items: Iterable[float]) -> float:
    values = _values(items)
    center = statistics.median(values)
    return statistics.median(abs(value - center) for value in values)


def differences(values: Iterable[float]) -> list[float]:
    ordered = _values(values)
    if len(ordered) < 2:
        return []
    return [ordered[index] - ordered[index - 1] for index in range(1, len(ordered))]


def timing_features(flow_start_timestamps: Iterable[float]) -> dict[str, float | None]:
    starts = sorted(_values(flow_start_timestamps))
    iat = differences(starts)
    if not iat:
        raise ValueError("at least two flow starts are required")
    mean, std, cv = population_mean_std_cv(iat)
    return {
        "iat_mean_s": mean,
        "iat_std_s": std,
        "iat_cv": cv,
        "iat_mad_s": raw_mad(iat),
    }


def packet_size_features(packet_sizes: Iterable[float]) -> dict[str, float | None]:
    mean, std, cv = population_mean_std_cv(packet_sizes)
    return {
        "packet_size_mean_bytes": mean,
        "packet_size_std_bytes": std,
        "packet_size_cv": cv,
    }


def directionality_features(
    directions: Iterable[str],
    packet_sizes: Iterable[float],
) -> dict[str, float | None]:
    direction_values = list(directions)
    size_values = _values(packet_sizes)
    if len(direction_values) != len(size_values):
        raise ValueError("directions and packet_sizes must have the same length")
    if not direction_values:
        raise ValueError("at least one directional packet is required")
    if any(direction not in {"out", "in"} for direction in direction_values):
        raise ValueError("direction must be 'out' or 'in'")

    outbound_count = sum(direction == "out" for direction in direction_values)
    inbound_count = sum(direction == "in" for direction in direction_values)
    outbound_bytes = sum(size for direction, size in zip(direction_values, size_values) if direction == "out")
    inbound_bytes = sum(size for direction, size in zip(direction_values, size_values) if direction == "in")

    packet_ratio = outbound_count / inbound_count if inbound_count else None
    total_bytes = outbound_bytes + inbound_bytes
    byte_asymmetry = (outbound_bytes - inbound_bytes) / total_bytes if total_bytes else None

    if len(direction_values) < 2:
        change_ratio = None
    else:
        changes = sum(
            direction_values[index] != direction_values[index - 1]
            for index in range(1, len(direction_values))
        )
        change_ratio = changes / (len(direction_values) - 1)

    return {
        "out_in_packet_ratio": packet_ratio,
        "byte_asymmetry": byte_asymmetry,
        "direction_change_ratio": change_ratio,
    }


def burst_features(
    flow_start_timestamps: Iterable[float],
    threshold_s: float,
) -> dict[str, float | int | None]:
    if threshold_s <= 0:
        raise ValueError("threshold_s must be positive")
    starts = sorted(_values(flow_start_timestamps))

    burst_starts = [starts[0]]
    burst_sizes = [1]
    for index in range(1, len(starts)):
        gap = starts[index] - starts[index - 1]
        if gap <= threshold_s:
            burst_sizes[-1] += 1
        else:
            burst_starts.append(starts[index])
            burst_sizes.append(1)

    burst_intervals = differences(burst_starts)
    burst_interval_cv: float | None = None
    if burst_intervals:
        _mean, _std, burst_interval_cv = population_mean_std_cv(burst_intervals)

    return {
        "burst_count": len(burst_sizes),
        "burst_mean_size": statistics.fmean(burst_sizes),
        "burst_interval_cv": burst_interval_cv,
    }


def validate_feature_values(features: dict[str, float | int | None]) -> list[str]:
    errors: list[str] = []
    for name, value in features.items():
        if value is None:
            errors.append(f"{name}:missing")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{name}:non_numeric")
            continue
        if not math.isfinite(float(value)):
            errors.append(f"{name}:non_finite")
    return errors
