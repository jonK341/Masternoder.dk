#!/usr/bin/env python3
"""
MN2 daemon staking enabler (ops).

Discovers the running masternoder2d daemon on the server, then (with --apply)
ensures `staking=1` is in its config, restarts the daemon, and reports
getstakinginfo / getwalletinfo so you can confirm the pool is minting.

Usage (from repo root, same creds as deploy.py — DEPLOY_PASS in .env or prompt):
  python scripts/mn2_enable_staking.py            # discover only (read-only)
  python scripts/mn2_enable_staking.py --apply     # add staking=1 + restart daemon
  python scripts/mn2_enable_staking.py --apply --unlock   # also unlock wallet for staking
                                                          # (needs MN2_WALLET_PASSPHRASE env)

Safe by default: no --apply == nothing is changed.
"""
import os
import sys
import json

import paramiko

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

APPLY = "--apply" in sys.argv
UNLOCK = "--unlock" in sys.argv
MNSYNC_RESET = "--mnsync-reset" in sys.argv


def sh(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def main():
    host, user = deploy_host(), deploy_user()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=require_deploy_pass(), timeout=30)
    print(f"== Connected {user}@{host} ==\n")

    # 1) Find the running daemon + how it was launched
    print("-- running daemon (ps) --")
    print(sh(ssh, "ps aux | grep -i [m]asternoder2 || echo '(none)'"))
    print("\n-- listening 9332 --")
    print(sh(ssh, "ss -tlnp 2>/dev/null | grep 9332 || echo '(not listening)'"))

    # 2) Locate config + datadir. App connects via 127.0.0.1:9332; config is either
    #    ~/.masternoder2/masternoder2.conf or /var/www/html/config/masternoder2.conf.
    print("\n-- candidate config files --")
    conf_find = sh(ssh, "ls -1 ~/.masternoder2/masternoder2.conf /var/www/html/config/masternoder2.conf 2>/dev/null || true")
    print(conf_find or "(none found in standard spots)")
    # Figure out which datadir the running process uses
    datadir = sh(ssh, "ps aux | grep -i [m]asternoder2 | grep -o -- '-datadir=[^ ]*' | head -1 || true")
    print(f"\n-- process -datadir flag --\n{datadir or '(no -datadir flag → default ~/.masternoder2)'}")

    # 3) Read RPC creds from the app .env and probe staking RPCs
    print("\n-- RPC creds from /var/www/html/.env --")
    rpc_user = sh(ssh, "grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\\r\"'")
    rpc_pass = sh(ssh, "grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\\r\"'")
    rpc_url = sh(ssh, "grep '^MN2_RPC_URL=' /var/www/html/.env | cut -d= -f2- | tr -d '\\r\"'") or "http://127.0.0.1:9332"
    print(f"user={rpc_user!r} url={rpc_url!r} pass={'set' if rpc_pass else 'MISSING'}")

    def rpc(method, params=None):
        params = params or []
        body = json.dumps({"jsonrpc": "1.0", "id": "ops", "method": method, "params": params})
        cmd = (f"curl -s -m 15 -u '{rpc_user}:{rpc_pass}' "
               f"-d '{body}' -H 'Content-Type: application/json' {rpc_url}/")
        return sh(ssh, cmd)

    print("\n-- getstakingstatus (before) --  (this build's staking RPC; getstakinginfo is not implemented)")
    print(rpc("getstakingstatus") or "(no response)")
    print("\n-- mnsync status --  (staking is gated on masternode sync finishing: mnsync must be true)")
    print(rpc("mnsync", ["status"]) or "(no response)")
    print("\n-- getwalletinfo (before) --")
    wi = rpc("getwalletinfo")
    print(wi or "(no response)")

    # Opt-in: kick a stuck masternode sync (safe; just restarts the sync state machine).
    # On a tiny network the winners/budget stages have no data, so we poll while they
    # time-through toward RequestedMasternodeAssets=999 (FINISHED) and staking flips on.
    if MNSYNC_RESET:
        import re as _re
        import time as _t
        print("\n== mnsync reset (unsticking masternode sync) ==")
        print(rpc("mnsync", ["reset"]) or "(no response)")
        for i in range(9):  # ~9 x 15s = ~135s
            _t.sleep(15)
            st = rpc("mnsync", ["status"])
            gs = rpc("getstakingstatus")
            asset = (_re.search(r'"RequestedMasternodeAssets":(\d+)', st or "") or [None, "?"])[1]
            staking_on = '"staking status":true' in (gs or "").replace(" ", "") or '"staking_status":true' in (gs or "").replace(" ", "")
            print(f"  [{(i+1)*15:>3}s] RequestedMasternodeAssets={asset}  staking={'TRUE' if staking_on else 'false'}")
            if staking_on:
                print("  >>> staking is now ACTIVE — pool is minting.")
                break
        print("\n-- mnsync status (final) --")
        print(rpc("mnsync", ["status"]) or "(no response)")
        print("-- getstakingstatus (final) --")
        print(rpc("getstakingstatus") or "(no response)")

    # Determine the actual config path to edit (prefer the datadir the process uses)
    if "-datadir=" in (datadir or ""):
        ddir = datadir.split("=", 1)[1].strip()
        conf_path = f"{ddir}/masternoder2.conf"
    elif "/var/www/html/config/masternoder2.conf" in conf_find:
        conf_path = "/var/www/html/config/masternoder2.conf"
    else:
        conf_path = "~/.masternoder2/masternoder2.conf"
    print(f"\n== Target config for staking flag: {conf_path} ==")
    print("-- current staking-related lines --")
    print(sh(ssh, f"grep -nE 'staking|enablestaking' {conf_path} 2>/dev/null || echo '(no staking lines)'"))

    if not APPLY:
        print("\n[DRY-RUN] No changes made. Re-run with --apply to enable staking + restart.")
        ssh.close()
        return 0

    # 4) Apply: ensure staking=1 and enablestaking=1 (idempotent), keep a backup
    print("\n== APPLY: enabling staking in config ==")
    apply_cmd = (
        f"cp {conf_path} {conf_path}.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true; "
        f"touch {conf_path}; "
        f"grep -q '^staking=' {conf_path} && sed -i 's/^staking=.*/staking=1/' {conf_path} || echo 'staking=1' >> {conf_path}; "
        f"grep -q '^enablestaking=' {conf_path} && sed -i 's/^enablestaking=.*/enablestaking=1/' {conf_path} || echo 'enablestaking=1' >> {conf_path}"
    )
    print(sh(ssh, apply_cmd) or "(config updated)")
    print(sh(ssh, f"grep -nE 'staking|enablestaking' {conf_path}"))

    # 5) Restart the daemon. Prefer systemd if a unit exists; else relaunch the same way it runs now.
    print("\n== Restarting daemon ==")
    has_unit = sh(ssh, "systemctl list-unit-files 2>/dev/null | grep -i masternoder2d || true")
    if has_unit:
        print("systemd unit found → systemctl restart masternoder2d (a wallet daemon restart can take a while)")
        # Long timeout: stopping/starting flushes + reloads the wallet; 30s is not enough.
        print(sh(ssh, "systemctl restart masternoder2d 2>&1; sleep 12; systemctl is-active masternoder2d", timeout=180))
    else:
        # Reconstruct the launch command from the running process (binary + args), then relaunch via nohup.
        launch = sh(ssh, "ps aux | grep -i [m]asternoder2 | grep -v grep | head -1 | awk '{for(i=11;i<=NF;i++) printf $i\" \"; print \"\"}'")
        print(f"no systemd unit; current launch cmd:\n  {launch or '(unknown)'}")
        cli = (launch.split()[0].replace("masternoder2d", "masternoder2-cli")
               if launch else "masternoder2-cli")
        # Graceful stop via RPC, then relaunch with the same command line.
        print(sh(ssh, "fuser -k 9332/tcp 2>/dev/null; pkill -TERM -f '[m]asternoder2d' 2>/dev/null; sleep 6 || true"))
        if launch:
            print(sh(ssh, f"cd /root 2>/dev/null; nohup {launch} >> /var/log/masternoder2d.log 2>&1 & sleep 10; echo relaunched"))
        else:
            print("[WARN] Could not determine launch command. Start the daemon manually (see MN2_DAEMON_SETUP.md §4).")

    print("\n-- listening 9332 (after) --")
    print(sh(ssh, "sleep 5; ss -tlnp 2>/dev/null | grep 9332 || echo '(not listening yet — may still be loading wallet)'"))

    # 6) Optional: unlock wallet for staking only (needs passphrase via env, never logged)
    if UNLOCK:
        pw = (os.environ.get("MN2_WALLET_PASSPHRASE") or "").strip()
        if not pw:
            print("\n[UNLOCK] MN2_WALLET_PASSPHRASE not set; skipping wallet unlock.")
        else:
            print("\n== Unlocking wallet for staking (timeout 0 = until restart, staking-only) ==")
            body = json.dumps({"jsonrpc": "1.0", "id": "ops", "method": "walletpassphrase",
                               "params": [pw, 0, True]})
            cmd = (f"curl -s -m 15 -u '{rpc_user}:{rpc_pass}' -d '{body}' "
                   f"-H 'Content-Type: application/json' {rpc_url}/")
            res = sh(ssh, cmd)
            print("walletpassphrase: " + ("OK (no error)" if '"error":null' in res else res))

    print("\n-- getstakingstatus (after) --")
    print(rpc("getstakingstatus") or "(no response)")
    ssh.close()
    print("\nDone. staking_status:true means the daemon is minting. If false, check mintablecoins/")
    print("walletunlocked/enoughcoins in the output above (coins may need maturity/more confirmations).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
