#!/usr/bin/env python3
import os, sys, subprocess
ROOT = "/var/www/html"
sys.path.insert(0, ROOT)
os.chdir(ROOT)
for line in open(".env", encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    k, v = k.strip(), v.strip().strip(chr(34)).strip(chr(39))
    if k and k not in os.environ:
        os.environ[k] = v
os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")
try:
    ip = subprocess.check_output(["curl", "-4", "-s", "--max-time", "8", "ifconfig.me"], text=True).strip()
except Exception as e:
    ip = f"error:{e}"
print("server_outbound_ipv4=", ip)
import scripts.remote_vault_import as _rvi  # noqa: F401
from backend.services import exchange_secrets_vault_service as vault
from backend.services.exchange_venue_api_service import venue_has_credentials, get_account_balance
from backend.services.external_exchange_connector_service import fetch_ticker
print("encryption_available=", vault.encryption_available())
names = vault.list_secret_names()
print("xeggex_vault_keys=", "xeggex_api_key" in names and "xeggex_api_secret" in names)
print("venue_has_credentials(xeggex)=", venue_has_credentials("xeggex"))
t = fetch_ticker("xeggex", "DOGE")
print("xeggex_ticker_doge=", {k: t.get(k) for k in ("success", "bid", "ask", "last", "error") if k in t})
bal = get_account_balance("xeggex", dry_run=False)
print("xeggex_account=", {"success": bal.get("success"), "status_code": bal.get("status_code"), "error": bal.get("error")})
