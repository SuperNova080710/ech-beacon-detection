#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE=(docker compose -f "${ROOT_DIR}/docker-compose.yml" --project-directory "${ROOT_DIR}")

PROTECTED_NAME="${PROTECTED_NAME:-protected.ech.test}"
PUBLIC_NAME="${PUBLIC_NAME:-public.ech.test}"
EVIDENCE_DIR="${EVIDENCE_DIR:-${ROOT_DIR}/artifacts/evidence}"

PLAIN_PCAP="/captures/plain.pcap"
ECH_PCAP="/captures/ech.pcap"

mkdir -p "$EVIDENCE_DIR"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

extract_sni() {
  local pcap="$1"

  "${COMPOSE[@]}" exec -T packet-capture \
    tshark -r "$pcap" \
      -Y 'tls.handshake.type == 1' \
      -T fields \
      -e tls.handshake.extensions_server_name \
    | sed '/^[[:space:]]*$/d' \
    | sort -u
}

echo "=== tshark version ==="
"${COMPOSE[@]}" exec -T packet-capture tshark --version | sed -n '1,3p' \
  | tee "$EVIDENCE_DIR/tshark-version.txt"

echo
echo "=== ECH OFF ClientHello SNI ==="
PLAIN_SNI="$(extract_sni "$PLAIN_PCAP")"
printf '%s\n' "$PLAIN_SNI" | tee "$EVIDENCE_DIR/plain-clienthello-sni.txt"

if ! printf '%s\n' "$PLAIN_SNI" | grep -Fxq "$PROTECTED_NAME"; then
  fail "ECH OFF ClientHello does not expose protected SNI: $PROTECTED_NAME"
fi

echo "PASS: ECH OFF ClientHello exposes protected SNI: $PROTECTED_NAME"

echo
echo "=== ECH ON ClientHello SNI ==="
ECH_SNI="$(extract_sni "$ECH_PCAP")"
printf '%s\n' "$ECH_SNI" | tee "$EVIDENCE_DIR/ech-clienthello-sni.txt"

if printf '%s\n' "$ECH_SNI" | grep -Fxq "$PROTECTED_NAME"; then
  fail "ECH ON ClientHello exposes protected SNI: $PROTECTED_NAME"
fi

if ! printf '%s\n' "$ECH_SNI" | grep -Fxq "$PUBLIC_NAME"; then
  fail "ECH ON ClientHello does not expose expected outer SNI: $PUBLIC_NAME"
fi

echo "PASS: ECH ON ClientHello does not expose protected SNI: $PROTECTED_NAME"
echo "PASS: ECH ON ClientHello exposes public outer SNI: $PUBLIC_NAME"

echo
echo "=== Protocol-aware PCAP verification result ==="
echo "PASS: plain.pcap -> SNI ${PROTECTED_NAME}"
echo "PASS: ech.pcap   -> outer SNI ${PUBLIC_NAME}"
echo "PASS: ech.pcap   -> protected SNI not visible in parsed ClientHello"
echo "Evidence directory: ${EVIDENCE_DIR}"
