#!/usr/bin/env bash
# PaperTrail — Database and Challenge State Reset Script
set -Eeuo pipefail

APP_DIR="/opt/papertrail"
SERVICE_NAME="papertrail"

echo "[*] Initiating PaperTrail database reset..."

# Determine context (installed in /opt or running locally)
if [[ -d "$APP_DIR" ]]; then
  BASE_DIR="$APP_DIR"
  IS_SYSTEM=1
else
  BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  IS_SYSTEM=0
fi

if [[ "$IS_SYSTEM" -eq 1 && command -v systemctl >/dev/null 2>&1 ]]; then
  echo "[*] Stopping $SERVICE_NAME service..."
  systemctl stop "$SERVICE_NAME" || true
fi

echo "[*] Removing mutable SQLite database..."
rm -f "$BASE_DIR/instance/papertrail.db"

echo "[*] Re-initializing database schema..."
if [[ -f "$BASE_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$BASE_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

PYTHONPATH="$BASE_DIR" "$PYTHON_BIN" -m scripts.init_db
PYTHONPATH="$BASE_DIR" "$PYTHON_BIN" -m scripts.seed_db

if [[ "$IS_SYSTEM" -eq 1 ]]; then
  chown -R papertrail:papertrail "$BASE_DIR/instance"
  chmod 0600 "$BASE_DIR/instance/"*.db 2>/dev/null || true
  echo "[*] Restarting $SERVICE_NAME service..."
  systemctl restart "$SERVICE_NAME"
  sleep 1
fi

echo "[+] PaperTrail database state has been cleanly restored to initial seed baseline."
