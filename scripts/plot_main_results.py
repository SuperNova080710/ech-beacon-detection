#!/usr/bin/env python3
"""Generate frozen main-v1 paper figures without modifying source results."""

import hashlib
import json
import platform
import shutil
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUN_TAG = "main-v1"

METRICS_PATH = Path(
    "results/metrics/main-v1/heldout-evaluation.json"
)

COST_PATH = Path(
    "results/metrics/main-v1/processing-cost-benchmark.json"
)

OUTPUT_DIR = Path("results/figures/main-v1")

EXPECTED_HASHES = {
    METRICS_PATH:
        "b357dee703565d98b65467b94f488f9681e53f3ed41b1e3153f432279be9f46b",
    COST_PATH:
        "4d25da1fd02a2b672e42074454239ca1067c2e055090112c732c70391105c3df",
}

FIGURE_NAMES = (
    "01-overall-performance.png",
    "02-jitter-recall.png",
    "03-jitter-conditional-f1.png",
    "04-normal-profile-fpr.png",
    "05-inference-cost.png",
    "06-calibration-cost.png",
)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_sources():
    for path, expected in EXPECTED_HASHES.items():
        assert path.is_file(), f"Missing file: {path}"
        assert sha256(path) == expected, f"SHA mismatch: {path}"

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def annotate_bars(ax, bars, unit="", digits=4):
    for bar in bars:
        value = bar.get_height()
        ax.annotate(
            f"{value:.{digits}f}{unit}",
            (bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )

def save_figure(fig, directory, filename):
    fig.savefig(
        directory / filename,
        dpi=170,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)

def prepare_axis(ax):
    ax.grid(axis="y", alpha=0.22)
    ax.set_axisbelow(True)

def main():
    verify_sources()

    metrics = load_json(METRICS_PATH)
    costs = load_json(COST_PATH)

    assert metrics["run_tag"] == RUN_TAG
    assert costs["run_tag"] == RUN_TAG

    detectors = metrics["detectors"]

    timing = detectors["timing-only"]
    multi = detectors["multi-feature"]

    assert metrics["sample_counts"] == {
        "total": 110,
        "beacon": 50,
        "normal": 60,
    }

    assert (
        timing["overall"]["TP"],
        timing["overall"]["FP"],
        timing["overall"]["TN"],
        timing["overall"]["FN"],
    ) == (50, 10, 50, 0)

    assert (
        multi["overall"]["TP"],
        multi["overall"]["FP"],
        multi["overall"]["TN"],
        multi["overall"]["FN"],
    ) == (50, 7, 53, 0)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for name in (*FIGURE_NAMES, "figure-manifest.json"):
        assert not (OUTPUT_DIR / name).exists(), (
            f"Refusing overwrite: {OUTPUT_DIR / name}"
        )

    plt.rcParams.update({
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.labelsize": 10,
        "figure.figsize": (8.8, 5.2),
        "savefig.dpi": 170,
    })

    with tempfile.TemporaryDirectory(
        prefix="ech-main-v1-figures-"
    ) as temporary:
        temporary = Path(temporary)

        # Figure 1: Overall performance
        keys = ("precision", "recall", "f1", "fpr")
        labels = ("Precision", "Recall", "F1", "FPR")
        x = list(range(len(keys)))
        width = 0.35

        fig, ax = plt.subplots()

        bars_a = ax.bar(
            [i - width / 2 for i in x],
            [timing["overall"][k] for k in keys],
            width,
            label="Timing-only",
        )

        bars_b = ax.bar(
            [i + width / 2 for i in x],
            [multi["overall"][k] for k in keys],
            width,
            label="Multi-feature",
        )

        annotate_bars(ax, bars_a)
        annotate_bars(ax, bars_b)

        ax.set_xticks(x, labels)
        ax.set_ylim(0, 1.13)
        ax.set_ylabel("Score / Rate")
        ax.set_title("Overall Held-out Performance (N=110)")
        ax.legend()
        prepare_axis(ax)

        fig.text(
            0.5, 0.01,
            "FPR: lower is better. Beacon=50, Normal=60.",
            ha="center",
            fontsize=9,
        )

        fig.tight_layout(rect=(0, 0.05, 1, 1))
        save_figure(fig, temporary, FIGURE_NAMES[0])

        # Figure 2: Jitter vs Recall
        jitters = (0, 10, 30, 50, 70)
        jitter_labels = [str(j) for j in jitters]

        recall_t = [
            timing["by_jitter_with_shared_normal_60"][str(j)]["recall"]
            for j in jitters
        ]

        recall_m = [
            multi["by_jitter_with_shared_normal_60"][str(j)]["recall"]
            for j in jitters
        ]

        assert recall_t == recall_m == [1.0] * 5

        fig, ax = plt.subplots()

        ax.plot(
            jitters,
            recall_t,
            marker="o",
            linewidth=2,
            label="Timing-only = Multi-feature",
        )

        ax.set_ylim(0, 1.10)
        ax.set_xticks(jitters, jitter_labels)
        ax.set_xlabel("Beacon Jitter (%)")
        ax.set_ylabel("Recall")
        ax.set_title("Beacon Recall by Jitter")
        ax.legend(loc="lower left")
        prepare_axis(ax)

        fig.text(
            0.5, 0.01,
            "10 held-out Beacon trials per jitter level.",
            ha="center",
            fontsize=9,
        )

        fig.tight_layout(rect=(0, 0.05, 1, 1))
        save_figure(fig, temporary, FIGURE_NAMES[1])

        # Figure 3: Conditional F1 by Jitter
        f1_t = [
            timing["by_jitter_with_shared_normal_60"][str(j)]["f1"]
            for j in jitters
        ]

        f1_m = [
            multi["by_jitter_with_shared_normal_60"][str(j)]["f1"]
            for j in jitters
        ]

        fig, ax = plt.subplots()

        ax.plot(
            jitters,
            f1_t,
            marker="o",
            linewidth=2,
            label="Timing-only",
        )

        ax.plot(
            jitters,
            f1_m,
            marker="s",
            linewidth=2,
            label="Multi-feature",
        )

        ax.set_ylim(0, 1.0)
        ax.set_xticks(jitters, jitter_labels)
        ax.set_xlabel("Beacon Jitter (%)")
        ax.set_ylabel("Conditional F1")
        ax.set_title("Conditional F1 by Beacon Jitter")
        ax.legend()
        prepare_axis(ax)

        fig.text(
            0.5, 0.01,
            "Each condition: 10 Beacon + the same 60 Normal trials.",
            ha="center",
            fontsize=9,
        )

        fig.tight_layout(rect=(0, 0.05, 1, 1))
        save_figure(fig, temporary, FIGURE_NAMES[2])

        # Figure 4: Normal-profile false positive rates
        profiles = (
            "interactive-burst",
            "irregular-lognormal",
            "mixed-activity",
        )

        profile_labels = (
            "Interactive\nburst",
            "Irregular\nlognormal",
            "Mixed\nactivity",
        )

        fpr_t = [
            timing["by_normal_profile"][p]["fpr"]
            for p in profiles
        ]

        fpr_m = [
            multi["by_normal_profile"][p]["fpr"]
            for p in profiles
        ]

        x = list(range(len(profiles)))

        fig, ax = plt.subplots()

        bars_a = ax.bar(
            [i - width / 2 for i in x],
            fpr_t,
            width,
            label="Timing-only",
        )

        bars_b = ax.bar(
            [i + width / 2 for i in x],
            fpr_m,
            width,
            label="Multi-feature",
        )

        annotate_bars(ax, bars_a)
        annotate_bars(ax, bars_b)

        ax.set_xticks(x, profile_labels)
        ax.set_ylim(0, 0.70)
        ax.set_ylabel("False Positive Rate")
        ax.set_title("Held-out FPR by Normal Traffic Profile")
        ax.legend()
        prepare_axis(ax)

        fig.text(
            0.5, 0.01,
            "Profile sample sizes: 24 / 18 / 18.",
            ha="center",
            fontsize=9,
        )

        fig.tight_layout(rect=(0, 0.05, 1, 1))
        save_figure(fig, temporary, FIGURE_NAMES[3])

        # Figure 5: Inference latency
        inference = costs["inference"]

        inference_values = [
            inference["timing_only"]["median_batch_ms"],
            inference["multi_feature"]["median_batch_ms"],
        ]

        fig, ax = plt.subplots()

        bars = ax.bar(
            ["Timing-only", "Multi-feature"],
            inference_values,
            width=0.52,
        )

        annotate_bars(ax, bars, digits=6)

        ax.set_ylabel("Median Batch Time (ms)")
        ax.set_title("Pure Inference Cost: 110 Trials")
        ax.set_ylim(0, max(inference_values) * 1.18)
        prepare_axis(ax)

        fig.text(
            0.5, 0.01,
            "250 repetitions; excludes feature extraction and file I/O.",
            ha="center",
            fontsize=9,
        )

        fig.tight_layout(rect=(0, 0.05, 1, 1))
        save_figure(fig, temporary, FIGURE_NAMES[4])

        # Figure 6: Training / calibration cost
        calibration = costs["calibration"]

        calibration_values = [
            calibration["timing_only"]["median_ms"],
            calibration["multi_feature"]["median_ms"],
        ]

        fig, ax = plt.subplots()

        bars = ax.bar(
            ["Timing-only", "Multi-feature"],
            calibration_values,
            width=0.52,
        )

        annotate_bars(ax, bars, digits=6)

        ax.set_yscale("log")
        ax.set_ylim(0.01, 1000)
        ax.set_ylabel("Median Preparation Time (ms, log scale)")
        ax.set_title("Training / Calibration Preparation Cost")
        prepare_axis(ax)

        fig.text(
            0.5, 0.01,
            "Different workloads: 40 Normal vs 90 training samples.",
            ha="center",
            fontsize=9,
        )

        fig.tight_layout(rect=(0, 0.05, 1, 1))
        save_figure(fig, temporary, FIGURE_NAMES[5])

        # Verify all figures before publishing.
        for name in FIGURE_NAMES:
            path = temporary / name
            assert path.is_file() and path.stat().st_size > 0

        figures = {}

        for name in FIGURE_NAMES:
            source = temporary / name
            destination = OUTPUT_DIR / name

            # Exclusive creation: do not overwrite existing figures.
            with source.open("rb") as reader:
                with destination.open("xb") as writer:
                    shutil.copyfileobj(reader, writer)

            assert sha256(source) == sha256(destination)

            figures[name] = {
                "sha256": sha256(destination),
                "size_bytes": destination.stat().st_size,
            }

    manifest = {
        "schema_version": "1.0.0",
        "run_tag": RUN_TAG,
        "script_sha256": sha256(Path(__file__)),
        "environment": {
            "python": sys.version.split()[0],
            "matplotlib": matplotlib.__version__,
            "platform": platform.platform(),
        },
        "source_sha256": {
            str(path): expected
            for path, expected in EXPECTED_HASHES.items()
        },
        "figures": figures,
        "notes": [
            "All figures use frozen main-v1 evaluation results.",
            "Jitter-level Recall uses 10 Beacon trials per level.",
            "Conditional jitter F1 reuses the same 60 Normal trials.",
            "Calibration comparison uses different workloads.",
            "Latency results are Python microbenchmarks.",
            "No test-driven model or threshold changes.",
        ],
    }

    manifest_path = OUTPUT_DIR / "figure-manifest.json"

    with manifest_path.open("x", encoding="utf-8") as stream:
        json.dump(
            manifest,
            stream,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        stream.write("\n")

    print("PASS: Evaluation/Benchmark source SHA-256")
    print("PASS: Six paper figures generated")
    print("PASS: Figure SHA-256 manifest generated")
    print("PASS: Source results unchanged")

    print("\n=== Generated Figures ===")

    total = 0

    for name, metadata in figures.items():
        total += metadata["size_bytes"]
        print(
            f"{name}: "
            f"{metadata['size_bytes']} bytes "
            f"SHA={metadata['sha256']}"
        )

    print(f"\nTotal PNG bytes: {total}")
    print("Manifest SHA-256:", sha256(manifest_path))

if __name__ == "__main__":
    main()
