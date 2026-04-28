# Step-by-step: MN2 secret password and daemon config path (`/config`)

Use this checklist to set the MN2 RPC password once and point the daemon at the project’s **config** folder (deployed as `/var/www/html/config` on the server).

---

## Overview


| Step | What                               | Where                                                   |
| ---- | ---------------------------------- | ------------------------------------------------------- |
| 1    | Set RPC password in project config | Local: `config/masternoder2.conf`                       |
| 2    | Set same password in app env       | Local: `.env` → `MN2_RPC_PASSWORD`                      |
| 3    | Deploy config + .env to server     | `config/` and `.env` → `/var/www/html/`                 |
| 4    | Daemon uses `/config` on server    | Server: run daemon with `-datadir=/var/www/html/config` |
| 5    | Restart app so it loads new .env   | `systemctl restart uwsgi-vidgenerator`                  |
| 6    | Verify                             | Deposit-address API and RPC health                      |


---

## Step 0 — Verify locally (optional)

After you complete Steps 1 and 2 (same password in `config/masternoder2.conf` and `.env`), run from the project root:

```bash
python scripts/verify_mn2_production_ready.py
```

This checks that `MN2_RPC_USER` / `MN2_RPC_PASSWORD` match `config/masternoder2.conf` and runs `getblockcount` against `MN2_RPC_URL` (requires the daemon running for the RPC part). Use `--no-rpc` to only compare files.

---

## Step 1 — Set secret password in project config (local)

1. Open `**config/masternoder2.conf**` in the project root.
2. Set `**rpcpassword=**` to a strong secret (e.g. long random string).
  Example: `rpcpassword=Kp9mN2xL7vQw4jRc8sFb3hYt6nWz1aDg5`
3. Ensure `**rpcuser=mn2rpc**` (or match what you will put in `.env`).
4. Save the file.
  - `config/masternoder2.conf` is gitignored; do not commit real passwords.

---

## Step 2 — Set same password in app env (local)

1. Open `**.env**` in the project root.
2. Set MN2 variables to match `**config/masternoder2.conf**`:
  ```env
   MN2_RPC_URL=http://127.0.0.1:9332
   MN2_RPC_USER=mn2rpc
   MN2_RPC_PASSWORD=<same value as rpcpassword in config/masternoder2.conf>
  ```
3. Save `.env`.
  - Do not commit `.env` with real secrets.

---

## Step 3 — Deploy config folder and .env to server

From your machine (project root):

```bash
# Deploy config files (masternoder2.conf + example) to /var/www/html/config/
python scripts/deploy.py config

# Deploy .env (and systemd units) so the app gets MN2_RPC_*
python scripts/deploy.py mn2_env
```

Or full deploy (includes config and .env):

```bash
python scripts/deploy_all_and_restart_uwsgi.py
```

After this, the server has:

- `**/var/www/html/config/masternoder2.conf**` — daemon config with `rpcuser` / `rpcpassword`
- `**/var/www/html/.env**` — app env with `MN2_RPC_USER` / `MN2_RPC_PASSWORD`

---

## Step 4 — Point MN2 daemon at `/config` on the server

On the **server**, the daemon must use the same config (and thus same password) as the app.

**Option A — Daemon uses project config dir (`-datadir`)**

If your daemon supports `-datadir` (Bitcoin Core style), run it so the data dir is the project’s config folder:

```bash
# Example: run from daemon binary directory
./masternoder2d -datadir=/var/www/html/config
```

Then the daemon reads `**/var/www/html/config/masternoder2.conf**`. No copy to `~/.masternoder2` needed.

**Option B — Copy config into daemon default path**

If you do not use `-datadir`, copy the deployed config into the daemon’s default config location:

```bash
mkdir -p ~/.masternoder2
cp /var/www/html/config/masternoder2.conf ~/.masternoder2/
# Then start daemon as usual (e.g. ./masternoder2d)
```

**Option C — Systemd unit with `-datadir`**

If you run the daemon via systemd, set the data dir in the service file:

```ini
[Service]
ExecStart=/path/to/masternoder2d -datadir=/var/www/html/config
```

Restart the daemon after changing config or ExecStart.

---

## Step 5 — Restart app so it loads the new .env

On the server (or via deploy script):

```bash
sudo systemctl daemon-reload
sudo systemctl restart uwsgi-vidgenerator
```

From your machine:

```bash
python scripts/deploy_all_and_restart_uwsgi.py --no-upload
# or after deploying: deploy.py already restarts uwsgi-vidgenerator for mn2_env
```

Ensure the uwsgi unit loads `.env` (e.g. `EnvironmentFile=-/var/www/html/.env` in `systemd/uwsgi-vidgenerator.service`).

---

## Step 6 — Verify

1. **RPC from server** (replace `YOUR_RPC_PASSWORD` with the real password):
  ```bash
   curl -u mn2rpc:YOUR_RPC_PASSWORD -d '{"jsonrpc":"1.0","id":"1","method":"getblockcount","params":[]}' -H "Content-Type: application/json" http://127.0.0.1:9332
  ```
   You should get JSON with a `result` (block count).
2. **Deposit-address API** (from your machine):
  ```bash
   python scripts/test_deposit_address_api.py user_jon_ulrik
  ```
   Expect: `Deposit address: OK (real address)` when RPC and `.env` are correct.
3. **Profile page**
  Open `https://masternoder.dk/profile` and check that the MN2 Wallet section shows a deposit address (no “Wallet RPC authentication failed”).

---

## Quick checklist (copy-paste)

- **1.** Set `rpcpassword` in `config/masternoder2.conf` (local).
- **2.** Set `MN2_RPC_USER=mn2rpc` and `MN2_RPC_PASSWORD=<same>` in `.env` (local).
- **3.** Deploy: `python scripts/deploy.py config` then `python scripts/deploy.py mn2_env` (or full deploy).
- **4.** On server: run daemon with `-datadir=/var/www/html/config` (or copy `config/masternoder2.conf` to `~/.masternoder2/`).
- **5.** Restart app: `systemctl restart uwsgi-vidgenerator` (and `daemon-reload` if you changed systemd).
- **6.** Test: `curl -u mn2rpc:PASSWORD ... getblockcount` and `python scripts/test_deposit_address_api.py user_jon_ulrik`.

---

See also: [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md), [MN2_OPS.md](MN2_OPS.md).