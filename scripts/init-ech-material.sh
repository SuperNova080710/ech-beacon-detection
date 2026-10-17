#!/usr/bin/env bash
set -Eeuo pipefail

PROTECTED_NAME="${PROTECTED_NAME:-protected.ech.test}"
PUBLIC_NAME="${PUBLIC_NAME:-public.ech.test}"
FORCE_REGENERATE="${FORCE_REGENERATE:-0}"

CERT_DIR="/work/certs"
ECH_DIR="/work/ech"
CERT_FILE="${CERT_DIR}/fullchain.pem"
KEY_FILE="${CERT_DIR}/privkey.pem"
ECH_FILE="${ECH_DIR}/${PROTECTED_NAME}.pem.ech"

mkdir -p "$CERT_DIR" "$ECH_DIR"

need_generate=0
for file in "$CERT_FILE" "$KEY_FILE" "$ECH_FILE"; do
  if [ ! -s "$file" ]; then
    need_generate=1
  fi
done

if [ "$FORCE_REGENERATE" = "1" ]; then
  need_generate=1
fi

if [ "$need_generate" = "1" ]; then
  echo "[bootstrap] generating local TLS certificate for ${PROTECTED_NAME} / ${PUBLIC_NAME}"
  rm -f "$CERT_FILE" "$KEY_FILE" "$ECH_FILE"

  openssl req \
    -x509 \
    -newkey rsa:2048 \
    -sha256 \
    -nodes \
    -days 30 \
    -subj "/CN=${PROTECTED_NAME}" \
    -addext "subjectAltName=DNS:${PROTECTED_NAME},DNS:${PUBLIC_NAME}" \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE"

  echo "[bootstrap] generating RFC 9849 ECHConfig for public_name=${PUBLIC_NAME}"
  openssl ech \
    -public_name "$PUBLIC_NAME" \
    -out "$ECH_FILE"
else
  echo "[bootstrap] existing TLS/ECH material found; reusing named-volume contents"
fi

# NGINX runs as uid/gid 101 inside the lab image.
chown 101:101 "$CERT_FILE" "$KEY_FILE" "$ECH_FILE"
chmod 0644 "$CERT_FILE"
chmod 0600 "$KEY_FILE" "$ECH_FILE"

echo
openssl version
echo
openssl x509 -in "$CERT_FILE" -noout -subject -issuer -dates -ext subjectAltName
echo
openssl ech -in "$ECH_FILE" -text >/tmp/ech-info.txt
sed -n '1,40p' /tmp/ech-info.txt

echo
printf '[bootstrap] ready: %s\n' "$ECH_FILE"
