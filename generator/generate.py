#!/usr/bin/env python3
"""Execute one deterministic Native ECH traffic trial and persist raw metadata."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from traffic_model import beacon_plan, load_config, normal_plan, scheduled_offsets

DEFAULT_OUTPUT_ROOT = Path("/data/raw")
CURL_META_PREFIX = "__CURL_META__\t"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat(timespec="microseconds")


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp, path)


def extract_echconfig(path: Path) -> str:
    inside = False
    chunks: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "-----BEGIN ECHCONFIG-----":
                inside = True
                continue
            if line == "-----END ECHCONFIG-----":
                inside = False
                break
            if inside:
                chunks.append("".join(line.split()))
    value = "".join(chunks)
    if not value:
        raise RuntimeError(f"ECHConfigList was not found in {path}")
    return value


def parse_headers_and_meta(stdout: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "http_status": None,
        "curl_time_total_s": None,
        "content_length": None,
        "ech_status": None,
        "outer_sni": None,
        "tls_sni": None,
    }

    for raw_line in stdout.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        lower = line.lower()
        if lower.startswith("content-length:"):
            value = line.split(":", 1)[1].strip()
            result["content_length"] = int(value) if value.isdigit() else None
        elif lower.startswith("x-ech-status:"):
            result["ech_status"] = line.split(":", 1)[1].strip()
        elif lower.startswith("x-ech-outer-sni:"):
            result["outer_sni"] = line.split(":", 1)[1].strip()
        elif lower.startswith("x-tls-sni:"):
            result["tls_sni"] = line.split(":", 1)[1].strip()
        elif line.startswith(CURL_META_PREFIX):
            parts = line.split("\t")
            if len(parts) >= 3:
                result["http_status"] = int(parts[1]) if parts[1].isdigit() else None
                try:
                    result["curl_time_total_s"] = float(parts[2])
                except ValueError:
                    result["curl_time_total_s"] = None
    return result


def make_query(length: int) -> str:
    return "q" * length


def run_transaction(
    config: dict[str, Any],
    echconfig: str,
    payload_name: str,
) -> tuple[dict[str, Any], str]:
    payload = config["payload_profiles"][payload_name]
    query = make_query(int(payload["query_bytes"]))
    url = (
        f"https://{config['protected_name']}:{int(config['port'])}"
        f"/traffic/{payload_name}?d={query}"
    )

    command = [
        str(config["curl_bin"]),
        "-skS",
        "--http1.1",
        "--tlsv1.3",
        "--ech",
        f"ecl:{echconfig}",
        "--connect-timeout",
        "5",
        "--max-time",
        "10",
        "-H",
        "Connection: close",
        "-H",
        "Cache-Control: no-cache",
        "-D",
        "-",
        "-o",
        "/dev/null",
        "-w",
        f"\n{CURL_META_PREFIX}%{{http_code}}\t%{{time_total}}\n",
        url,
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        parsed = parse_headers_and_meta(completed.stdout)
        parsed["curl_exit_code"] = completed.returncode
        parsed["curl_stderr"] = completed.stderr.strip()
        return parsed, url
    except subprocess.TimeoutExpired as exc:
        return {
            "http_status": None,
            "curl_time_total_s": None,
            "content_length": None,
            "ech_status": None,
            "outer_sni": None,
            "tls_sni": None,
            "curl_exit_code": 124,
            "curl_stderr": f"subprocess timeout: {exc}",
        }, url


def transaction_failure(parsed: dict[str, Any], config: dict[str, Any], payload_name: str) -> list[str]:
    reasons: list[str] = []
    expected_length = int(config["payload_profiles"][payload_name]["response_bytes"])
    if parsed["curl_exit_code"] != 0:
        reasons.append(f"curl_exit={parsed['curl_exit_code']}")
    if parsed["http_status"] != 200:
        reasons.append(f"http_status={parsed['http_status']}")
    if parsed["content_length"] != expected_length:
        reasons.append(f"content_length={parsed['content_length']} expected={expected_length}")
    if parsed["ech_status"] != "SUCCESS":
        reasons.append(f"ech_status={parsed['ech_status']}")
    if parsed["outer_sni"] != config["public_name"]:
        reasons.append(f"outer_sni={parsed['outer_sni']}")
    if parsed["tls_sni"] != config["protected_name"]:
        reasons.append(f"tls_sni={parsed['tls_sni']}")
    return reasons


def write_csv(path: Path, transactions: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "index",
        "payload_profile",
        "query_bytes",
        "response_bytes",
        "response_content_length",
        "scheduled_interval_before_s",
        "scheduled_offset_s",
        "scheduled_timestamp_utc",
        "actual_start_timestamp_utc",
        "actual_end_timestamp_utc",
        "actual_start_offset_s",
        "actual_iat_from_previous_s",
        "schedule_lag_s",
        "elapsed_s",
        "curl_time_total_s",
        "http_status",
        "ech_status",
        "outer_sni",
        "tls_sni",
        "curl_exit_code",
        "success",
        "failure_reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for transaction in transactions:
            writer.writerow({field: transaction.get(field) for field in fields})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="/workspace/generator/config.json")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--pcap-filename", default=None)
    parser.add_argument("--plan-only", action="store_true")

    subparsers = parser.add_subparsers(dest="traffic_class", required=True)

    beacon = subparsers.add_parser("beacon")
    beacon.add_argument("--jitter", required=True, type=int)
    beacon.add_argument("--trial", required=True, type=int)

    normal = subparsers.add_parser("normal")
    normal.add_argument("--profile", required=True)
    normal.add_argument("--trial", required=True, type=int)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)

    if args.traffic_class == "beacon":
        plan = beacon_plan(config, args.jitter, args.trial)
    else:
        plan = normal_plan(config, args.profile, args.trial)

    plan["scheduled_offsets_s"] = scheduled_offsets(plan["scheduled_intervals_s"])

    if args.plan_only:
        json.dump(plan, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    output_root = Path(args.output_root)
    manifest_path = output_root / "manifests" / f"{plan['trial_id']}.json"
    csv_path = output_root / "flow-metadata" / f"{plan['trial_id']}.csv"

    echconfig = extract_echconfig(Path(config["ech_file"]))
    trial_start_utc = utc_now()
    trial_start_monotonic = time.monotonic()

    manifest: dict[str, Any] = {
        "schema_version": int(config["schema_version"]),
        **plan,
        "generator_started_at_utc": iso(trial_start_utc),
        "generator_finished_at_utc": None,
        "status": "running",
        "failure_reason": None,
        "pcap_filename": args.pcap_filename,
        "pcap_sha256": None,
        "pcap_bytes": None,
        "transactions": [],
    }
    atomic_json(manifest_path, manifest)

    previous_actual_offset: float | None = None
    failure_reasons: list[str] = []

    for index, payload_name in enumerate(plan["payload_profile_sequence"]):
        target_offset = float(plan["scheduled_offsets_s"][index])
        target_monotonic = trial_start_monotonic + target_offset
        remaining = target_monotonic - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)

        actual_start_monotonic = time.monotonic()
        actual_start_utc = utc_now()
        actual_offset = actual_start_monotonic - trial_start_monotonic
        parsed, _url = run_transaction(config, echconfig, payload_name)
        actual_end_monotonic = time.monotonic()
        actual_end_utc = utc_now()

        reasons = transaction_failure(parsed, config, payload_name)
        success = not reasons
        if reasons:
            failure_reasons.extend(f"request_{index + 1}:{reason}" for reason in reasons)

        profile = config["payload_profiles"][payload_name]
        transaction = {
            "index": index + 1,
            "payload_profile": payload_name,
            "query_bytes": int(profile["query_bytes"]),
            "response_bytes": int(profile["response_bytes"]),
            "response_content_length": parsed["content_length"],
            "url_path": f"/traffic/{payload_name}",
            "scheduled_interval_before_s": None if index == 0 else plan["scheduled_intervals_s"][index - 1],
            "scheduled_offset_s": target_offset,
            "scheduled_timestamp_utc": iso(trial_start_utc + timedelta(seconds=target_offset)),
            "actual_start_timestamp_utc": iso(actual_start_utc),
            "actual_end_timestamp_utc": iso(actual_end_utc),
            "actual_start_offset_s": round(actual_offset, 9),
            "actual_iat_from_previous_s": None
            if previous_actual_offset is None
            else round(actual_offset - previous_actual_offset, 9),
            "schedule_lag_s": round(actual_start_monotonic - target_monotonic, 9),
            "elapsed_s": round(actual_end_monotonic - actual_start_monotonic, 9),
            "curl_time_total_s": parsed["curl_time_total_s"],
            "http_status": parsed["http_status"],
            "ech_status": parsed["ech_status"],
            "outer_sni": parsed["outer_sni"],
            "tls_sni": parsed["tls_sni"],
            "curl_exit_code": parsed["curl_exit_code"],
            "curl_stderr": parsed["curl_stderr"],
            "success": success,
            "failure_reason": ";".join(reasons) if reasons else "",
        }
        manifest["transactions"].append(transaction)
        previous_actual_offset = actual_offset
        atomic_json(manifest_path, manifest)

    manifest["generator_finished_at_utc"] = iso(utc_now())
    manifest["status"] = "success" if not failure_reasons else "failure"
    manifest["failure_reason"] = ";".join(failure_reasons) if failure_reasons else None
    atomic_json(manifest_path, manifest)
    write_csv(csv_path, manifest["transactions"])

    print(f"TRIAL_ID={plan['trial_id']}")
    print(f"STATUS={manifest['status']}")
    print(f"MANIFEST={manifest_path}")
    print(f"FLOW_METADATA={csv_path}")
    print(f"TRANSACTIONS={len(manifest['transactions'])}")

    return 0 if manifest["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
