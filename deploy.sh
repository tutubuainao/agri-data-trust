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
MAINTENANCE_FLAG="/tmp/agri_data_trust_maintenance"
MAINTENANCE_PAGE="/www/wwwroot/39.106.238.181/agri-trust-updating.html"

cleanup_remote() {
  rm -f "$MAINTENANCE_FLAG"
}
trap cleanup_remote EXIT

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
Description=Agri Data Trust FastAPI App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/agri-data-trust
Environment=MPLCONFIGDIR=/opt/agri-data-trust/.mplconfig
Environment=XDG_CACHE_HOME=/opt/agri-data-trust/.cache
ExecStart=/opt/agri-data-trust/.venv/bin/uvicorn api_app:app --host 127.0.0.1 --port 8501
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

cat >"$MAINTENANCE_PAGE" <<'HTML'
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>系统正在更新</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f4f7f4;
      color: #111827;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
    }
    main {
      width: min(560px, calc(100% - 36px));
      padding: 34px;
      border: 1px solid #d9e1dc;
      border-radius: 12px;
      background: #ffffff;
      box-shadow: 0 24px 70px rgba(17, 24, 39, 0.10);
    }
    h1 { margin: 0; font-size: 2rem; }
    p { margin: 14px 0 0; color: #5f6f66; line-height: 1.7; }
    a { display: inline-flex; margin-top: 22px; color: #14532d; font-weight: 800; text-decoration: none; }
  </style>
</head>
<body>
  <main>
    <h1>系统正在更新</h1>
    <p>农业数据可信度检测系统正在发布新版本，通常几十秒内完成。请稍后刷新页面。</p>
    <a href="/agri-trust/">重新打开检测系统</a>
  </main>
</body>
</html>
HTML

if [[ -f "$VHOST" ]] && ! grep -q 'location \^~ /agri-trust/' "$VHOST"; then
  python3 <<'PY'
from pathlib import Path
from datetime import datetime

p = Path("/www/server/panel/vhost/nginx/39.106.238.181.conf")
text = p.read_text()
block = """    # Agri Data Trust FastAPI app
    error_page 503 /agri-trust-updating.html;

    location = /agri-trust-updating.html {
        root /www/wwwroot/39.106.238.181;
    }

    location = /agri-trust {
        return 301 /agri-trust/;
    }

    location ^~ /agri-trust/ {
        if (-f /tmp/agri_data_trust_maintenance) {
            return 503;
        }
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

if [[ -f "$VHOST" ]] && ! grep -q 'agri_data_trust_maintenance' "$VHOST"; then
  python3 <<'PY'
from pathlib import Path
from datetime import datetime

p = Path("/www/server/panel/vhost/nginx/39.106.238.181.conf")
text = p.read_text()
backup = p.with_suffix(p.suffix + f".bak.{datetime.now():%Y%m%d_%H%M%S}")
backup.write_text(text)

if "error_page 503 /agri-trust-updating.html;" not in text:
    marker = "    location = /agri-trust"
    text = text.replace(
        marker,
        "    error_page 503 /agri-trust-updating.html;\n\n"
        "    location = /agri-trust-updating.html {\n"
        "        root /www/wwwroot/39.106.238.181;\n"
        "    }\n\n"
        + marker,
        1,
    )

needle = "    location ^~ /agri-trust/ {\n"
guard = (
    "    location ^~ /agri-trust/ {\n"
    "        if (-f /tmp/agri_data_trust_maintenance) {\n"
    "            return 503;\n"
    "        }\n"
)
if needle not in text:
    raise SystemExit("Agri trust nginx location not found")
text = text.replace(needle, guard, 1)
p.write_text(text)
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

touch "$MAINTENANCE_FLAG"
systemctl daemon-reload
systemctl enable agri-data-trust >/dev/null
systemctl restart agri-data-trust

sleep 12
systemctl --no-pager --full status agri-data-trust | sed -n '1,30p'
rm -f "$MAINTENANCE_FLAG"
curl -fsSI -H 'Host: 39.106.238.181' http://127.0.0.1/agri-trust/ >/dev/null
curl -fsSI -H 'Host: 39.106.238.181' http://127.0.0.1/agri-trust/methodology >/dev/null
echo "Server deployment OK"
REMOTE

echo "==> Verifying public URL"
curl -fsSI --max-time 20 "$PUBLIC_URL" >/dev/null
curl -fsSI --max-time 20 "${PUBLIC_URL%/}/methodology" >/dev/null
echo "Deploy complete: $PUBLIC_URL"
