#!/usr/bin/env python3
"""Verify the eight pre-defined traffic-generator pilot trials."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from traffic_model import beacon_plan, load_config, normal_plan


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise AssertionError(message)


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        fail(f"missing manifest: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def verify_common(
    manifest: dict[str, Any],
    expected: dict[str, Any],
    config: dict[str, Any],
    pcap_root: Path,
) -> None:
    trial_id = expected["trial_id"]
    if manifest["trial_id"] != trial_id:
        fail(f"{trial_id}: trial_id mismatch")
    if manifest["status"] != "success":
        fail(f"{trial_id}: generator status is {manifest['status']}")
    if manifest["scheduled_intervals_s"] != expected["scheduled_intervals_s"]:
        fail(f"{trial_id}: scheduled intervals are not deterministic")
    if manifest["payload_profile_sequence"] != expected["payload_profile_sequence"]:
        fail(f"{trial_id}: payload sequence mismatch")

    transactions = manifest["transactions"]
    if len(transactions) != int(config["request_count"]):
        fail(f"{trial_id}: expected {config['request_count']} transactions, got {len(transactions)}")
    for transaction in transactions:
        if not transaction["success"]:
            fail(f"{trial_id}: request {transaction['index']} failed")
        if transaction["ech_status"] != "SUCCESS":
            fail(f"{trial_id}: request {transaction['index']} ECH status is not SUCCESS")
        if transaction["outer_sni"] != config["public_name"]:
            fail(f"{trial_id}: unexpected outer SNI")
        if transaction["tls_sni"] != config["protected_name"]:
            fail(f"{trial_id}: unexpected protected SNI")

    pcap_filename = manifest.get("pcap_filename")
    pcap_sha256 = manifest.get("pcap_sha256")
    if not pcap_filename or not pcap_sha256:
        fail(f"{trial_id}: PCAP metadata is missing")
    prefix = "artifacts/pcap/"
    if not pcap_filename.startswith(prefix):
        fail(f"{trial_id}: unexpected PCAP path {pcap_filename}")
    pcap_path = pcap_root / pcap_filename[len(prefix):]
    if not pcap_path.is_file():
        fail(f"{trial_id}: PCAP file is missing at {pcap_path}")
    if sha256_file(pcap_path) != pcap_sha256:
        fail(f"{trial_id}: PCAP SHA-256 does not match manifest")

    clienthello = manifest.get("pcap_clienthello") or {}
    if clienthello.get("count") != int(config["request_count"]):
        fail(f"{trial_id}: expected 30 ClientHello packets, got {clienthello.get('count')}")
    if len(clienthello.get("iat_s") or []) != int(config["request_count"]) - 1:
        fail(f"{trial_id}: PCAP ClientHello IAT count mismatch")
    sni_values = clienthello.get("outer_sni") or []
    if not sni_values or any(value != config["public_name"] for value in sni_values):
        fail(f"{trial_id}: PCAP contains unexpected outer SNI values: {sni_values}")
    if config["protected_name"] in sni_values:
        fail(f"{trial_id}: protected SNI is visible in parsed ClientHello")
    if len(clienthello.get("scheduled_iat_error_s") or []) != int(config["request_count"]) - 1:
        fail(f"{trial_id}: scheduled-vs-PCAP IAT comparison is incomplete")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="/workspace/generator/config.json")
    parser.add_argument("--run-tag", default="pilot-v1")
    parser.add_argument("--data-root", default="/data/raw")
    parser.add_argument("--pcap-root", default="/pcap")
    args = parser.parse_args()

    config = load_config(args.config)
    manifest_root = Path(args.data_root) / args.run_tag / "manifests"
    pcap_root = Path(args.pcap_root)

    expected_plans: list[dict[str, Any]] = []
    for jitter in config["beacon"]["jitter_pct"]:
        expected_plans.append(beacon_plan(config, int(jitter), 1))
    for profile in config["normal"]["profiles"]:
        expected_plans.append(normal_plan(config, profile, 1))

    beacon_manifests: list[dict[str, Any]] = []
    for expected in expected_plans:
        manifest_path = manifest_root / f"{expected['trial_id']}.json"
        manifest = load_manifest(manifest_path)
        verify_common(manifest, expected, config, pcap_root)
        if expected["traffic_class"] == "beacon":
            beacon_manifests.append(manifest)
        mean_error = manifest["pcap_clienthello"]["mean_abs_scheduled_iat_error_s"]
        print(f"PASS: {expected['trial_id']} mean_abs_iat_error_s={mean_error}")

    zero = next(item for item in beacon_manifests if item["jitter_pct"] == 0)
    if any(value != 1.0 for value in zero["scheduled_intervals_s"]):
        fail("beacon 0% jitter does not contain only 1.0 s intervals")

    normalized = beacon_manifests[0]["normalized_jitter"]
    payloads = beacon_manifests[0]["payload_profile_sequence"]
    for manifest in beacon_manifests[1:]:
        if manifest["normalized_jitter"] != normalized:
            fail("paired beacon trials do not share the normalized jitter sequence")
        if manifest["payload_profile_sequence"] != payloads:
            fail("paired beacon trials do not share the payload sequence")

    base = float(config["beacon"]["base_interval_s"])
    for manifest in beacon_manifests:
        ratio = int(manifest["jitter_pct"]) / 100.0
        low = base * (1.0 - ratio)
        high = base * (1.0 + ratio)
        if not all(low <= value <= high for value in manifest["scheduled_intervals_s"]):
            fail(f"{manifest['trial_id']}: scheduled interval escaped jitter range")

    print()
    print("PASS: all 8 pilot trials satisfy the pre-defined generator conditions")
    print("PASS: Native ECH SUCCESS and public outer SNI confirmed for every transaction")
    print("PASS: 30 protocol-parsed ClientHello packets confirmed per trial")
    print("PASS: scheduled and network-observed ClientHello IAT are both preserved")
    print("PASS: paired jitter and payload sequences are deterministic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
