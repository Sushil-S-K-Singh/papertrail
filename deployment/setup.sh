#!/usr/bin/env bash
# PaperTrail — Production Deployment & Provisioning Script
# Target: Ubuntu Server 24.04 LTS
set -Eeuo pipefail

APP_DIR="/opt/papertrail"
SERVICE_USER="papertrail"
SERVICE_GROUP="papertrail"

echo "[*] Starting PaperTrail deployment on Ubuntu Server..."

if [[ "$EUID" -ne 0 ]]; then
  echo "[-] ERROR: This setup script must be executed with root/sudo privileges."
  exit 1
fi

# 1. Install system dependencies
echo "[*] Updating apt repositories and installing system prerequisites..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl sqlite3

# 2. Create unprivileged service user and group
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  echo "[*] Creating dedicated system service user: $SERVICE_USER..."
  useradd --system --shell /usr/sbin/nologin --home-dir "$APP_DIR" "$SERVICE_USER"
fi

# 3. Create target application directory structure
echo "[*] Creating application directories in $APP_DIR..."
install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0755 "$APP_DIR"
install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0755 "$APP_DIR/instance"

# 4. Copy application source files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "[*] Synchronizing application sources from $SCRIPT_DIR to $APP_DIR..."
cp -r "$SCRIPT_DIR/app" "$APP_DIR/"
cp -r "$SCRIPT_DIR/scripts" "$APP_DIR/"
cp "$SCRIPT_DIR/config.py" "$APP_DIR/"
cp "$SCRIPT_DIR/run.py" "$APP_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$APP_DIR/"

# 5. Create Python virtual environment and install pinned dependencies
echo "[*] Creating virtual environment and installing pinned dependencies..."
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
"$APP_DIR/.venv/bin/pip" install gunicorn

# 6. Initialize database and deterministic synthetic seed data
echo "[*] Initializing SQLite database and loading deterministic seed data..."
PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" -m scripts.init_db
PYTHONPATH="$APP_DIR" "$APP_DIR/.venv/bin/python" -m scripts.seed_db

# 7. Configure permissions
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$APP_DIR"
chmod 0600 "$APP_DIR/instance/"*.db 2>/dev/null || true

# 8. Install and configure systemd service
echo "[*] Installing systemd unit file..."
cat << 'EOF' > /etc/systemd/system/papertrail.service
[Unit]
Description=PaperTrail Enterprise Document Approval Portal
After=network.target

[Service]
Type=simple
User=papertrail
Group=papertrail
WorkingDirectory=/opt/papertrail
Environment="PATH=/opt/papertrail/.venv/bin:/usr/local/bin:/usr/bin"
Environment="FLASK_ENV=production"
Environment="PYTHONPATH=/opt/papertrail"
ExecStart=/opt/papertrail/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 run:app
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable papertrail
systemctl restart papertrail

# 9. Verify deployment
echo "[*] Verifying service status and health..."
sleep 2
systemctl is-active --quiet papertrail || {
  echo "[-] ERROR: PaperTrail service failed to start. Showing journal logs:"
  journalctl -u papertrail -n 30 --no-pager
  exit 1
}

echo "[+] PaperTrail deployed successfully and listening on http://127.0.0.1:5000"
echo "[+] Health check:"
curl -s http://127.0.0.1:5000/health || true
echo ""
