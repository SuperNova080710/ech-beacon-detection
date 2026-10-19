#!/usr/bin/env bash
# Extract and verify all 200 trials, refusing any incomplete raw dataset.
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT_DIR/docker-compose.yml" --project-directory "$ROOT_DIR")
RUN_TAG="${RUN_TAG:-main-v1}"

python3 "$ROOT_DIR/generator/experiment_plan.py" --run-tag "$RUN_TAG" \
  --start 1 --end 1 --format tsv >/dev/null

RAW="$ROOT_DIR/data/raw/$RUN_TAG"
PCAP="$ROOT_DIR/artifacts/pcap/$RUN_TAG"
PROCESSED="$ROOT_DIR/data/processed/$RUN_TAG"
[[ -f "$RAW/run-environment.txt" ]] || {
  echo "FAIL: missing experiment environment fingerprint" >&2
  exit 1
}
[[ -d "$PCAP" ]] || { echo "FAIL: raw PCAP directory missing" >&2; exit 1; }
[[ ! -e "$PROCESSED" ]] || {
  echo "FAIL: refusing processed overwrite; preserve existing results" >&2
  exit 1
}

echo "=== Verify entire 200-trial raw dataset before extraction ==="
"${COMPOSE[@]}" exec -T ech-client python3 \
  /workspace/generator/verify_main.py --run-tag "$RUN_TAG"

echo "=== Feature Extractor math unit tests ==="
"${COMPOSE[@]}" exec -T ech-client python3 \
  /workspace/extractor/test_feature_math.py

echo "=== Extract PCAP-level features for 200 trials ==="
"${COMPOSE[@]}" exec -T ech-client python3 \
  /workspace/extractor/extract_features.py --run-tag "$RUN_TAG"

echo "=== Verify processed feature/label/provenance ==="
"${COMPOSE[@]}" exec -T ech-client python3 \
  /workspace/extractor/verify_main_features.py --run-tag "$RUN_TAG"

HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
"${COMPOSE[@]}" exec -T ech-client sh -lc \
  "chown -R '$HOST_UID:$HOST_GID' '/data/processed/$RUN_TAG'" || true

echo "PASS: 200-trial raw/processed validation completed for RUN_TAG=$RUN_TAG"
echo "Processed output: $PROCESSED"
