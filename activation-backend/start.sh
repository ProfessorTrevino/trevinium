#!/usr/bin/env bash
set -euo pipefail

if [ -z "${ACTIVATION_SIGNING_PRIVATE_KEY_B64:-}" ] && [ -z "${ACTIVATION_SIGNING_PRIVATE_KEY:-}" ] && [ -z "${ACTIVATION_SIGNING_PRIVATE_KEY_PATH:-}" ]; then
  echo "FATAL: Set ACTIVATION_SIGNING_PRIVATE_KEY_B64 in Render → Environment"
  echo "Paste the one-line value from Desktop/RENDER_KEY_PASTE_THIS.txt"
  exit 1
fi

if [ -z "${GUMROAD_PRODUCT_PERMALINK:-}" ]; then
  export GUMROAD_PRODUCT_PERMALINK=kavwc
fi

exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-10000}"