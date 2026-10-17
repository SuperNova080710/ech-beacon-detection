#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE=(docker compose -f "${ROOT_DIR}/docker-compose.yml" --project-directory "${ROOT_DIR}")

RUN_TAG="${RUN_TAG:-pilot-v1}"
PORT="${PORT:-8443}"
CAPTURE_DRAIN_SECONDS="${CAPTURE_DRAIN_SECONDS:-1}"

if [[ ! "$RUN_TAG" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "FAIL: invalid RUN_TAG: $RUN_TAG" >&2
  exit 2
fi

usage() {
  cat >&2 <<'EOF'
Usage:
  run-traffic-trial.sh beacon <jitter:0|10|30|50|70> <trial:1..20>
  run-traffic-trial.sh normal <interactive-burst|irregular-lognormal|mixed-activity> <trial>
EOF
  exit 2
}

[[ $# -eq 3 ]] || usage
KIND="$1"
VALUE="$2"
TRIAL="$3"
[[ "$TRIAL" =~ ^[0-9]+$ ]] || usage

GENERATOR_ARGS=()
CATEGORY=""
TRIAL_ID=""

if [[ "$KIND" == "beacon" ]]; then
  [[ "$VALUE" =~ ^(0|10|30|50|70)$ ]] || usage
  (( TRIAL >= 1 && TRIAL <= 20 )) || usage
  printf -v TRIAL_PADDED '%02d' "$TRIAL"
  printf -v JITTER_PADDED '%02d' "$VALUE"
  TRIAL_ID="beacon-j${JITTER_PADDED}-t${TRIAL_PADDED}"
  CATEGORY="beacon"
  GENERATOR_ARGS=(beacon --jitter "$VALUE" --trial "$TRIAL")
elif [[ "$KIND" == "normal" ]]; then
  case "$VALUE" in
    interactive-burst) MAX_TRIAL=40 ;;
    irregular-lognormal|mixed-activity) MAX_TRIAL=30 ;;
    *) usage ;;
  esac
  (( TRIAL >= 1 && TRIAL <= MAX_TRIAL )) || usage
  printf -v TRIAL_PADDED '%02d' "$TRIAL"
  TRIAL_ID="normal-${VALUE}-t${TRIAL_PADDED}"
  CATEGORY="normal"
  GENERATOR_ARGS=(normal --profile "$VALUE" --trial "$TRIAL")
else
  usage
fi

HOST_OUTPUT_ROOT="${ROOT_DIR}/data/raw/${RUN_TAG}"
CONTAINER_OUTPUT_ROOT="/data/raw/${RUN_TAG}"
HOST_PCAP_DIR="${ROOT_DIR}/artifacts/pcap/${RUN_TAG}/${CATEGORY}"
PCAP_RELATIVE="${RUN_TAG}/${CATEGORY}/${TRIAL_ID}.pcap"
HOST_PCAP="${ROOT_DIR}/artifacts/pcap/${PCAP_RELATIVE}"
CAPTURE_PCAP="/captures/${PCAP_RELATIVE}"
READONLY_PCAP="/pcap/${PCAP_RELATIVE}"
MANIFEST_HOST="${HOST_OUTPUT_ROOT}/manifests/${TRIAL_ID}.json"
PID_FILE="/tmp/traffic-trial-${TRIAL_ID}.pid"
CAPTURE_LOG="/tmp/traffic-trial-${TRIAL_ID}.log"

mkdir -p "${HOST_OUTPUT_ROOT}/manifests" "${HOST_OUTPUT_ROOT}/flow-metadata" "$HOST_PCAP_DIR"

if [[ -e "$MANIFEST_HOST" || -e "$HOST_PCAP" ]]; then
  echo "FAIL: trial output already exists for ${TRIAL_ID} in RUN_TAG=${RUN_TAG}" >&2
  echo "Use a new RUN_TAG to preserve the previous raw data." >&2
  exit 1
fi

CAPTURE_STARTED=0
stop_capture() {
  if [[ "$CAPTURE_STARTED" -eq 1 ]]; then
    "${COMPOSE[@]}" exec -T packet-capture sh -lc "
      if [ -s '${PID_FILE}' ]; then
        pid=\$(cat '${PID_FILE}')
        kill -INT \"\$pid\" 2>/dev/null || true
        attempts=0
        while kill -0 \"\$pid\" 2>/dev/null; do
          attempts=\$((attempts + 1))
          if [ \"\$attempts\" -ge 50 ]; then
            echo 'WARN: tcpdump did not exit after SIGINT; sending TERM' >&2
            kill -TERM \"\$pid\" 2>/dev/null || true
            break
          fi
          sleep 0.1
        done
      fi
    " || true
    CAPTURE_STARTED=0
  fi
}
trap stop_capture EXIT INT TERM

"${COMPOSE[@]}" exec -T packet-capture sh -lc \
  "mkdir -p '/captures/${RUN_TAG}/${CATEGORY}'; rm -f '${CAPTURE_PCAP}' '${PID_FILE}'; tcpdump -i any -U -s 0 -w '${CAPTURE_PCAP}' 'tcp port ${PORT}' >'${CAPTURE_LOG}' 2>&1 & echo \$! >'${PID_FILE}'"
CAPTURE_STARTED=1
sleep 1

set +e
"${COMPOSE[@]}" exec -T ech-client \
  python3 /workspace/generator/generate.py \
  --output-root "$CONTAINER_OUTPUT_ROOT" \
  --pcap-filename "artifacts/pcap/${PCAP_RELATIVE}" \
  "${GENERATOR_ARGS[@]}"
GENERATOR_STATUS=$?
set -e

# Give libpcap/tcpdump time to drain the final packets from the kernel capture buffer.
sleep "$CAPTURE_DRAIN_SECONDS"
stop_capture
trap - EXIT INT TERM

if [[ ! -s "$HOST_PCAP" ]]; then
  echo "FAIL: PCAP was not created: $HOST_PCAP" >&2
  exit 1
fi

PCAP_SHA256="$(sha256sum "$HOST_PCAP" | awk '{print $1}')"
PCAP_BYTES="$(stat -c '%s' "$HOST_PCAP")"

if [[ -f "$MANIFEST_HOST" ]]; then
  "${COMPOSE[@]}" exec -T ech-client \
    python3 /workspace/generator/finalize_manifest.py \
    --output-root "$CONTAINER_OUTPUT_ROOT" \
    --trial-id "$TRIAL_ID" \
    --pcap-filename "artifacts/pcap/${PCAP_RELATIVE}" \
    --pcap-path "$READONLY_PCAP" \
    --pcap-sha256 "$PCAP_SHA256" \
    --pcap-bytes "$PCAP_BYTES"
else
  echo "FAIL: manifest was not created: $MANIFEST_HOST" >&2
  exit 1
fi

HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
"${COMPOSE[@]}" exec -T ech-client sh -lc \
  "chown -R '${HOST_UID}:${HOST_GID}' '${CONTAINER_OUTPUT_ROOT}'" || true
"${COMPOSE[@]}" exec -T packet-capture sh -lc \
  "chown '${HOST_UID}:${HOST_GID}' '${CAPTURE_PCAP}'" || true

if [[ "$GENERATOR_STATUS" -ne 0 ]]; then
  echo "FAIL: generator reported a failed trial; raw data was preserved." >&2
  exit "$GENERATOR_STATUS"
fi

echo "PASS: ${TRIAL_ID}"
echo "Manifest: ${MANIFEST_HOST}"
echo "PCAP: ${HOST_PCAP}"
echo "SHA-256: ${PCAP_SHA256}"
