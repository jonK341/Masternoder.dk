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
  python scripts/mn2_enable_staking.py --addnode IP1,IP2  # persist peers + live-add (unstick mnsync)
  python scripts/mn2_enable_staking.py --watch            # read-only: poll mnsync→staking until FINISHED
  python scripts/mn2_enable_staking.py --watch --watch-min 30   # watch for 30 min
  python scripts/mn2_enable_staking.py --mnsync-finish    # force fresh peers to push a stuck MNW/BUDGET sync to FINISHED
  python scripts/mn2_enable_staking.py --mnsync-finish --ask-pass   # prompt SSH password (ignores .env DEPLOY_PASS)

Safe by default: no --apply == nothing is changed.

Success for --mnsync-finish / --watch requires getstakingstatus mnsync=true AND staking status=true
(stable for 3 consecutive polls). Staking-only blips with mnsync=false are not treated as done.
"""
import os
import re
import sys
import json
import time

import paramiko

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

APPLY = "--apply" in sys.argv
UNLOCK = "--unlock" in sys.argv
MNSYNC_RESET = "--mnsync-reset" in sys.argv
MNSYNC_NEXT = "--mnsync-next" in sys.argv


def _arg_value(flag: str):
    """Return the value following `flag` in argv, or None."""
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1].strip()
    return None


# --addnode 1.2.3.4  OR  --addnode 1.2.3.4,5.6.7.8,...  (peers that relay masternode data)
_addnode_raw = _arg_value("--addnode")
ADDNODES = [p.strip() for p in (_addnode_raw or "").split(",") if p.strip()]

WATCH = "--watch" in sys.argv          # poll mnsync/staking until FINISHED (read-only)
WATCH_MINUTES = int(_arg_value("--watch-min") or 20)

# Force fresh peer connections to break the MNW/BUDGET fulfilled-request deadlock
# (see masternode-sync.cpp: advance check sits after `if HasFulfilledRequest(...) continue`).
MNSYNC_FINISH = "--mnsync-finish" in sys.argv
ASK_PASS = "--ask-pass" in sys.argv


def sh(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def _parse_staking(gs: str):
    compact = (gs or "").replace(" ", "")
    mnsync_on = '"mnsync":true' in compact
    staking_on = '"stakingstatus":true' in compact or '"staking_status":true' in compact
    return mnsync_on, staking_on


def _parse_mnsync_status(st: str):
    asset = (re.search(r'"RequestedMasternodeAssets":(\d+)', st or "") or [None, "?"])[1]
    attempt = (re.search(r'"RequestedMasternodeAttempt":(\d+)', st or "") or [None, "?"])[1]
    fails = (re.search(r'"nCountFailures":(\d+)', st or "") or [None, "?"])[1]
    mnlist = (re.search(r'"countMasternodeList":(\d+)', st or "") or [None, "?"])[1]
    return asset, attempt, fails, mnlist


def _minting_ready(mnsync_on: bool, staking_on: bool, asset: str) -> bool:
    """Both getstakingstatus flags must be true for sustained minting."""
    return bool(mnsync_on and staking_on)


def _poll_line(label: str, st: str, gs: str, conns: str = "?") -> tuple:
    asset, attempt, fails, mnlist = _parse_mnsync_status(st)
    mnsync_on, staking_on = _parse_staking(gs)
    print(
        f"  {label} conns={conns}  asset={asset}  attempt={attempt}  mnList={mnlist}  "
        f"fails={fails}  mnsync={'TRUE' if mnsync_on else 'false'}  "
        f"staking={'TRUE' if staking_on else 'false'}"
    )
    return asset, mnsync_on, staking_on, fails


def _run_mnsync_next_until_finished(rpc, *, max_steps: int = 24) -> bool:
    """Step mnsync asset stages via RPC until FINISHED (999) or staking stable."""
    last = None
    stable_hits = 0
    for i in range(max_steps):
        rpc("mnsync", ["next"])
        time.sleep(3)
        st = rpc("mnsync", ["status"])
        gs = rpc("getstakingstatus")
        asset, mnsync_on, staking_on, _ = _poll_line(f"[next {i + 1:>2}]", st, gs)
        if _minting_ready(mnsync_on, staking_on, asset):
            stable_hits += 1
            if stable_hits >= 2:
                return True
        else:
            stable_hits = 0
        if asset == "999":
            time.sleep(5)
            gs = rpc("getstakingstatus")
            mnsync_on, staking_on = _parse_staking(gs)
            if mnsync_on and staking_on:
                return True
        if asset == last and i >= 2:
            err = rpc("mnsync", ["next"]) or ""
            if '"error"' in err and '"error":null' not in err:
                print("  (mnsync next stopped advancing — RPC may not support it on this build)")
                break
        last = asset
    return False


def _run_peer_finish_loop(rpc, sh, ssh, onetry_cmd: str, *, rounds: int = 36) -> bool:
    """Inject fresh onetry peers until mnsync+staking stable (3 consecutive polls)."""
    stable_hits = 0
    for i in range(rounds):
        sh(ssh, onetry_cmd)
        time.sleep(10)
        st = rpc("mnsync", ["status"])
        gs = rpc("getstakingstatus")
        conns = (re.search(r'"result":(\d+)', rpc("getconnectioncount") or "") or [None, "?"])[1]
        asset, mnsync_on, staking_on, fails = _poll_line(f"[{(i + 1) * 10:>4}s]", st, gs, conns)
        if fails not in ("0", "?", None):
            print("  !!! sync hit FAILED — check SPORK_8 masternode-payment-enforcement.")
            return False
        if _minting_ready(mnsync_on, staking_on, asset):
            stable_hits += 1
            if stable_hits >= 3:
                print("  >>> mnsync + staking stable — pool is minting.")
                return True
        else:
            stable_hits = 0
    return False


def main():
    host, user = deploy_host(), deploy_user()
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=require_deploy_pass(force_prompt=ASK_PASS), timeout=30)
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

    # Read-only watch loop: poll masternode-sync progress until it reaches FINISHED
    # (RequestedMasternodeAssets=999) and staking flips on. Changes nothing on the server.
    if WATCH:
        print(f"\n== watch mnsync/staking (read-only, up to {WATCH_MINUTES} min) ==")
        print("  done when mnsync=TRUE and staking=TRUE for 3 consecutive polls\n")
        iters = max(1, (WATCH_MINUTES * 60) // 20)
        stable_hits = 0
        for i in range(iters):
            st = rpc("mnsync", ["status"])
            gs = rpc("getstakingstatus")
            conns = (re.search(r'"result":(\d+)', rpc("getconnectioncount") or "") or [None, "?"])[1]
            asset, mnsync_on, staking_on, _ = _poll_line(f"[{i * 20:>4}s]", st, gs, conns)
            if _minting_ready(mnsync_on, staking_on, asset):
                stable_hits += 1
                if stable_hits >= 3:
                    print("\n  >>> mnsync + staking stable — pool is minting. Done.")
                    break
            else:
                stable_hits = 0
            if i < iters - 1:
                time.sleep(20)
        else:
            print("\n  [WARN] Watch ended without stable mnsync+staking.")
        print("\nmnsync status (final): " + (rpc("mnsync", ["status"]) or "(no response)"))
        print("getstakingstatus (final): " + (rpc("getstakingstatus") or "(no response)"))
        ssh.close()
        return 0

    print("\n-- getstakingstatus (before) --  (this build's staking RPC; getstakinginfo is not implemented)")
    print(rpc("getstakingstatus") or "(no response)")
    print("\n-- peers --  (need peers that relay the masternode list to finish mnsync)")
    print("connections: " + (rpc("getconnectioncount") or "(no response)"))
    print("known masternodes: " + (rpc("getmasternodecount") or "(no response)"))
    print("\n-- mnsync status --  (staking is gated on masternode sync finishing: mnsync must be true)")
    print(rpc("mnsync", ["status"]) or "(no response)")

    # Force-finish a deadlocked masternode sync by injecting FRESH peer connections.
    # The MNW/BUDGET stages only advance via a timeout branch that's unreachable once
    # every connected peer has fulfilled the sync request. A brand-new connection
    # (`addnode <ip> onetry`) is unfulfilled, so when the node has been parked > 25s
    # it immediately hits the timeout → GetNextAsset → walks MNW→BUDGET→FINISHED(999).
    if MNSYNC_FINISH:
        addnode_conf = (datadir.split("=", 1)[1].strip() + "/masternoder2.conf"
                        if "-datadir=" in (datadir or "") else "~/.masternoder2/masternoder2.conf")
        peers = [p for p in sh(ssh, f"grep -E '^addnode=' {addnode_conf} 2>/dev/null | cut -d= -f2").splitlines() if p.strip()]
        peers = [p.strip() for p in peers] or ADDNODES
        print(f"\n== mnsync finish (fresh peers + mnsync next if needed) ==")
        print(f"  peers to cycle: {len(peers)}")
        print("  note: 0 enabled masternodes on-chain causes sync reset loops — we require mnsync+staking stable.")
        sp = rpc("spork", ["show"])
        if not sp or '"error":null' not in sp:
            sp = rpc("spork", ["active"])
        print("  spork show: " + (sp or "(unsupported)"))
        # Persist a few peers so connection count stays >= 6 between onetry rounds.
        for ip in peers[:4]:
            rpc("addnode", [ip, "add"])
        onetry_cmd = "; ".join(
            f"curl -s -m 8 -u '{rpc_user}:{rpc_pass}' -H 'Content-Type: application/json' "
            f"-d '{{\"jsonrpc\":\"1.0\",\"id\":\"ops\",\"method\":\"addnode\",\"params\":[\"{ip}\",\"onetry\"]}}' {rpc_url}/ >/dev/null"
            for ip in peers
        ) if peers else "true"
        ok = _run_peer_finish_loop(rpc, sh, ssh, onetry_cmd, rounds=36)
        if not ok:
            print("\n== phase 2: mnsync next (step asset stages to FINISHED/999) ==")
            ok = _run_mnsync_next_until_finished(rpc)
        if not ok:
            print("\n== phase 3: peer finish loop again (after mnsync next) ==")
            ok = _run_peer_finish_loop(rpc, sh, ssh, onetry_cmd, rounds=18)
        print("\nmnsync status (final): " + (rpc("mnsync", ["status"]) or "(no response)"))
        print("getstakingstatus (final): " + (rpc("getstakingstatus") or "(no response)"))
        if ok:
            print("\nDone — mnsync and staking are both true (stable).")
        else:
            print("\n[WARN] Minting not stable yet. Try again in a few minutes or run:")
            print("  python scripts/mn2_enable_staking.py --watch --watch-min 30 --ask-pass")
        ssh.close()
        return 0 if ok else 1

    # Opt-in: add peers that serve masternode data so mnsync can complete.
    # Persists addnode= lines to the daemon's config (survives restarts) AND adds each live via RPC.
    if ADDNODES:
        import re as _re
        import time as _t
        addnode_conf = (datadir.split("=", 1)[1].strip() + "/masternoder2.conf"
                        if "-datadir=" in (datadir or "") else "~/.masternoder2/masternoder2.conf")
        print(f"\n== addnode x{len(ADDNODES)} (persist to {addnode_conf} + live add) ==")
        for ip in ADDNODES:
            print(sh(ssh, f"grep -q '^addnode={ip}$' {addnode_conf} 2>/dev/null || echo 'addnode={ip}' >> {addnode_conf}; echo 'persisted {ip}'"))
            r = rpc("addnode", [ip, "add"])
            print(f"  addnode {ip} (live): " + ("OK" if '"error":null' in (r or "") else (r or "(no response)")))
        # Poll while peers feed us the masternode list and mnsync climbs past stage 2.
        print("\n-- waiting up to ~3 min for masternode list + mnsync to advance --")
        for i in range(12):  # 12 x 15s = 180s
            _t.sleep(15)
            conns = rpc("getconnectioncount")
            st = rpc("mnsync", ["status"])
            gs = rpc("getstakingstatus")
            asset = (_re.search(r'"RequestedMasternodeAssets":(\d+)', st or "") or [None, "?"])[1]
            cnt = (_re.search(r'"countMasternodeList":(\d+)', st or "") or [None, "?"])[1]
            staking_on = '"stakingstatus":true' in (gs or "").replace(" ", "") or '"staking_status":true' in (gs or "").replace(" ", "")
            print(f"  [{(i+1)*15:>3}s] conns={conns}  asset={asset}  mnList={cnt}  staking={'TRUE' if staking_on else 'false'}")
            if staking_on:
                print("  >>> staking is now ACTIVE — pool is minting.")
                break
        print("\nmnsync status (final): " + (rpc("mnsync", ["status"]) or "(no response)"))
        print("getstakingstatus (final): " + (rpc("getstakingstatus") or "(no response)"))
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
        for i in range(20):  # ~20 x 15s = ~5 min (lets each stage time through to FINISHED)
            _t.sleep(15)
            st = rpc("mnsync", ["status"])
            gs = rpc("getstakingstatus")
            asset = (_re.search(r'"RequestedMasternodeAssets":(\d+)', st or "") or [None, "?"])[1]
            mnlist = (_re.search(r'"countMasternodeList":(\d+)', st or "") or [None, "?"])[1]
            winners = (_re.search(r'"countMasternodeWinner":(\d+)', st or "") or [None, "?"])[1]
            mnsync_on = '"mnsync":true' in (gs or "").replace(" ", "")
            staking_on = '"stakingstatus":true' in (gs or "").replace(" ", "") or '"staking_status":true' in (gs or "").replace(" ", "")
            print(f"  [{(i+1)*15:>3}s] asset={asset}  mnList={mnlist}  winners={winners}  mnsync={'TRUE' if mnsync_on else 'false'}  staking={'TRUE' if staking_on else 'false'}")
            if staking_on:
                print("  >>> staking is now ACTIVE — pool is minting.")
                break
        print("\n-- mnsync status (final) --")
        print(rpc("mnsync", ["status"]) or "(no response)")
        print("-- getstakingstatus (final) --")
        print(rpc("getstakingstatus") or "(no response)")

    # Opt-in: manually step the masternode-sync asset stages to FINISHED (999).
    # On a tiny network the winner/budget stages have no data to receive, so we push
    # past them. `mnsync next` is supported on most PIVX-style builds.
    if MNSYNC_NEXT:
        import re as _re
        import time as _t
        print("\n== mnsync next (stepping asset stages to FINISHED) ==")
        last = None
        for i in range(12):
            r = rpc("mnsync", ["next"])
            st = rpc("mnsync", ["status"])
            gs = rpc("getstakingstatus")
            asset = (_re.search(r'"RequestedMasternodeAssets":(\d+)', st or "") or [None, "?"])[1]
            staking_on = '"stakingstatus":true' in (gs or "").replace(" ", "") or '"staking_status":true' in (gs or "").replace(" ", "")
            note = r.strip() if (r and '"error":null' not in r) else ""
            print(f"  step {i+1}: RequestedMasternodeAssets={asset}  staking={'TRUE' if staking_on else 'false'}  {note}")
            if staking_on or asset == "999":
                if staking_on:
                    print("  >>> staking is now ACTIVE — pool is minting.")
                # one more status read after reaching 999 so staking flag settles
                _t.sleep(3)
                break
            if asset == last and i >= 2 and '"error"' in (r or ""):
                print("  (mnsync next not advancing / not supported on this build — stopping)")
                break
            last = asset
            _t.sleep(2)
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
