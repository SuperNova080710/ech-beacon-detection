#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE=(docker compose -f "${ROOT_DIR}/docker-compose.yml" --project-directory "${ROOT_DIR}")
RUN_TAG="${RUN_TAG:-pilot-v1}"

export RUN_TAG

if [[ ! "$RUN_TAG" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "FAIL: invalid RUN_TAG: $RUN_TAG" >&2
  exit 2
fi

if [[ -d "${ROOT_DIR}/data/raw/${RUN_TAG}" || -d "${ROOT_DIR}/artifacts/pcap/${RUN_TAG}" ]]; then
  echo "FAIL: RUN_TAG=${RUN_TAG} already has output." >&2
  echo "Use a new RUN_TAG instead of overwriting previous pilot raw data." >&2
  exit 1
fi

echo "=== Native ECH pre-check ==="
bash "${ROOT_DIR}/scripts/verify-ech.sh"

echo
echo "=== Generator model tests ==="
"${COMPOSE[@]}" exec -T ech-client \
  python3 /workspace/generator/test_traffic_model.py

echo
echo "=== Beacon pilot ==="
for jitter in 0 10 30 50 70; do
  bash "${ROOT_DIR}/scripts/run-traffic-trial.sh" beacon "$jitter" 1
done

echo
echo "=== Normal pilot ==="
for profile in interactive-burst irregular-lognormal mixed-activity; do
  bash "${ROOT_DIR}/scripts/run-traffic-trial.sh" normal "$profile" 1
done

echo
echo "=== Pilot verification ==="
"${COMPOSE[@]}" exec -T ech-client \
  python3 /workspace/generator/verify_pilot.py --run-tag "$RUN_TAG"

echo
echo "PASS: traffic generator pilot completed for RUN_TAG=${RUN_TAG}"
echo "Raw metadata: ${ROOT_DIR}/data/raw/${RUN_TAG}"
echo "PCAP: ${ROOT_DIR}/artifacts/pcap/${RUN_TAG}"
