#!/usr/bin/env python3
"""
Fix camgirls.masternoder.dk eiquidus homepage (empty tx table) and cam.masternoder.dk SSL.

Root cause: eiquidus v1.103 homepage JS calls /ext/getlasttxsajax/N but the API route is
/ext/getlasttxs/N — nginx rewrite restores compatibility without rebuilding eiquidus.

Also adds HTTP→HTTPS redirect for cam.masternoder.dk → camgirls.masternoder.dk (legacy alias).

  python scripts/fix_explorer_subdomains_remote.py --ask-pass
  python scripts/fix_explorer_subdomains_remote.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys

SNIPPET_PATH = "/etc/nginx/snippets/masternoder-explorer-compat.conf"
CAM_REDIRECT_PATH = "/etc/nginx/sites-available/cam-masternoder-redirect.conf"

SNIPPET = r"""# MasterNoder explorer compat — getlasttxsajax alias for eiquidus homepage DataTables
location ~ ^/ext/getlasttxsajax/(.*)$ {
    proxy_pass http://127.0.0.1:3000/ext/getlasttxs/$1$is_args$args;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
}
"""

CAM_REDIRECT = r"""# Legacy cam.masternoder.dk → canonical camgirls.masternoder.dk explorer
server {
    listen 80;
    listen [::]:80;
    server_name cam.masternoder.dk;
    return 301 https://camgirls.masternoder.dk$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name cam.masternoder.dk;

    ssl_certificate /etc/letsencrypt/live/camgirls.masternoder.dk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/camgirls.masternoder.dk/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    return 301 https://camgirls.masternoder.dk$request_uri;
}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix explorer subdomains on production server")
    parser.add_argument("--ask-pass", action="store_true", help="Prompt for SSH password")
    parser.add_argument("--dry-run", action="store_true", help="Print planned changes only")
    args = parser.parse_args()

    if args.dry_run:
        print("Would write:", SNIPPET_PATH)
        print(SNIPPET)
        print("Would write:", CAM_REDIRECT_PATH)
        print(CAM_REDIRECT)
        print("Would patch camgirls vhost to include snippet, enable cam redirect, reload nginx")
        print("Would verify: curl /ext/getlasttxsajax/0 and pm2 list explorer")
        return 0

    try:
        import paramiko
    except ImportError:
        print("paramiko required", file=sys.stderr)
        return 1

    try:
        import dotenv

        dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    except Exception:
        pass

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)

    remote_script = rf'''bash -s <<'ENDSCRIPT'
set -e

SNIPPET="{SNIPPET_PATH}"
CAM="{CAM_REDIRECT_PATH}"

echo "== write explorer compat snippet =="
sudo tee "$SNIPPET" > /dev/null <<'EOF'
{SNIPPET.rstrip()}
EOF

echo "== write cam.masternoder.dk redirect =="
sudo tee "$CAM" > /dev/null <<'EOF'
{CAM_REDIRECT.rstrip()}
EOF
sudo ln -sf "$CAM" /etc/nginx/sites-enabled/cam-masternoder-redirect.conf

echo "== patch camgirls vhost to include snippet =="
VHOST=""
for f in /etc/nginx/sites-enabled/*camgirls* /etc/nginx/sites-available/*camgirls*; do
  [ -f "$f" ] || continue
  VHOST="$f"
  break
done
if [ -z "$VHOST" ]; then
  echo "WARN: camgirls vhost not found — add manually: include {SNIPPET_PATH};"
else
  if ! grep -q 'masternoder-explorer-compat' "$VHOST" 2>/dev/null; then
    sudo sed -i '/server_name camgirls.masternoder.dk;/a \    include {SNIPPET_PATH};' "$VHOST"
    echo "OK patched $VHOST"
  else
    echo "OK snippet already included in $VHOST"
  fi
fi

echo "== cam.masternoder.dk TLS (optional redirect cert) =="
if [ ! -f /etc/letsencrypt/live/cam.masternoder.dk/fullchain.pem ]; then
  sudo certbot certonly --nginx -d cam.masternoder.dk --non-interactive --agree-tos -m admin@masternoder.dk 2>/dev/null \
    || echo "WARN: certbot for cam.masternoder.dk failed — run manually: sudo certbot --nginx -d cam.masternoder.dk"
fi
if [ -f /etc/letsencrypt/live/cam.masternoder.dk/fullchain.pem ]; then
  sudo sed -i 's|/etc/letsencrypt/live/camgirls.masternoder.dk/|/etc/letsencrypt/live/cam.masternoder.dk/|g' "$CAM"
fi

echo "== nginx test + reload =="
sudo nginx -t
sudo systemctl reload nginx

echo "== pm2 explorer =="
pm2 list 2>/dev/null | grep -E 'explorer|online|stopped' || true
pm2 restart explorer 2>/dev/null || echo "WARN: pm2 restart explorer failed (check pm2 list)"

echo "== verify getlasttxsajax alias =="
code=$(curl -s -o /dev/null -w '%{{http_code}}' 'http://127.0.0.1:3000/ext/getlasttxs/0')
echo "local getlasttxs HTTP $code"
code2=$(curl -s -o /dev/null -w '%{{http_code}}' -H 'Host: camgirls.masternoder.dk' 'http://127.0.0.1/ext/getlasttxsajax/0')
echo "nginx getlasttxsajax HTTP $code2"

echo "== verify cam redirect =="
curl -sI -H 'Host: cam.masternoder.dk' http://127.0.0.1/ | head -3 || true

echo DONE
ENDSCRIPT
'''

    _, stdout, stderr = ssh.exec_command(remote_script, timeout=120)
    out = (stdout.read() + stderr.read()).decode(errors="replace")
    print(out)
    code = stdout.channel.recv_exit_status()
    ssh.close()
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
