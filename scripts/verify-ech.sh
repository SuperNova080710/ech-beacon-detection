#!/usr/bin/env bash
set -Eeuo pipefail

PROTECTED_NAME="${PROTECTED_NAME:-protected.ech.test}"
PUBLIC_NAME="${PUBLIC_NAME:-public.ech.test}"
PORT="${PORT:-8443}"
ECH_FILE="/work/ech/${PROTECTED_NAME}.pem.ech"
EVIDENCE_DIR="${EVIDENCE_DIR:-artifacts/evidence}"

mkdir -p "$EVIDENCE_DIR"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

section() {
  echo
  echo "========================================================================"
  echo "$1"
  echo "========================================================================"
}

section "Container/version checks"
docker compose ps

docker compose exec -T ech-client openssl version | tee "$EVIDENCE_DIR/openssl-version.txt"
docker compose exec -T ech-client curl --version | tee "$EVIDENCE_DIR/curl-version.txt"
docker compose exec -T ech-nginx nginx -V 2>&1 | tee "$EVIDENCE_DIR/nginx-version.txt"

if ! grep -q 'OpenSSL 4\.0' "$EVIDENCE_DIR/openssl-version.txt"; then
  fail "ECH client is not using OpenSSL 4.0.x"
fi

if ! grep -qi 'ECH' "$EVIDENCE_DIR/curl-version.txt"; then
  fail "curl feature output does not report ECH support"
fi

section "Plain TLS request (ECH OFF)"
docker compose exec -T ech-client sh -lc "
  curl -skS --tlsv1.3 --ech false \
    -D /tmp/plain.headers \
    -o /tmp/plain.body \
    https://${PROTECTED_NAME}:${PORT}/ech-status
  cat /tmp/plain.headers
  cat /tmp/plain.body
" | tee "$EVIDENCE_DIR/plain-request.txt"

if ! grep -qi '^X-ECH-Status: NOT_TRIED' "$EVIDENCE_DIR/plain-request.txt"; then
  fail "plain request did not produce X-ECH-Status: NOT_TRIED"
fi

if ! grep -q '"server":"protected"' "$EVIDENCE_DIR/plain-request.txt"; then
  fail "plain request did not reach the protected virtual host"
fi

section "Native ECH request (ECH ON)"
docker compose exec -T ech-client sh -lc "
  set -eu
  ECHCONFIG=\$(awk '
    /^-----BEGIN ECHCONFIG-----/ {inside=1; next}
    /^-----END ECHCONFIG-----/ {inside=0; next}
    inside {gsub(/[[:space:]]/, \"\"); printf \"%s\", \$0}
    END {print \"\"}
  ' '${ECH_FILE}')

  test -n \"\$ECHCONFIG\"

  curl -skS --tlsv1.3 \
    --ech \"ecl:\${ECHCONFIG}\" \
    -D /tmp/ech.headers \
    -o /tmp/ech.body \
    https://${PROTECTED_NAME}:${PORT}/ech-status
  cat /tmp/ech.headers
  cat /tmp/ech.body
" | tee "$EVIDENCE_DIR/ech-request.txt"

if ! grep -qi '^X-ECH-Status: SUCCESS' "$EVIDENCE_DIR/ech-request.txt"; then
  fail "ECH request did not produce X-ECH-Status: SUCCESS"
fi

if ! grep -qi "^X-ECH-Outer-SNI: ${PUBLIC_NAME}" "$EVIDENCE_DIR/ech-request.txt"; then
  fail "ECH request did not expose the expected public outer SNI"
fi

if ! grep -q '"server":"protected"' "$EVIDENCE_DIR/ech-request.txt"; then
  fail "ECH request did not reach the protected virtual host"
fi

section "Recent NGINX ECH evidence"
docker compose logs --no-color --tail=80 ech-nginx \
  | tee "$EVIDENCE_DIR/nginx-ech-log.txt"

if ! grep -q 'ech_status="SUCCESS"' "$EVIDENCE_DIR/nginx-ech-log.txt"; then
  fail "NGINX log does not contain an ECH SUCCESS event"
fi

section "Verification result"
echo "PASS: ECH OFF -> NOT_TRIED"
echo "PASS: ECH ON  -> SUCCESS"
echo "PASS: outer SNI -> ${PUBLIC_NAME}"
echo "Evidence directory: ${EVIDENCE_DIR}"
