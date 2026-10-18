#!/usr/bin/env python3
"""Deterministic, L2-regularized 13-feature logistic-regression model (v1)."""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence

from timing_only_cli import FEATURE_COLUMNS

MODEL_VERSION = "1.0.0"
FEATURE_DEFINITION_VERSION = "1.0.0"
LEARNING_RATE = 0.1
EPOCHS = 800
L2_LAMBDA = 0.1
CALIBRATION_COUNT = 90
NORMAL_CALIBRATION_COUNT = 40
BEACON_CALIBRATION_COUNT = 50


def vector(row: Mapping[str, object]) -> list[float]:
    """Reject non-finite features before training or predicting."""
    result = []
    for field in FEATURE_COLUMNS:
        if field not in row or row[field] is None or isinstance(row[field], bool):
            raise ValueError(f"missing or invalid feature: {field}")
        try:
            value = float(row[field])
        except (ValueError, TypeError) as exc:
            raise ValueError(f"non-numeric feature: {field}") from exc
        if not math.isfinite(value):
            raise ValueError(f"non-finite feature: {field}")
        if field == "iat_cv" and value < 0:
            raise ValueError("iat_cv cannot be negative")
        result.append(value)
    return result


def sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    scaled = math.exp(value)
    return scaled / (1.0 + scaled)


def scaler_fit(vectors: Sequence[Sequence[float]]) -> tuple[list[float], list[float]]:
    if not vectors:
        raise ValueError("no training rows")
    dimension = len(FEATURE_COLUMNS)
    if any(len(row) != dimension for row in vectors):
        raise ValueError("feature dimension mismatch")
    means = [statistics.fmean(row[j] for row in vectors) for j in range(dimension)]
    stds = [statistics.pstdev(row[j] for row in vectors) for j in range(dimension)]
    scales = [std if std > 0 else 1.0 for std in stds]
    if not all(math.isfinite(x) and x > 0 for x in scales):
        raise ValueError("invalid scaler")
    return means, scales


def standardized(
    raw_vector: Sequence[float], means: Sequence[float], scales: Sequence[float]
) -> list[float]:
    if (len(raw_vector) != len(FEATURE_COLUMNS) or
        len(means) != len(FEATURE_COLUMNS) or
        len(scales) != len(FEATURE_COLUMNS)):
        raise ValueError("feature/scaler dimension mismatch")
    if any(not math.isfinite(float(s)) or float(s) <= 0 for s in scales):
        raise ValueError("invalid scaler scale")
    result = [(float(x) - float(m)) / float(s)
              for x, m, s in zip(raw_vector, means, scales)]
    if any(not math.isfinite(v) for v in result):
        raise ValueError("non-finite standardized feature")
    return result


def score_z(z: Sequence[float], weights: Sequence[float], intercept: float) -> float:
    if len(z) != len(weights):
        raise ValueError("weight dimension mismatch")
    value = float(intercept) + math.fsum(w * x for w, x in zip(weights, z))
    if not math.isfinite(value):
        raise ValueError("non-finite detector score")
    return value


def train(rows: Sequence[Mapping[str, object]], labels: Sequence[int]) -> dict:
    """Input order must be deterministically sorted by trial ID in the caller."""
    if len(rows) != CALIBRATION_COUNT or len(labels) != CALIBRATION_COUNT:
        raise ValueError("expected exactly 90 calibration trials")
    if any(type(y) is not int or y not in (0, 1) for y in labels):
        raise ValueError("labels must be integer 0 or 1")
    if (sum(y == 0 for y in labels) != NORMAL_CALIBRATION_COUNT or
        sum(y == 1 for y in labels) != BEACON_CALIBRATION_COUNT):
        raise ValueError("expected 40 normal and 50 beacon calibration trials")

    vectors = [vector(row) for row in rows]
    means, scales = scaler_fit(vectors)
    zrows = [standardized(x, means, scales) for x in vectors]
    weights = [0.0] * len(FEATURE_COLUMNS)
    intercept = 0.0
    n = len(zrows)
    for _ in range(EPOCHS):
        errors = [
            sigmoid(score_z(z, weights, intercept)) - label
            for z, label in zip(zrows, labels)
        ]
        gradient_intercept = math.fsum(errors) / n
        gradient_weights = [
            math.fsum(error * z[j] for error, z in zip(errors, zrows)) / n
            + L2_LAMBDA * weights[j]
            for j in range(len(weights))
        ]
        weights = [
            weight - LEARNING_RATE * grad
            for weight, grad in zip(weights, gradient_weights)
        ]
        intercept -= LEARNING_RATE * gradient_intercept

    training_scores = [score_z(z, weights, intercept) for z in zrows]
    # numerically stable logistic cross-entropy: log(1+exp(s)) - y*s
    loss = math.fsum(
        max(s, 0.0) + math.log1p(math.exp(-abs(s))) - label * s
        for s, label in zip(training_scores, labels)
    ) / n + (L2_LAMBDA / 2) * math.fsum(w * w for w in weights)
    if not math.isfinite(loss):
        raise ValueError("non-finite training loss")
    return {
        "model_version": MODEL_VERSION,
        "feature_definition_version": FEATURE_DEFINITION_VERSION,
        "feature_columns": list(FEATURE_COLUMNS),
        "learning_rate": LEARNING_RATE,
        "epochs": EPOCHS,
        "l2_lambda": L2_LAMBDA,
        "optimizer": "deterministic_full_batch_gradient_descent",
        "score": "linear_logit",
        "comparison": ">",
        "training_count": CALIBRATION_COUNT,
        "training_normal_count": NORMAL_CALIBRATION_COUNT,
        "training_beacon_count": BEACON_CALIBRATION_COUNT,
        "scaler_mean": means,
        "scaler_scale": scales,
        "weights": weights,
        "intercept": intercept,
        "training_regularized_loss": loss,
    }


def predict_score(row: Mapping[str, object], model: Mapping) -> float:
    raw = vector(row)
    z = standardized(raw, model["scaler_mean"], model["scaler_scale"])
    return score_z(z, model["weights"], model["intercept"])


def calibrate_threshold(normal_logits: Sequence[float]) -> dict:
    if len(normal_logits) != NORMAL_CALIBRATION_COUNT:
        raise ValueError("expected 40 normal calibration scores")
    values = [float(x) for x in normal_logits]
    if any(not math.isfinite(x) for x in values):
        raise ValueError("non-finite calibration score")
    ordered = sorted(values, reverse=True)
    threshold = ordered[2]
    false_positives = sum(value > threshold for value in values)
    assert false_positives <= 2
    return {
        "threshold": threshold,
        "calibration_normal_logits_desc": ordered,
        "calibration_fp_count": false_positives,
        "calibration_empirical_fpr": false_positives / NORMAL_CALIBRATION_COUNT,
        "target_calibration_fpr": 0.05,
    }


def classify(score: float, threshold: float) -> int:
    if not math.isfinite(float(score)) or not math.isfinite(float(threshold)):
        raise ValueError("non-finite threshold or score")
    return int(score > threshold)
