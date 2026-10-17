#!/usr/bin/env python3
"""Attach packet-capture metadata to an existing trial manifest."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="/data/raw")
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--pcap-filename", required=True)
    parser.add_argument("--pcap-sha256", required=True)
    parser.add_argument("--pcap-bytes", required=True, type=int)
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9a-f]{64}", args.pcap_sha256):
        raise SystemExit("invalid SHA-256")
    if args.pcap_bytes <= 0:
        raise SystemExit("pcap size must be positive")

    manifest_path = Path(args.output_root) / "manifests" / f"{args.trial_id}.json"
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    manifest["pcap_filename"] = args.pcap_filename
    manifest["pcap_sha256"] = args.pcap_sha256
    manifest["pcap_bytes"] = args.pcap_bytes
    manifest["pcap_finalized_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    atomic_json(manifest_path, manifest)

    print(f"FINALIZED={manifest_path}")
    print(f"PCAP_SHA256={args.pcap_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
