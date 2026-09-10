#!/usr/bin/env python3
"""Apply funded collateral txids to masternode.conf and start via CLI."""
from __future__ import annotations

import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

# txids from fund run 2026-09-10T20:34Z in alias order from conf
FUND_MAP = [
    ("platformmn2", "41dee9badf4db13aef396f7ed44f91e3b72c2bfb4689ca3d27e99d6c6fd6bb3e", 0),
    ("platformmn3", "37e4fef38c0cc9bffff7aee60d143f05c3b71f16077106b49ec1f42a8bf2a70b", 0),
    ("platformmn4", "3283ede6ea5fd6c9cad2f7e73a0259485ed97f15be4956d59d01e1b80cfcc5f1", 0),
    ("platformmn5", "33e1982c35140dd84e6a4421f1f246d1a78c904ffee4e1c868147779c3fab1ad", 0),
    ("userSanderSb6296", "3e27855c49855480c330708151812283d54a2a27ba6bfb1097c4bce4ee45d4f6", 0),
    ("userSanderS876cc", "c41238a4ec1212f562588c5e50774df973b950bca6f5b56a53af65c419602884", 0),
    ("userSanderS2b088", "da533798fd05f6a72461fb2952208c67cd30f932296a65c9286bbd125e137117", 0),
    ("userSanderS96aaa", "31d5e1b3b0e10e0665bf6b2b2a2fdb93cddd2ecb5678e94e758f532e444dc700", 0),
    ("userSanderS753eb", "fbd1ddc2062465e3f274da2bc26d2bb13bfc739c914c4f0fd3cda4503682ccf5", 0),
    ("userSanderS1a37d", "31d96988e793cdf3c4cd324fbc5c9000ecf0f58910b736cfdbbcde87698cafaa", 0),
    ("userSanderS88b78", "862f551a346395037c7d018a060ed723ec4f7cc8a68dd97bdcffea08cb9ad92a", 0),
    ("userSanderS91552", "3d21b52532eac503024854090847eaeda2d6bbd6f3ae1df29aa2cba6fcbb6d9b", 0),
    ("userSanderScc486", "095f12caae458d43a650e7ba144a642511b30e0d7685162ed3789beceae3ebd0", 0),
    ("userSanderS4660b", "ccba9a2bbe974766450d0e57805065b761c27a7abaeed61a9bb92c5f73cf979a", 0),
    ("userSanderSa528e", "9a6a7ffb2552fd972e2bea939f54498326e6e52ec0c50cfcaba59849afcf97f7", 0),
    ("usershopmnpu2f55", "c777adb128ca74eee4ad8bf976fbd61208574c3270abc3b470f71c62c3661412", 0),
    ("usershopmnpu8eca", "f3d681e341ddd5e6b720d883f037888141f7a137ee351c6953dfe407bbf178cc", 0),
    ("userSanderSab8e4", "2288ab852812e6f4673ff25f0c1f3389bfe8ea03ebe3fcee1aecb02956ffe639", 0),
    ("userSanderSabede", "dc10f6bb85638d88340b0800dce28b1397c7bad175adb4dd0fbd91ac836582c4", 0),
    ("userSanderSa2960", "3d902abdf2e5ec801df457da19122a9bf9d247b6101ea10147c9974b0e7058bb", 0),
    ("userSanderSa3592", "6886214c9825e2180c5d8da5985a533957907489242ddd83a71bdae405679a7d", 0),
    ("userSanderSa06b8", "27da61693b7b1cb67cfb3c3632e5b1186ea2ee695e85532270db9656bdef3c95", 0),
    ("userSanderSa67ab", "5d901057e9dca131fe3af164e8ea97d03dae37dc2ce0afe4dbaa9e7e1c4fa574", 0),
    ("userSanderSa4940", "cce1b489692e7a94afc856f1560fcac0b4057a05e2c845ee8bb10735e2376024", 0),
    ("userSanderSa6427", "386998bf498ae392bbfae569fa74368ae008268f70b4fb13d41cb0bfaf9691d0", 0),
    ("userSanderSaedb2", "36eb8be6ed9195296fdbc8dffc6afa6605bbad5bb835123912274c85295669cb", 0),
    ("userSanderSa4e99", "e6396efb0ff9faebc61e81005b643e8a5ca08437f6f86afb76c10c21d0b52dff", 0),
    ("userSanderSa9eff", "a91f9a7fc5f54ccbd54fd3982cc239c1a6b6ab6c3c4afd797c74ae30ff1c13fa", 0),
    ("userSanderSaf834", "68efe3fcb7bbfcc0aabe78482f94896a0c74471ff606c3b025c32a43a4686899", 0),
    ("userSanderSafb75", "75fac35ecb137a781fd52d9b4a543055ab7bac29c035ab3a01cadeb77c62db86", 0),
    ("userSanderSa2f8d", "7902c370126d106a628370f42450937dcb559307ce121e6acbb7777a26cdf0d3", 0),
    ("userSanderSa157c", "bbc996b37ce12dd425b4457244a79436ac6b14ca0e998ed29c1698f8a6828325", 0),
    ("userSanderSa0b76", "fffddc9ad3c753b687cf501c6ece5f60fe7c2de0e4c15a765d00147e21894731", 0),
    ("userSanderSaba13", "bca4951893e13cd35971f9f890feb9db9a5e4613b10d9141140b82ac13953ea7", 0),
    ("userSanderSa5c94", "5949351d595c9ddacdb62bb03cf5f053e9a45df95263348c925a5d9a3b34e484", 0),
    ("userSanderSafeaa", "700f4b72aca58f86a05560164760b4436eab0fbc4c821dc6e885207eec22dded", 0),
    ("userSanderSa2301", "a6e4287165daeae743b119f12dee5bf4c5eb81519c89e7898b3c4b18dcb48016", 0),
    ("userSanderSa19d7", "cf94e5eaf398d04572eef4aab3a5e311188fc6b86e6872fb7bddf160ef116c0f", 0),
    ("userSanderSae47b", "e5a036b5217eb249ac0b392e28d5418305983aeb4bde07595b8975275b094182", 0),
]

REMOTE_PY = r'''
import json, os, shutil, subprocess, sys, time
from datetime import datetime, timezone

CONF = "/var/www/html/config/masternode.conf"
CLI = ["/opt/masternoder2d/masternoder2-cli", "-datadir=/var/www/html/config"]
MAP = __MAP__
MIN_CONF = __MIN_CONF__
WAIT_MIN = __WAIT_MIN__
DO_START = __DO_START__


def cli(*args):
    p = subprocess.run(CLI + list(args), capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip())
    out = (p.stdout or "").strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out

by_alias = {a: (t, v) for a, t, v in MAP}
lines_out = []
for line in open(CONF, encoding="utf-8"):
    s = line.strip()
    if not s or s.startswith("#"):
        lines_out.append(line if line.endswith("\n") else line + "\n")
        continue
    p = s.split()
    if len(p) < 5:
        lines_out.append(line)
        continue
    alias = p[0]
    txid, vout = by_alias.get(alias, (p[3], int(p[4])))
    lines_out.append(f"{alias} {p[1]} {p[2]} {txid} {vout}\n")

ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
shutil.copy2(CONF, CONF + f".bak-map-{ts}")
with open(CONF, "w", encoding="utf-8") as f:
    f.writelines(lines_out)
print("applied map to masternode.conf", len(MAP), "entries")

# wait for confirmations
deadline = time.time() + WAIT_MIN * 60
for i in range(1, 999):
    utxos = cli("listunspent", "0", "9999999")
    cols = [u for u in (utxos if isinstance(utxos, list) else [])
            if abs(float(u.get("amount") or 0) - 5000) < 1e-8]
    ok = sum(1 for u in cols if int(u.get("confirmations") or 0) >= MIN_CONF)
    print(f"wait {i}: 5000_utxos={len(cols)} confirmed>={MIN_CONF}: {ok}/{len(MAP)}")
    if ok >= len(MAP):
        break
    if time.time() > deadline:
        print(f"timeout after {WAIT_MIN}m with {ok} confirmed")
        break
    time.sleep(30)

subprocess.run(["systemctl", "restart", "masternoder2d"], check=False)
for i in range(40):
    time.sleep(5)
    try:
        h = cli("getblockcount")
        if isinstance(h, int) and h > 0:
            print("RPC ready", h)
            break
    except Exception:
        pass

conf = cli("listmasternodeconf")
if isinstance(conf, list):
    from collections import Counter
    c = Counter((r.get("status") or "?").upper() for r in conf)
    print("listmasternodeconf:", dict(c))

if DO_START:
    locked = cli("listlockunspent")
    if isinstance(locked, list) and locked:
        cli("lockunspent", "true", json.dumps(locked))
    cli("startmasternode", "local", "false")
    for alias, _, _ in MAP[:10]:
        try:
            r = cli("startmasternode", "alias", "false", alias)
            print(f"start {alias}: {r}")
        except Exception as e:
            print(f"start {alias}: ERR {e}")
    # start rest
    for alias, _, _ in MAP[10:]:
        try:
            r = cli("startmasternode", "alias", "false", alias)
            print(f"start {alias}: ok" if r is not False else f"start {alias}: false")
        except Exception as e:
            print(f"start {alias}: ERR {e}")

print("getmasternodecount:", json.dumps(cli("getmasternodecount")))
rows = cli("listmasternodes")
if isinstance(rows, list):
    en = sum(1 for r in rows if "ENABLE" in str(r.get("status", "")).upper())
    print(f"ENABLED={en}/{len(rows)}")
'''


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--wait-min", type=int, default=25)
    p.add_argument("--min-conf", type=int, default=10)
    p.add_argument("--no-start", action="store_true")
    args = p.parse_args()

    py = (
        REMOTE_PY.replace("__MAP__", repr(FUND_MAP))
        .replace("__MIN_CONF__", str(args.min_conf))
        .replace("__WAIT_MIN__", str(args.wait_min))
        .replace("__DO_START__", "False" if args.no_start else "True")
    )
    b64 = base64.b64encode(py.encode()).decode()
    cmd = f"bash -lc 'cd /var/www/html && python3 -c \"import base64; exec(base64.b64decode(\\\"{b64}\\\").decode())\"'"

    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    timeout = max(600, args.wait_min * 60 + 300)
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(stdout.read().decode(errors="replace"))
    err = stderr.read().decode(errors="replace")
    if err.strip():
        print("[stderr]", err)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
