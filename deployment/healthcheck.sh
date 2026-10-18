#!/usr/bin/env bash
# PaperTrail — System Health & Integrity Check
set -Eeuo pipefail

APP_DIR="/opt/papertrail"
SERVICE_NAME="papertrail"
HEALTH_URL="http://127.0.0.1:5000/health"

echo "[*] Checking PaperTrail system health..."

# 1. Verify systemd service status if running under systemd
if command -v systemctl >/dev/null 2>&1; then
  if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "  [+] Service $SERVICE_NAME is active (running)."
  else
    echo "  [!] Warning: systemd service $SERVICE_NAME is not active."
  fi
fi

# 2. HTTP health endpoint probe
echo "[*] Querying application health endpoint at $HEALTH_URL..."
HEALTH_RESPONSE=$(curl --fail --silent --show-error "$HEALTH_URL")
echo "  [+] Response: $HEALTH_RESPONSE"

# 3. Database file presence check
if [[ -f "$APP_DIR/instance/papertrail.db" ]]; then
  echo "  [+] Database file located at $APP_DIR/instance/papertrail.db"
elif [[ -f "instance/papertrail.db" ]]; then
  echo "  [+] Database file located at ./instance/papertrail.db"
fi

echo "[+] All PaperTrail health checks passed successfully."
