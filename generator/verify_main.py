#!/usr/bin/env python3
"""Verify Native ECH main-experiment raw artifacts without reading detector scores."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from experiment_plan import Trial, build_catalog, validate_run_tag
from finalize_manifest import parse_clienthello
from traffic_model import beacon_plan, load_config, normal_plan
from verify_pilot import verify_common


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def paths_for(trial: Trial, tag: str, raw_root: Path, pcap_root: Path) -> tuple[Path, Path, Path]:
    raw_dir = raw_root / tag
    manifest = raw_dir / "manifests" / f"{trial.trial_id}.json"
    csv_file = raw_dir / "flow-metadata" / f"{trial.trial_id}.csv"
    pcap = pcap_root / tag / trial.category / f"{trial.trial_id}.pcap"
    return manifest, csv_file, pcap


def verify_one(
    trial: Trial,
    tag: str,
    raw_root: Path,
    pcap_root: Path,
    config: dict | None = None,
) -> dict:
    validate_run_tag(tag)
    cfg = config if config is not None else load_config()
    manifest_file, csv_file, pcap_file = paths_for(trial, tag, raw_root, pcap_root)
    check(manifest_file.is_file(), f"{trial.trial_id}: missing manifest")
    check(csv_file.is_file(), f"{trial.trial_id}: missing flow CSV")
    check(pcap_file.is_file(), f"{trial.trial_id}: missing PCAP")

    with manifest_file.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    expected = (beacon_plan(cfg, int(trial.value), trial.number)
                if trial.kind == "beacon"
                else normal_plan(cfg, trial.value, trial.number))
    check(expected["trial_id"] == trial.trial_id, f"{trial.trial_id}: catalog mismatch")
    check(manifest.get("trial_id") == manifest_file.stem, f"{trial.trial_id}: manifest filename mismatch")
    for name in (
        "traffic_class", "normal_profile", "trial_number", "jitter_pct",
        "request_count", "timing_seed", "payload_seed", "normalized_jitter",
        "scheduled_intervals_s", "payload_profile_sequence",
    ):
        check(manifest.get(name) == expected.get(name),
              f"{trial.trial_id}: deterministic generator field mismatch: {name}")
    check(manifest.get("pcap_filename") ==
          f"artifacts/pcap/{tag}/{trial.category}/{trial.trial_id}.pcap",
          f"{trial.trial_id}: PCAP path mismatch")
    check(manifest.get("pcap_bytes") == pcap_file.stat().st_size and pcap_file.stat().st_size > 0,
          f"{trial.trial_id}: PCAP size mismatch")

    # Reuse pre-existing evidence validations: 30 requests, ECH SUCCESS,
    # outer SNI, scheduled interval and payload sequence, PCAP SHA.
    verify_common(manifest, expected, cfg, pcap_root)

    with csv_file.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    check(len(rows) == 30, f"{trial.trial_id}: flow CSV row count != 30")
    for index, row in enumerate(rows, start=1):
        check(row.get("index") == str(index) and row.get("success") == "True",
              f"{trial.trial_id}: flow CSV row {index} invalid")
        check(row.get("payload_profile") == expected["payload_profile_sequence"][index - 1],
              f"{trial.trial_id}: flow CSV payload mismatch")

    # Independently parse the immutable captured PCAP rather than trusting the
    # stored ClientHello count alone.
    timestamps, outer_sni = parse_clienthello(pcap_file)
    check(len(timestamps) == 30 and len(outer_sni) == 30,
          f"{trial.trial_id}: actual PCAP does not contain 30 ClientHello")
    check(all(sni == cfg["public_name"] for sni in outer_sni),
          f"{trial.trial_id}: parsed outer SNI mismatch")
    stored = manifest["pcap_clienthello"]
    check(timestamps == stored["timestamps_epoch"] and outer_sni == stored["outer_sni"],
          f"{trial.trial_id}: stored ClientHello evidence mismatches PCAP")
    return manifest


def verify_all(tag: str, raw_root: Path, pcap_root: Path) -> None:
    validate_run_tag(tag)
    trials = build_catalog()
    expected_ids = {t.trial_id for t in trials}
    raw = raw_root / tag
    manifests = {p.stem for p in (raw / "manifests").glob("*.json")}
    metadata = {p.stem for p in (raw / "flow-metadata").glob("*.csv")}
    captures = {p.stem for p in (pcap_root / tag).glob("*/*.pcap")}
    for name, actual in (("manifests", manifests), ("flow CSV", metadata), ("PCAP", captures)):
        check(actual == expected_ids,
              f"{name}: missing={len(expected_ids-actual)}, unexpected={len(actual-expected_ids)}")
    paired: dict[int, tuple[list, list]] = {}
    config = load_config()
    for trial in trials:
        manifest = verify_one(trial, tag, raw_root, pcap_root, config)
        if trial.category == "beacon":
            pair = (manifest["normalized_jitter"], manifest["payload_profile_sequence"])
            previous = paired.setdefault(trial.number, pair)
            check(previous == pair, f"{trial.trial_id}: paired jitter/payload inconsistency")
    counts = Counter(t.category for t in trials)
    check(counts == {"beacon": 100, "normal": 100}, "unexpected class counts")
    print(f"PASS: main experiment {tag}: 200/200 raw trials validated")
    print("PASS: 100 beacon / 100 normal, each 30 requests and 30 parsed ClientHello")
    print("PASS: Native ECH SUCCESS, outer SNI, deterministic plans, paired jitter")
    print("PASS: source PCAP SHA-256, manifest/flow CSV correspondence")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tag", required=True)
    parser.add_argument("--trial-id")
    parser.add_argument("--raw-root", type=Path, default=Path("/data/raw"))
    parser.add_argument("--pcap-root", type=Path, default=Path("/pcap"))
    args = parser.parse_args()
    try:
        validate_run_tag(args.run_tag)
        if args.trial_id:
            trial = next((t for t in build_catalog() if t.trial_id == args.trial_id), None)
            if trial is None:
                raise ValueError(f"unknown trial ID: {args.trial_id}")
            verify_one(trial, args.run_tag, args.raw_root, args.pcap_root)
            print(f"PASS: raw trial {trial.trial_id}")
        else:
            verify_all(args.run_tag, args.raw_root, args.pcap_root)
        return 0
    except (ValueError, AssertionError, OSError, KeyError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
