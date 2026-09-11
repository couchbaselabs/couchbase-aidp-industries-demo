#!/usr/bin/env bash
# Exports the root CA(s) this Mac trusts for TLS-inspecting corporate
# proxies (Zscaler, Netskope, Palo Alto GlobalProtect, etc.) so
# `docker compose build` can trust them too — adapted from the reference
# Couchbase Agent Operations Manager and Procurement Command Center repos'
# script of the same name, extended to this app's three Docker build
# contexts (backend, mcp-servers, frontend).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIRS=(
  "$REPO_ROOT/backend/certs"
  "$REPO_ROOT/mcp-servers/certs"
  "$REPO_ROOT/frontend/certs"
)

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script currently only supports macOS (it uses the 'security' CLI to read the keychain)." >&2
  echo "On Linux, ask IT for your org's proxy root CA .pem and copy it manually to:" >&2
  for d in "${DEST_DIRS[@]}"; do echo "  ${d#$REPO_ROOT/}/corporate-ca.crt" >&2; done
  exit 1
fi

TMP_CERT="$(mktemp)"
trap 'rm -f "$TMP_CERT"' EXIT

echo "Exporting certificates from the System keychain..."
security find-certificate -a -p /Library/Keychains/System.keychain > "$TMP_CERT" 2>/dev/null || true

CERT_COUNT=$(grep -c "BEGIN CERTIFICATE" "$TMP_CERT" 2>/dev/null || echo 0)

if [[ "$CERT_COUNT" -eq 0 ]]; then
  echo "No certificates found in the System keychain — nothing to export."
  for d in "${DEST_DIRS[@]}"; do
    mkdir -p "$d"
    : > "$d/corporate-ca.crt"
  done
  exit 0
fi

for d in "${DEST_DIRS[@]}"; do
  mkdir -p "$d"
  cp "$TMP_CERT" "$d/corporate-ca.crt"
done

echo "Exported $CERT_COUNT certificate(s) to:"
for d in "${DEST_DIRS[@]}"; do echo "  ${d#$REPO_ROOT/}/corporate-ca.crt"; done
echo
echo "Now run: docker compose build --no-cache && docker compose up"
