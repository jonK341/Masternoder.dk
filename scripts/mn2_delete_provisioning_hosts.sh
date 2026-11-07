#!/usr/bin/env bash
# Remove queued / provisioning / planned hosts from the fleet registry (keeps active).
# Does NOT refund shop orders. Optionally strips matching masternode.conf aliases.
#
# Usage:
#   cd /var/www/html
#   bash scripts/mn2_delete_provisioning_hosts.sh              # dry-run counts
#   bash scripts/mn2_delete_provisioning_hosts.sh --apply      # execute
#   bash scripts/mn2_delete_provisioning_hosts.sh --apply --keep-conf   # registry only
set -euo pipefail

WEB="${WEB_ROOT:-/var/www/html}"
cd "$WEB"

APPLY=0
REMOVE_CONF=1
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --keep-conf) REMOVE_CONF=0 ;;
    -h|--help)
      sed -n '1,12p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

export PYTHONPATH="${WEB}${PYTHONPATH:+:$PYTHONPATH}"

python3 <<PY
import json
import sys
from scripts.daemon_env import load_dotenv

load_dotenv()
from backend.services.mn2_masternode_service import delete_pending_provisioning_hosts

dry = ${APPLY} == 0
remove_conf = ${REMOVE_CONF} != 0
out = delete_pending_provisioning_hosts(dry_run=dry, remove_conf=remove_conf)
print(json.dumps(out, indent=2))
if dry:
    print("\\nDry-run only. Re-run with --apply to delete.", file=sys.stderr)
    sys.exit(0 if out.get("removed_count") else 0)
sys.exit(0 if out.get("success") else 1)
PY
