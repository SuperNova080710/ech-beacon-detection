#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE=(docker compose -f "${ROOT_DIR}/docker-compose.yml" --project-directory "${ROOT_DIR}")
RUN_TAG="${RUN_TAG:-pilot-v2}"
OVERWRITE="${OVERWRITE:-0}"

if [[ ! "$RUN_TAG" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "FAIL: invalid RUN_TAG: $RUN_TAG" >&2
  exit 2
fi

if [[ ! -d "${ROOT_DIR}/data/raw/${RUN_TAG}/manifests" ]]; then
  echo "FAIL: raw manifest directory not found: data/raw/${RUN_TAG}/manifests" >&2
  exit 1
fi

if [[ ! -d "${ROOT_DIR}/artifacts/pcap/${RUN_TAG}" ]]; then
  echo "FAIL: PCAP directory not found: artifacts/pcap/${RUN_TAG}" >&2
  exit 1
fi

echo "=== Feature math unit tests ==="
"${COMPOSE[@]}" exec -T ech-client \
  python3 /workspace/extractor/test_feature_math.py

echo
echo "=== PCAP feature extraction: ${RUN_TAG} ==="
EXTRACT_ARGS=(
  python3 /workspace/extractor/extract_features.py
  --run-tag "$RUN_TAG"
)
if [[ "$OVERWRITE" == "1" ]]; then
  EXTRACT_ARGS+=(--overwrite)
fi
"${COMPOSE[@]}" exec -T ech-client "${EXTRACT_ARGS[@]}"

echo
echo "=== Processed pilot verification ==="
"${COMPOSE[@]}" exec -T ech-client \
  python3 /workspace/extractor/verify_pilot_features.py \
  --run-tag "$RUN_TAG"

HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
"${COMPOSE[@]}" exec -T ech-client sh -lc \
  "chown -R '${HOST_UID}:${HOST_GID}' '/data/processed/${RUN_TAG}'" || true

echo
echo "PASS: Feature Extractor pilot completed for RUN_TAG=${RUN_TAG}"
echo "Processed data: ${ROOT_DIR}/data/processed/${RUN_TAG}"
