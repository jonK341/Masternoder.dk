#!/bin/bash
# Run ON THE SERVER (ssh root@masternoder.dk) after pulling/deploying alias fix,
# or paste this whole file if git pull is not available yet.
set -euo pipefail
WEB="/var/www/html"
cd "$WEB"

echo "== config permissions (www-data must write masternode.conf) =="
bash "$WEB/scripts/mn2_fix_config_permissions.sh" --verify || bash "$WEB/scripts/mn2_fix_config_permissions.sh"

echo "== patch mn2_masternode_service.py (alias sanitization) =="
SVC="$WEB/backend/services/mn2_masternode_service.py"
python3 - <<'PY'
import re
from pathlib import Path

path = Path("/var/www/html/backend/services/mn2_masternode_service.py")
text = path.read_text(encoding="utf-8")
if "_alias_from_host_id" in text:
    print("already patched")
else:
    if "import re\n" not in text and "import re\r\n" not in text:
        text = text.replace("import os\n", "import os\nimport re\n", 1)
    insert = '''
def _alias_from_host_id(host_id: str) -> str:
    """Daemon alias: single token, no spaces (host ids may contain display names)."""
    alias = re.sub(r"[^a-zA-Z0-9]", "", (host_id or "").strip())[:16]
    if alias:
        return alias
    import uuid
    return "mn" + uuid.uuid4().hex[:14]


'''
    anchor = "def _format_masternode_conf_line("
    if anchor not in text:
        raise SystemExit("anchor not found — deploy full file from repo")
    text = text.replace(anchor, insert + anchor, 1)
    old = "    alias = host_id.replace(\"-\", \"\")[:16]"
    new = "    alias = _alias_from_host_id(host_id)"
    if old not in text:
        raise SystemExit("provision_host alias line not found")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)
PY

HOSTING="$WEB/backend/services/mn2_masternode_hosting_service.py"
python3 - <<'PY'
import re
from pathlib import Path
path = Path("/var/www/html/backend/services/mn2_masternode_hosting_service.py")
text = path.read_text(encoding="utf-8")
if "uid_slug" in text:
    print("hosting already patched")
else:
    if "import re\n" not in text:
        text = text.replace("import os\n", "import os\nimport re\n", 1)
    old = '        hid = f"user-{uid[:8]}-{uuid.uuid4().hex[:6]}"'
    new = '        uid_slug = re.sub(r"[^a-zA-Z0-9]", "", str(uid))[:8] or uuid.uuid4().hex[:8]\n        hid = f"user-{uid_slug}-{uuid.uuid4().hex[:6]}"'
    if old not in text:
        raise SystemExit("host id line not found")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched hosting")
PY

find "$WEB" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>/dev/null || true
sleep 8

SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\r"')
D="-datadir=/var/www/html/config"
CLI="/opt/masternoder2d/masternoder2-cli $D"

echo "== unlock wallet (if MN2_WALLET_PASSPHRASE set) =="
bash "$WEB/scripts/mn2_unlock_collateral.sh" 2>/dev/null || true

echo "== provision-pending (4 passes x limit=80) =="
for pass in 1 2 3 4; do
  echo "--- pass $pass ---"
  curl -s -X POST -H "X-Ops-Secret: $SECRET" \
    "http://127.0.0.1:5000/api/mn2/masternode/provision-pending?limit=80" | python3 -c "
import json,sys
d=json.load(sys.stdin)
res=d.get('results') or []
print('processed', d.get('processed'), 'active', sum(1 for r in res if r.get('status')=='active'),
      'prov', sum(1 for r in res if r.get('status')=='provisioning'),
      'err', sum(1 for r in res if r.get('error')))
for r in res[:3]:
    print(' ', r.get('host_id'), r.get('status'), (r.get('error') or r.get('message') or '')[:70])
"
done

echo "== start all aliases from conf =="
if [ -f "$WEB/scripts/mn2_start_masternode.py" ]; then
  cd "$WEB" && python3 scripts/mn2_start_masternode.py --all-from-conf
fi

echo "== counts =="
grep -c '^user' /var/www/html/config/masternode.conf 2>/dev/null || echo 0
$CLI listmasternodeconf 2>/dev/null | python3 -c "import json,sys; r=json.load(sys.stdin); print('aliases', len(r) if isinstance(r,list) else '?')"
$CLI listmasternodes 2>/dev/null | python3 -c "
import json,sys
rows=json.load(sys.stdin)
if not isinstance(rows,list): rows=[rows]
en=sum(1 for r in rows if 'ENABLE' in str(r.get('status','')).upper())
print('ENABLED', en, 'total', len(rows))
"
