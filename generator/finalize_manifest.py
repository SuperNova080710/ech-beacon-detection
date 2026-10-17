#!/usr/bin/env python3
"""Attach packet-capture metadata and ClientHello timing to a trial manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_clienthello(pcap_path: Path) -> tuple[list[str], list[str]]:
    command = [
        "tshark",
        "-r",
        str(pcap_path),
        "-Y",
        "tls.handshake.type == 1 && !tcp.analysis.retransmission",
        "-T",
        "fields",
        "-E",
        "separator=\t",
        "-E",
        "occurrence=f",
        "-e",
        "frame.time_epoch",
        "-e",
        "tls.handshake.extensions_server_name",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"tshark failed: {completed.stderr.strip()}")

    timestamps: list[str] = []
    sni_values: list[str] = []
    for raw in completed.stdout.splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t", 1)
        timestamp = parts[0].strip()
        sni = parts[1].strip() if len(parts) == 2 else ""
        if timestamp:
            timestamps.append(timestamp)
            sni_values.append(sni)
    return timestamps, sni_values


def differences(values: list[float]) -> list[float]:
    return [round(values[index] - values[index - 1], 9) for index in range(1, len(values))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="/data/raw")
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--pcap-filename", required=True)
    parser.add_argument("--pcap-path", required=True)
    parser.add_argument("--pcap-sha256", required=True)
    parser.add_argument("--pcap-bytes", required=True, type=int)
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9a-f]{64}", args.pcap_sha256):
        raise SystemExit("invalid SHA-256")
    if args.pcap_bytes <= 0:
        raise SystemExit("pcap size must be positive")

    pcap_path = Path(args.pcap_path)
    if not pcap_path.is_file():
        raise SystemExit(f"pcap not found: {pcap_path}")
    if pcap_path.stat().st_size != args.pcap_bytes:
        raise SystemExit("pcap size changed before manifest finalization")
    if sha256_file(pcap_path) != args.pcap_sha256:
        raise SystemExit("pcap SHA-256 mismatch before manifest finalization")

    manifest_path = Path(args.output_root) / "manifests" / f"{args.trial_id}.json"
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    timestamps_epoch, outer_sni = parse_clienthello(pcap_path)
    timestamp_values = [float(value) for value in timestamps_epoch]
    clienthello_iat = differences(timestamp_values)
    scheduled = [float(value) for value in manifest["scheduled_intervals_s"]]

    compare_count = min(len(clienthello_iat), len(scheduled))
    errors = [round(clienthello_iat[i] - scheduled[i], 9) for i in range(compare_count)]
    absolute_errors = [abs(value) for value in errors]

    manifest["pcap_filename"] = args.pcap_filename
    manifest["pcap_sha256"] = args.pcap_sha256
    manifest["pcap_bytes"] = args.pcap_bytes
    manifest["pcap_clienthello"] = {
        "count": len(timestamps_epoch),
        "timestamps_epoch": timestamps_epoch,
        "iat_s": clienthello_iat,
        "outer_sni": outer_sni,
        "scheduled_iat_error_s": errors,
        "mean_abs_scheduled_iat_error_s": round(sum(absolute_errors) / len(absolute_errors), 9)
        if absolute_errors
        else None,
        "max_abs_scheduled_iat_error_s": round(max(absolute_errors), 9) if absolute_errors else None,
    }
    manifest["pcap_finalized_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    atomic_json(manifest_path, manifest)

    print(f"FINALIZED={manifest_path}")
    print(f"PCAP_SHA256={args.pcap_sha256}")
    print(f"CLIENTHELLO_COUNT={len(timestamps_epoch)}")
    if absolute_errors:
        print(f"MEAN_ABS_IAT_ERROR_S={manifest['pcap_clienthello']['mean_abs_scheduled_iat_error_s']}")
        print(f"MAX_ABS_IAT_ERROR_S={manifest['pcap_clienthello']['max_abs_scheduled_iat_error_s']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
