#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT_DIR/docker-compose.yml" --project-directory "$ROOT_DIR")
RUN_TAG="${RUN_TAG:-main-v1}"
START="${START:-1}"
END="${END:-10}"
EXECUTE="${EXECUTE:-0}"

PLAN="$(mktemp)"
trap 'rm -f "$PLAN"' EXIT
python3 "$ROOT_DIR/generator/experiment_plan.py" \
  --run-tag "$RUN_TAG" --start "$START" --end "$END" --format tsv > "$PLAN"

echo "=== Main experiment plan RUN_TAG=$RUN_TAG START=$START END=$END ==="
awk -F '\t' '{printf "%03d/200 %s\n",$1,$5}' "$PLAN"
if [[ "$EXECUTE" != "1" ]]; then
  [[ "$EXECUTE" == "0" ]] || { echo "FAIL: EXECUTE must be 0 or 1" >&2; exit 2; }
  echo "DRY RUN ONLY. Set EXECUTE=1 to collect real Native ECH PCAP."
  exit 0
fi

command -v flock >/dev/null || { echo "FAIL: flock is required" >&2; exit 1; }
LOCK="/tmp/ech-beacon-${UID}-$RUN_TAG.lock"
exec 9>"$LOCK"
flock -n 9 || { echo "FAIL: another capture batch for this RUN_TAG is running" >&2; exit 1; }

RAW="$ROOT_DIR/data/raw/$RUN_TAG"
PCAP="$ROOT_DIR/artifacts/pcap/$RUN_TAG"
PROCESSED="$ROOT_DIR/data/processed/$RUN_TAG"
ENV_FILE="$RAW/run-environment.txt"
[[ ! -e "$PROCESSED" ]] || { echo "FAIL: processed output exists; collection is locked" >&2; exit 1; }
if [[ ! -f "$ENV_FILE" ]] && { [[ -e "$RAW" ]] || [[ -e "$PCAP" ]]; }; then
  echo "FAIL: raw/PCAP already exists without environment fingerprint" >&2
  exit 1
fi

echo "=== Native ECH preflight ==="
bash "$ROOT_DIR/scripts/verify-ech.sh"
echo "=== Generator unit tests ==="
"${COMPOSE[@]}" exec -T ech-client python3 /workspace/generator/test_traffic_model.py

SOURCE_SHA="$(
  cd "$ROOT_DIR"
  sha256sum generator/config.json generator/generate.py generator/traffic_model.py \
    generator/finalize_manifest.py generator/experiment_plan.py generator/verify_main.py \
    scripts/run-traffic-trial.sh scripts/run-main-experiment.sh docker-compose.yml \
    docker/nginx.conf | sha256sum | awk '{print $1}'
)"
ECH_SHA="$("${COMPOSE[@]}" exec -T ech-client \
  sha256sum /work/ech/protected.ech.test.pem.ech | awk '{print $1}')"
if [[ ! "$SOURCE_SHA" =~ ^[0-9a-f]{64}$ || ! "$ECH_SHA" =~ ^[0-9a-f]{64}$ ]]; then
  echo "FAIL: unable to compute source/ECH fingerprint" >&2
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  grep -Fxq "generator_source_sha256=$SOURCE_SHA" "$ENV_FILE" || {
    echo "FAIL: generator/config changed; cannot mix trials in this RUN_TAG" >&2; exit 1;
  }
  grep -Fxq "ech_material_sha256=$ECH_SHA" "$ENV_FILE" || {
    echo "FAIL: ECH material changed; cannot mix trials in this RUN_TAG" >&2; exit 1;
  }
  grep -Fxq "capture_drain_seconds=${CAPTURE_DRAIN_SECONDS:-1}" "$ENV_FILE" || {
    echo "FAIL: capture drain setting changed" >&2; exit 1;
  }
else
  mkdir -p "$RAW"
  {
    echo "run_tag=$RUN_TAG"
    echo "started_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "git_commit=$(git -C "$ROOT_DIR" rev-parse HEAD)"
    echo "generator_source_sha256=$SOURCE_SHA"
    echo "ech_material_sha256=$ECH_SHA"
    echo "host_kernel=$(uname -sr)"
    echo "docker_version=$(docker --version)"
    echo "compose_version=$("${COMPOSE[@]}" version --short)"
    echo "python_version=$(python3 --version)"
    echo "extractor_feature_version=1.0.0"
    echo "capture_drain_seconds=${CAPTURE_DRAIN_SECONDS:-1}"
  } > "$ENV_FILE"
fi

COLLECTED=0
SKIPPED=0
while IFS=$'\t' read -r INDEX KIND VALUE NUMBER TRIAL_ID CATEGORY; do
  MANIFEST="$RAW/manifests/$TRIAL_ID.json"
  FLOW="$RAW/flow-metadata/$TRIAL_ID.csv"
  CAPTURE="$PCAP/$CATEGORY/$TRIAL_ID.pcap"
  PRESENT=0
  [[ -e "$MANIFEST" ]] && PRESENT=$((PRESENT+1))
  [[ -e "$FLOW" ]] && PRESENT=$((PRESENT+1))
  [[ -e "$CAPTURE" ]] && PRESENT=$((PRESENT+1))
  if [[ "$PRESENT" -eq 3 ]]; then
    echo "=== Verify completed trial before skip: $TRIAL_ID ==="
    "${COMPOSE[@]}" exec -T ech-client \
      python3 /workspace/generator/verify_main.py \
      --run-tag "$RUN_TAG" --trial-id "$TRIAL_ID"
    SKIPPED=$((SKIPPED+1))
    continue
  fi
  if [[ "$PRESENT" -ne 0 ]]; then
    echo "FAIL: incomplete $TRIAL_ID output; preserving evidence, refusing rerun" >&2
    exit 1
  fi

  echo "=== Collect $INDEX/200: $TRIAL_ID ==="
  RUN_TAG="$RUN_TAG" bash "$ROOT_DIR/scripts/run-traffic-trial.sh" "$KIND" "$VALUE" "$NUMBER"
  "${COMPOSE[@]}" exec -T ech-client \
    python3 /workspace/generator/verify_main.py \
    --run-tag "$RUN_TAG" --trial-id "$TRIAL_ID"
  COLLECTED=$((COLLECTED+1))
done < "$PLAN"

echo "BATCH PASS: RUN_TAG=$RUN_TAG newly_collected=$COLLECTED verified_existing=$SKIPPED"
if [[ "$END" == "200" ]]; then
  echo "=== Full 200-trial raw dataset check ==="
  "${COMPOSE[@]}" exec -T ech-client \
    python3 /workspace/generator/verify_main.py --run-tag "$RUN_TAG"
fi
