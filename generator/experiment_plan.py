#!/usr/bin/env python3
"""Frozen 200-trial experiment catalog and safe batch planner, no traffic generated."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass

from traffic_model import beacon_plan, load_config, normal_plan


@dataclass(frozen=True)
class Trial:
    index: int
    kind: str
    value: str
    number: int
    trial_id: str
    category: str


RUN_TAG_RE = re.compile(r"main-v[1-9][0-9]*(?:-[A-Za-z0-9][A-Za-z0-9._-]*)?\Z")


def validate_run_tag(tag: str) -> str:
    if not isinstance(tag, str) or not RUN_TAG_RE.fullmatch(tag):
        raise ValueError("main experiment RUN_TAG must look like main-v1 or main-v2; no pilot tags")
    lowered = tag.lower()
    if "pilot" in lowered or "capture" in lowered or "test" in lowered:
        raise ValueError("diagnostic/pilot/test run tags cannot be used as the main experiment")
    return tag


def build_catalog(config: dict | None = None) -> list[Trial]:
    cfg = config if config is not None else load_config()
    catalog: list[Trial] = []

    # Stable, documented 1-based sequence, 100 beacon followed by 100 normal.
    for jitter in cfg["beacon"]["jitter_pct"]:
        for trial in range(1, int(cfg["beacon"]["trials_per_level"]) + 1):
            plan = beacon_plan(cfg, int(jitter), trial)
            catalog.append(Trial(
                len(catalog) + 1, "beacon", str(jitter), trial,
                plan["trial_id"], "beacon",
            ))
    for profile, meta in cfg["normal"]["profiles"].items():
        for trial in range(1, int(meta["samples"]) + 1):
            plan = normal_plan(cfg, profile, trial)
            catalog.append(Trial(
                len(catalog) + 1, "normal", profile, trial,
                plan["trial_id"], "normal",
            ))

    if (len(catalog) != 200 or
        sum(item.category == "beacon" for item in catalog) != 100 or
        sum(item.category == "normal" for item in catalog) != 100 or
        len({item.trial_id for item in catalog}) != 200):
        raise ValueError("generator config no longer describes frozen 100/100 experiment")
    return catalog


def select_batch(catalog: list[Trial], start: int, end: int) -> list[Trial]:
    if not 1 <= start <= end <= len(catalog):
        raise ValueError(f"batch indices must satisfy 1 <= START <= END <= {len(catalog)}")
    return catalog[start - 1:end]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=200)
    parser.add_argument("--format", choices=("tsv", "human"), default="human")
    parser.add_argument("--run-tag", default="main-v1")
    args = parser.parse_args()
    try:
        validate_run_tag(args.run_tag)
        trials = select_batch(build_catalog(), args.start, args.end)
    except ValueError as exc:
        parser.error(str(exc))
    for trial in trials:
        if args.format == "tsv":
            print(f"{trial.index}\t{trial.kind}\t{trial.value}\t{trial.number}\t{trial.trial_id}\t{trial.category}")
        else:
            print(f"{trial.index:03d}/200 {trial.trial_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
