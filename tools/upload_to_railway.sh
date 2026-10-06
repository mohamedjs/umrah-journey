#!/usr/bin/env bash
# Build the game and upload it to Railway (project "umrah-journey", service "umrah-web").
#   bash tools/upload_to_railway.sh
# The service is a small Bun function that serves the files from the "game-files" bucket.
# Uploads need the secret in tools/.railway-upload-token (same value as the service's
# UPLOAD_TOKEN variable; never commit it). Run it from your own terminal (needs internet).
set -euo pipefail
cd "$(dirname "$0")/.."
URL="${URL:-https://umrah-web-production.up.railway.app}"
TOKEN="$(cat tools/.railway-upload-token)"
OUT="$(mktemp -d)"
npx vite build --outDir "$OUT" --emptyOutDir
cd "$OUT"
COUNT=$(find . -type f | wc -l)
echo "Uploading $COUNT files to $URL …"
# everything except index.html first, then index.html (so the new page never points at missing files)
find . -type f ! -name index.html | sed 's#^\./##' | xargs -P 8 -I{} sh -c \
  'curl -fsS --retry 3 -X PUT -H "x-upload-token: $0" --data-binary @"{}" "$1/__upload/{}" >/dev/null || { echo "✗ {}"; exit 255; }' "$TOKEN" "$URL"
curl -fsS --retry 3 -X PUT -H "x-upload-token: $TOKEN" --data-binary @index.html "$URL/__upload/index.html" >/dev/null
curl -fsS -X DELETE -H "x-upload-token: $TOKEN" "$URL/__upload/cache" >/dev/null
rm -rf "$OUT"
echo "Done ✓  $URL"
