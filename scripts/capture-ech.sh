#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
COMPOSE=(docker compose -f "${ROOT_DIR}/docker-compose.yml" --project-directory "${ROOT_DIR}")

PROTECTED_NAME="${PROTECTED_NAME:-protected.ech.test}"
PUBLIC_NAME="${PUBLIC_NAME:-public.ech.test}"
PORT="${PORT:-8443}"
PCAP_DIR="${PCAP_DIR:-${ROOT_DIR}/artifacts/pcap}"
ECH_FILE="/work/ech/${PROTECTED_NAME}.pem.ech"

mkdir -p "$PCAP_DIR"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

capture_request() {
  local mode="$1"
  local pcap="/captures/${mode}.pcap"

  "${COMPOSE[@]}" exec -T packet-capture sh -lc \
    "rm -f '${pcap}' /tmp/tcpdump.pid; tcpdump -i any -U -s 0 -w '${pcap}' 'tcp port ${PORT}' >/tmp/tcpdump-${mode}.log 2>&1 & echo \$! >/tmp/tcpdump.pid"

  sleep 1

  if [ "$mode" = "plain" ]; then
    "${COMPOSE[@]}" exec -T ech-client \
      curl -skS --tlsv1.3 --ech false \
      -o /dev/null "https://${PROTECTED_NAME}:${PORT}/ech-status"
  else
    "${COMPOSE[@]}" exec -T ech-client sh -lc "
      set -eu
      ECHCONFIG=\$(awk '
        /^-----BEGIN ECHCONFIG-----/ {inside=1; next}
        /^-----END ECHCONFIG-----/ {inside=0; next}
        inside {gsub(/[[:space:]]/, \"\"); printf \"%s\", \$0}
        END {print \"\"}
      ' '${ECH_FILE}')
      test -n \"\$ECHCONFIG\"
      curl -skS --tlsv1.3 --ech \"ecl:\${ECHCONFIG}\" \
        -o /dev/null "https://${PROTECTED_NAME}:${PORT}/ech-status"
    "
  fi

  sleep 1
  "${COMPOSE[@]}" exec -T packet-capture sh -lc \
    'if [ -s /tmp/tcpdump.pid ]; then kill -INT "$(cat /tmp/tcpdump.pid)" 2>/dev/null || true; fi'
  sleep 1
}

echo "Capturing ECH OFF traffic..."
capture_request plain

echo "Capturing ECH ON traffic..."
capture_request ech

PLAIN_PCAP="${PCAP_DIR}/plain.pcap"
ECH_PCAP="${PCAP_DIR}/ech.pcap"

[ -s "$PLAIN_PCAP" ] || fail "plain.pcap was not created"
[ -s "$ECH_PCAP" ] || fail "ech.pcap was not created"

echo
echo "=== Coarse plaintext-SNI evidence ==="

if grep -aFq "$PROTECTED_NAME" "$PLAIN_PCAP"; then
  echo "PASS: ECH OFF capture contains protected SNI: $PROTECTED_NAME"
else
  fail "ECH OFF capture does not contain the protected SNI as plaintext"
fi

if grep -aFq "$PROTECTED_NAME" "$ECH_PCAP"; then
  fail "ECH ON capture still contains protected SNI as plaintext"
else
  echo "PASS: ECH ON capture does not contain protected SNI as plaintext"
fi

if grep -aFq "$PUBLIC_NAME" "$ECH_PCAP"; then
  echo "PASS: ECH ON capture contains public outer SNI: $PUBLIC_NAME"
else
  echo "WARN: public outer SNI was not found by raw byte search; use a protocol-aware parser for confirmation"
fi

echo
echo "PCAP files:"
ls -lh "$PLAIN_PCAP" "$ECH_PCAP"
