#!/usr/bin/env bash
set -euo pipefail

APP_NAME="agri-data-trust"
SERVER_HOST="${SERVER_HOST:-39.106.238.181}"
SERVER_USER="${SERVER_USER:-root}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/agri_data_trust_deploy}"
REMOTE_DIR="${REMOTE_DIR:-/opt/agri-data-trust}"
REMOTE_ARCHIVE="/tmp/${APP_NAME}-deploy.tar.gz"
PUBLIC_URL="${PUBLIC_URL:-http://39.106.238.181/agri-trust/}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE="$(mktemp "/tmp/${APP_NAME}.XXXXXX.tar.gz")"

cleanup() {
  rm -f "$ARCHIVE"
}
trap cleanup EXIT

if [[ ! -f "$SSH_KEY" ]]; then
  echo "SSH key not found: $SSH_KEY" >&2
  exit 1
fi

echo "==> Packaging $APP_NAME"
COPYFILE_DISABLE=1 tar \
  --exclude=".venv" \
  --exclude="reports/*" \
  --exclude=".mplconfig" \
  --exclude=".cache" \
  --exclude="__pycache__" \
  --exclude="*.pyc" \
  -czf "$ARCHIVE" \
  -C "$(dirname "$PROJECT_ROOT")" \
  "$(basename "$PROJECT_ROOT")"

echo "==> Uploading archive to ${SERVER_USER}@${SERVER_HOST}"
scp -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "$ARCHIVE" "${SERVER_USER}@${SERVER_HOST}:${REMOTE_ARCHIVE}"

echo "==> Deploying on server"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "${SERVER_USER}@${SERVER_HOST}" \
  "REMOTE_DIR='${REMOTE_DIR}' REMOTE_ARCHIVE='${REMOTE_ARCHIVE}' PIP_INDEX_URL='${PIP_INDEX_URL}' bash -s" <<'REMOTE'
set -euo pipefail

STAMP="$(date +%Y%m%d_%H%M%S)"
APP_PARENT="$(dirname "$REMOTE_DIR")"
APP_BASENAME="$(basename "$REMOTE_DIR")"
BACKUP_DIR="${REMOTE_DIR}.backup.${STAMP}"
VHOST="/www/server/panel/vhost/nginx/39.106.238.181.conf"

mkdir -p "$APP_PARENT"

if [[ -d "$REMOTE_DIR" ]]; then
  mv "$REMOTE_DIR" "$BACKUP_DIR"
fi

tar -xzf "$REMOTE_ARCHIVE" -C "$APP_PARENT"
if [[ "$APP_PARENT/$APP_BASENAME" != "$REMOTE_DIR" ]]; then
  mv "$APP_PARENT/$APP_BASENAME" "$REMOTE_DIR"
fi

cd "$REMOTE_DIR"
find . -name '._*' -delete

if [[ -d "${BACKUP_DIR}/.venv" ]]; then
  cp -a "${BACKUP_DIR}/.venv" "$REMOTE_DIR/.venv"
fi

if [[ ! -x ".venv/bin/python" ]]; then
  if ! python3 -m venv .venv; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3.10-venv python3-pip
    python3 -m venv .venv
  fi
fi

.venv/bin/python -m pip install --upgrade pip setuptools wheel -i "$PIP_INDEX_URL"
.venv/bin/pip install -r requirements.txt -i "$PIP_INDEX_URL" --timeout 120

mkdir -p reports .mplconfig .cache
find reports -maxdepth 1 -type f -name '*.md' -delete

cat >/etc/systemd/system/agri-data-trust.service <<'SERVICE'
[Unit]
Description=Agri Data Trust Streamlit MVP
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/agri-data-trust
Environment=STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
Environment=MPLCONFIGDIR=/opt/agri-data-trust/.mplconfig
Environment=XDG_CACHE_HOME=/opt/agri-data-trust/.cache
ExecStart=/opt/agri-data-trust/.venv/bin/streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --server.baseUrlPath agri-trust --browser.gatherUsageStats false
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable agri-data-trust >/dev/null
systemctl restart agri-data-trust

if [[ -f "$VHOST" ]] && ! grep -q 'location \^~ /agri-trust/' "$VHOST"; then
  python3 <<'PY'
from pathlib import Path
from datetime import datetime

p = Path("/www/server/panel/vhost/nginx/39.106.238.181.conf")
text = p.read_text()
block = """    # Agri Data Trust Streamlit app
    location = /agri-trust {
        return 301 /agri-trust/;
    }

    location ^~ /agri-trust/ {
        proxy_pass http://127.0.0.1:8501/agri-trust/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_buffering off;
    }

"""
marker = "    #SSL-START"
if marker not in text:
    raise SystemExit("Nginx insertion marker not found")
backup = p.with_suffix(p.suffix + f".bak.{datetime.now():%Y%m%d_%H%M%S}")
backup.write_text(text)
p.write_text(text.replace(marker, block + marker, 1))
PY
fi

if [[ -f "$VHOST" ]] && ! grep -q 'ayaumathxu.top' "$VHOST"; then
  python3 <<'PY'
from pathlib import Path
p = Path("/www/server/panel/vhost/nginx/39.106.238.181.conf")
text = p.read_text()
text = text.replace(
    "server_name 39.106.238.181;",
    "server_name 39.106.238.181 ayaumathxu.top www.ayaumathxu.top;",
)
p.write_text(text)
PY
fi

nginx -t
nginx -s reload || systemctl reload nginx

sleep 5
systemctl --no-pager --full status agri-data-trust | sed -n '1,30p'
curl -fsSI -H 'Host: 39.106.238.181' http://127.0.0.1/agri-trust/ >/dev/null
echo "Server deployment OK"
REMOTE

echo "==> Verifying public URL"
curl -fsSI --max-time 20 "$PUBLIC_URL" >/dev/null
echo "Deploy complete: $PUBLIC_URL"
