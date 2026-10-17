#!/usr/bin/env python3
"""Extract deterministic trial-level features from Native ECH PCAP files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from feature_math import (
    burst_features,
    directionality_features,
    packet_size_features,
    timing_features,
    validate_feature_values,
)

FEATURE_COLUMNS = [
    "iat_mean_s",
    "iat_std_s",
    "iat_cv",
    "iat_mad_s",
    "packet_size_mean_bytes",
    "packet_size_std_bytes",
    "packet_size_cv",
    "out_in_packet_ratio",
    "byte_asymmetry",
    "direction_change_ratio",
    "burst_count",
    "burst_mean_size",
    "burst_interval_cv",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tshark_version() -> str:
    completed = subprocess.run(
        ["tshark", "--version"], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(f"tshark --version failed: {completed.stderr.strip()}")
    return completed.stdout.splitlines()[0].strip()


def parse_packets(pcap_path: Path, server_port: int) -> list[dict[str, Any]]:
    command = [
        "tshark",
        "-r",
        str(pcap_path),
        "-Y",
        f"ip && tcp.port == {server_port}",
        "-T",
        "fields",
        "-E",
        "separator=\t",
        "-E",
        "occurrence=f",
        "-e",
        "frame.number",
        "-e",
        "frame.time_epoch",
        "-e",
        "ip.len",
        "-e",
        "tcp.stream",
        "-e",
        "tcp.srcport",
        "-e",
        "tcp.dstport",
        "-e",
        "tcp.flags.syn",
        "-e",
        "tcp.flags.ack",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"tshark failed for {pcap_path}: {completed.stderr.strip()}")

    packets: list[dict[str, Any]] = []
    for line_number, raw in enumerate(completed.stdout.splitlines(), start=1):
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) < 8:
            parts.extend([""] * (8 - len(parts)))
        try:
            frame_number = int(parts[0])
            timestamp = float(parts[1])
            ip_length = int(parts[2])
            stream = int(parts[3])
            srcport = int(parts[4])
            dstport = int(parts[5])
            syn = int(parts[6] or "0")
            ack = int(parts[7] or "0")
        except ValueError as exc:
            raise RuntimeError(
                f"invalid tshark field at output line {line_number}: {raw!r}"
            ) from exc

        if not math.isfinite(timestamp) or ip_length <= 0:
            raise RuntimeError(f"invalid packet metadata at output line {line_number}")

        if dstport == server_port:
            direction = "out"
        elif srcport == server_port:
            direction = "in"
        else:
            continue

        packets.append(
            {
                "frame_number": frame_number,
                "timestamp": timestamp,
                "ip_length": ip_length,
                "stream": stream,
                "srcport": srcport,
                "dstport": dstport,
                "syn": syn,
                "ack": ack,
                "direction": direction,
            }
        )

    packets.sort(key=lambda item: (item["timestamp"], item["frame_number"]))
    return packets


def flow_start_timestamps(
    packets: list[dict[str, Any]], server_port: int
) -> tuple[list[float], set[int]]:
    streams = {int(packet["stream"]) for packet in packets}
    first_syn_by_stream: dict[int, float] = {}
    for packet in packets:
        if (
            packet["dstport"] == server_port
            and packet["syn"] == 1
            and packet["ack"] == 0
        ):
            stream = int(packet["stream"])
            timestamp = float(packet["timestamp"])
            previous = first_syn_by_stream.get(stream)
            if previous is None or timestamp < previous:
                first_syn_by_stream[stream] = timestamp
    return sorted(first_syn_by_stream.values()), streams


def pcap_path_from_manifest(manifest: dict[str, Any], pcap_root: Path) -> Path:
    filename = manifest.get("pcap_filename")
    prefix = "artifacts/pcap/"
    if not isinstance(filename, str) or not filename.startswith(prefix):
        raise ValueError(f"unexpected pcap_filename: {filename!r}")
    return pcap_root / filename[len(prefix) :]


def extract_trial(
    manifest_path: Path,
    pcap_root: Path,
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    trial_started = time.perf_counter_ns()
    manifest = load_json(manifest_path)
    trial_id = str(manifest.get("trial_id", manifest_path.stem))
    errors: list[str] = []

    if manifest.get("status") != "success":
        errors.append(f"manifest_status={manifest.get('status')}")

    expected_flow_count = int(config["expected_flow_count"])
    if int(manifest.get("request_count", -1)) != expected_flow_count:
        errors.append(f"request_count={manifest.get('request_count')}")

    pcap_path = pcap_path_from_manifest(manifest, pcap_root)
    if not pcap_path.is_file():
        raise FileNotFoundError(f"{trial_id}: PCAP not found: {pcap_path}")

    expected_sha = manifest.get("pcap_sha256")
    actual_sha = sha256_file(pcap_path)
    if actual_sha != expected_sha:
        errors.append("pcap_sha256_mismatch")

    parse_started = time.perf_counter_ns()
    packets = parse_packets(pcap_path, int(config["server_port"]))
    parse_finished = time.perf_counter_ns()

    compute_started = time.perf_counter_ns()
    starts, streams = flow_start_timestamps(packets, int(config["server_port"]))
    directional_packets = [packet for packet in packets if packet["direction"] in {"out", "in"}]
    packet_sizes = [float(packet["ip_length"]) for packet in directional_packets]
    directions = [str(packet["direction"]) for packet in directional_packets]

    if len(streams) != expected_flow_count:
        errors.append(f"flow_count={len(streams)} expected={expected_flow_count}")
    if len(starts) != expected_flow_count:
        errors.append(f"flow_start_count={len(starts)} expected={expected_flow_count}")
    if max(len(starts) - 1, 0) != expected_flow_count - 1:
        errors.append(f"iat_count={max(len(starts) - 1, 0)} expected={expected_flow_count - 1}")
    if not packets:
        errors.append("packet_count=0")
    outbound_count = sum(direction == "out" for direction in directions)
    inbound_count = sum(direction == "in" for direction in directions)
    if outbound_count == 0:
        errors.append("outbound_packet_count=0")
    if inbound_count == 0:
        errors.append("inbound_packet_count=0")

    features: dict[str, float | int | None] = {}
    try:
        features.update(timing_features(starts))
        features.update(packet_size_features(packet_sizes))
        features.update(directionality_features(directions, packet_sizes))
        features.update(
            burst_features(starts, float(config["burst_gap_threshold_s"]))
        )
    except ValueError as exc:
        errors.append(f"feature_calculation:{exc}")

    errors.extend(validate_feature_values(features))
    compute_finished = time.perf_counter_ns()

    if set(features) != set(FEATURE_COLUMNS):
        errors.append("feature_schema_mismatch")

    feature_row: dict[str, Any] = {"trial_id": trial_id}
    for column in FEATURE_COLUMNS:
        feature_row[column] = features.get(column)

    traffic_class = str(manifest.get("traffic_class"))
    label_row = {
        "trial_id": trial_id,
        "traffic_class": traffic_class,
        "label": 1 if traffic_class == "beacon" else 0 if traffic_class == "normal" else None,
        "jitter_pct": manifest.get("jitter_pct"),
        "normal_profile": manifest.get("normal_profile"),
    }
    if label_row["label"] is None:
        errors.append(f"unknown_traffic_class={traffic_class}")

    trial_finished = time.perf_counter_ns()
    provenance = {
        "trial_id": trial_id,
        "source_manifest": str(manifest_path),
        "source_pcap": str(pcap_path),
        "source_pcap_sha256": actual_sha,
        "packet_count": len(packets),
        "flow_count": len(streams),
        "flow_start_count": len(starts),
        "iat_count": max(len(starts) - 1, 0),
        "outbound_packet_count": outbound_count,
        "inbound_packet_count": inbound_count,
        "tshark_parse_ms": round((parse_finished - parse_started) / 1_000_000.0, 6),
        "feature_compute_ms": round((compute_finished - compute_started) / 1_000_000.0, 6),
        "total_extraction_ms": round((trial_finished - trial_started) / 1_000_000.0, 6),
        "validation_status": "pass" if not errors else "fail",
        "validation_errors": errors,
    }
    return feature_row, label_row, provenance


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tag", required=True)
    parser.add_argument("--config", default="/workspace/extractor/config.json")
    parser.add_argument("--raw-root", default="/data/raw")
    parser.add_argument("--pcap-root", default="/pcap")
    parser.add_argument("--processed-root", default="/data/processed")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = load_json(Path(args.config))
    manifest_dir = Path(args.raw_root) / args.run_tag / "manifests"
    if not manifest_dir.is_dir():
        raise SystemExit(f"manifest directory not found: {manifest_dir}")

    manifests = sorted(manifest_dir.glob("*.json"))
    if not manifests:
        raise SystemExit(f"no manifests found: {manifest_dir}")

    output_dir = Path(args.processed_root) / args.run_tag
    features_path = output_dir / "features.csv"
    labels_path = output_dir / "labels.csv"
    provenance_path = output_dir / "provenance.json"
    existing = [path for path in (features_path, labels_path, provenance_path) if path.exists()]
    if existing and not args.overwrite:
        names = ", ".join(str(path) for path in existing)
        raise SystemExit(f"processed output already exists; refusing overwrite: {names}")
    output_dir.mkdir(parents=True, exist_ok=True)

    version = tshark_version()
    feature_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    trial_provenance: list[dict[str, Any]] = []

    for manifest_path in manifests:
        feature_row, label_row, provenance = extract_trial(
            manifest_path, Path(args.pcap_root), config
        )
        feature_rows.append(feature_row)
        label_rows.append(label_row)
        trial_provenance.append(provenance)
        print(
            f"{provenance['validation_status'].upper()}: {provenance['trial_id']} "
            f"flows={provenance['flow_count']} packets={provenance['packet_count']} "
            f"total_ms={provenance['total_extraction_ms']}"
        )

    feature_rows.sort(key=lambda row: row["trial_id"])
    label_rows.sort(key=lambda row: row["trial_id"])
    trial_provenance.sort(key=lambda row: row["trial_id"])

    feature_ids = [row["trial_id"] for row in feature_rows]
    label_ids = [row["trial_id"] for row in label_rows]
    if feature_ids != label_ids or len(set(feature_ids)) != len(feature_ids):
        raise SystemExit("feature/label trial_id mapping is not one-to-one")

    write_csv(features_path, feature_rows, ["trial_id", *FEATURE_COLUMNS])
    write_csv(
        labels_path,
        label_rows,
        ["trial_id", "traffic_class", "label", "jitter_pct", "normal_profile"],
    )

    failed_trials = [
        row["trial_id"] for row in trial_provenance if row["validation_status"] != "pass"
    ]
    provenance_document = {
        "extractor_schema_version": int(config["schema_version"]),
        "feature_definition_version": str(config["feature_definition_version"]),
        "run_tag": args.run_tag,
        "extracted_at_utc": utc_now(),
        "tshark_version": version,
        "server_port": int(config["server_port"]),
        "expected_flow_count": int(config["expected_flow_count"]),
        "burst_gap_threshold_s": float(config["burst_gap_threshold_s"]),
        "feature_columns": FEATURE_COLUMNS,
        "trial_count": len(trial_provenance),
        "validation_status": "pass" if not failed_trials else "fail",
        "failed_trials": failed_trials,
        "trials": trial_provenance,
    }
    write_json_atomic(provenance_path, provenance_document)

    print(f"FEATURES={features_path}")
    print(f"LABELS={labels_path}")
    print(f"PROVENANCE={provenance_path}")
    print(f"TRIALS={len(trial_provenance)}")
    print(f"VALIDATION={provenance_document['validation_status']}")
    return 0 if not failed_trials else 1


if __name__ == "__main__":
    raise SystemExit(main())
