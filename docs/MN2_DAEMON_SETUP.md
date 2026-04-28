# MasterNoder2 daemon — download and start (cmd guide)

Quick command-line guide to download and run the MN2 daemon so the Masternoder.dk backend can use RPC (e.g. `/api/health/system` → `mn2_rpc`, deposits/withdrawals later).

**Where the daemon runs:** The daemon must run on the **server** where the Masternoder.dk backend is deployed (same machine or same private network). The backend connects to `MN2_RPC_URL` (e.g. `http://127.0.0.1:9332` on the server). You do **not** run the daemon on your local dev machine unless you are testing MN2 integration locally — in production, install and run the daemon on the deployment server and set `MN2_RPC_*` in the server’s `.env`.

**Releases:** [MasterNoder2 releases](https://github.com/jonK341/MasterNoder2/releases) (latest: **v1.2.2.0**).  
**Default RPC port:** `9332` (mainnet). For **testnet**, use port `19332` and set `MN2_NETWORK=testnet` in `.env` (or set `MN2_RPC_URL=http://127.0.0.1:19332`). The app uses `MN2_RPC_URL` if set; otherwise it picks the default by `MN2_NETWORK`.

**Server setup:** The steps below (download, extract, config, start) are intended for the **server** (e.g. Linux). On that server, set `MN2_RPC_URL`, `MN2_RPC_USER`, and `MN2_RPC_PASSWORD` in the app’s `.env` to match the daemon’s `masternoder2.conf`. Local dev can leave MN2 vars empty or point to a test daemon; the health check will show `mn2_rpc` as unreachable until a daemon is available.

**Fix deposit-address 401:** The app must see the same RPC credentials as the wallet. The deploy script uploads `.env` to `/var/www/html/.env` and the systemd unit loads it via `EnvironmentFile=-/var/www/html/.env`. So ensure your local `.env` has `MN2_RPC_USER=mn2rpc` and `MN2_RPC_PASSWORD=` (same as in `config/masternoder2.conf`), then run `python scripts/deploy_all_and_restart_uwsgi.py` so the server gets `.env` and the updated unit; after restart, deposit-address should work.

**Step-by-step todo (secret password + daemon path `/config`):** See [MN2_CONFIG_AND_PASSWORD_STEPS.md](MN2_CONFIG_AND_PASSWORD_STEPS.md) for a checklist: set password in `config/masternoder2.conf` and `.env`, deploy config + mn2_env, run daemon with `-datadir=/var/www/html/config`, restart app, verify.

---

## 1. Download

### Windows (PowerShell)

```powershell
# Create a folder for the daemon
mkdir $env:USERPROFILE\mn2-daemon
cd $env:USERPROFILE\mn2-daemon

# Download Linux daemon (tar.gz) — for WSL or use Windows build if available
$url = "https://github.com/jonK341/MasterNoder2/releases/download/v1.2.2.0/masternoder2d.tar.gz"
Invoke-WebRequest -Uri $url -OutFile "masternoder2d.tar.gz" -UseBasicParsing
```

If the release provides a **Windows** asset (e.g. `.zip` or installer), download that instead and extract to the same folder.

### Linux / WSL

```bash
# Create folder
mkdir -p ~/mn2-daemon
cd ~/mn2-daemon

# Download (pick one)
wget https://github.com/jonK341/MasterNoder2/releases/download/v1.2.2.0/masternoder2d.tar.gz
# or
curl -L -o masternoder2d.tar.gz https://github.com/jonK341/MasterNoder2/releases/download/v1.2.2.0/masternoder2d.tar.gz
```

---

## 2. Extract

### Windows (PowerShell 5+ or Windows 10+ tar)

```powershell
# If you have tar (Windows 10 build 17063+)
tar -xzf masternoder2d.tar.gz
```

If you don’t have `tar`, use 7-Zip or another tool to extract the `.tar.gz` into the same folder.

### Linux / WSL

The tarball extracts to a **directory** named `masternoder2d`; the **binary** is inside it.

```bash
tar -xzf masternoder2d.tar.gz
ls -la   # -> masternoder2d/ (directory)
ls masternoder2d/   # -> masternoder2d (the executable)
# Run from inside the directory: cd masternoder2d && ./masternoder2d
```

---

## 3. RPC config (so the site backend can connect)

The project includes a **template**: **`config/masternoder2.conf.example`**. Copy it to **`config/masternoder2.conf`** (this file is gitignored and can hold your real password), or create `masternoder2.conf` from the example and set a strong `rpcpassword`.

1. **Set a strong RPC password**  
   In `config/masternoder2.conf`, set `rpcpassword=` to a strong value (or keep the one already set there).

2. **Install the config for the daemon**  
   The daemon reads `~/.masternoder2/masternoder2.conf` (Linux). Create it on the server in one of these ways:

   - **If the Masternoder.dk repo is on the server** (e.g. `/var/www/masternoder.dk` or your deploy path), copy from the repo:
     ```bash
     mkdir -p ~/.masternoder2
     cp /path/to/your/Masternoder.dk/config/masternoder2.conf ~/.masternoder2/
     ```
     Replace `/path/to/your/Masternoder.dk` with the actual path (e.g. `~/Masternoder.dk` or the app deploy directory).

   - **If the repo is not on the server**, create the config file directly (replace `REPLACE_WITH_STRONG_PASSWORD` with a strong password and use the same in the app’s `.env` as `MN2_RPC_PASSWORD`):
     ```bash
     mkdir -p ~/.masternoder2
     cat > ~/.masternoder2/masternoder2.conf << 'EOF'
     server=1
     rpcuser=mn2rpc
     rpcpassword=REPLACE_WITH_STRONG_PASSWORD
     rpcport=9332
     rpcallowip=127.0.0.1
     rpcbind=127.0.0.1
     EOF
     ```
   - **Windows:** typically `%APPDATA%\MasterNoder2\masternoder2.conf`, or run the daemon with `-datadir` pointing to a folder that contains this config.

3. **Configure `.env`**  
   Set the same credentials in the Masternoder.dk `.env` (same values as in the conf file):

   ```env
   MN2_RPC_URL=http://127.0.0.1:9332
   MN2_RPC_USER=mn2rpc
   MN2_RPC_PASSWORD=REPLACE_WITH_STRONG_PASSWORD
   ```

   Replace `REPLACE_WITH_STRONG_PASSWORD` with the same password you put in `config/masternoder2.conf`.

---

## 4. Start the daemon

### Production server (masternoder.dk app at `/var/www/html`)

Use the same config directory as the app so RPC credentials match `.env`:

```bash
# Replace /opt/... with wherever you installed the Linux binary (see §1–2 above).
/opt/masternoder2d/masternoder2d -datadir=/var/www/html/config
```

Or use the repo helper (resolves `MN2_BINARY` if you export it):

```bash
cd /var/www/html
chmod +x scripts/run_masternoder2d.sh
export MN2_BINARY=/opt/masternoder2d/masternoder2d   # if not in PATH
./scripts/run_masternoder2d.sh
```

**Windows (PowerShell):** `chmod`, `export`, and `./script.sh` are **bash** commands. Either:

- Run **`powershell -File scripts/run_masternoder2d.ps1`** from the repo (uses Git Bash if installed), or  
- Open **Git Bash** / **WSL** and run the `bash` commands above, or  
- **SSH** to the Linux server and run the script there (recommended for production).

**systemd (recommended):** copy `systemd/masternoder2d.service.example` to `/etc/systemd/system/masternoder2d.service`, fix `ExecStart` to your binary path, then `sudo systemctl daemon-reload && sudo systemctl enable --now masternoder2d`.

---

### Production server — default datadir `~/.masternoder2` (no `-datadir`)

The headless daemon looks for **`~/.masternoder2/masternoder2.conf`**. Without a valid file it often exits immediately or never binds **9332**. You need at least:

| Setting | Why |
|--------|-----|
| `server=1` | Enables RPC server (otherwise no listener on 9332). |
| `rpcuser` / `rpcpassword` | Must match app `.env` (`MN2_RPC_USER` / `MN2_RPC_PASSWORD`). |
| `rpcport=9332` | Same as `MN2_RPC_URL` (mainnet). |
| `rpcallowip` / `rpcbind` | Usually `127.0.0.1` so only local uwsgi can call RPC. |

**1. Create config on the server (SSH as the user that will run the daemon, often `root` or a dedicated user):**

```bash
mkdir -p ~/.masternoder2
# From your deployed repo (adjust path if needed):
cp /var/www/html/config/masternoder2.conf ~/.masternoder2/masternoder2.conf
# Or copy from example and edit password:
# cp /var/www/html/config/masternoder2.conf.example ~/.masternoder2/masternoder2.conf
chmod 600 ~/.masternoder2/masternoder2.conf
nano ~/.masternoder2/masternoder2.conf   # set rpcpassword; keep server=1
```

**2. Match the app:** in `/var/www/html/.env` set `MN2_RPC_USER` and `MN2_RPC_PASSWORD` to the **same** `rpcuser` / `rpcpassword` as in that file. Restart uwsgi after changing `.env`.

**3. Start the daemon** (path to binary from your install, e.g. extracted tarball):

```bash
cd /opt/masternoder2d/masternoder2d   # or wherever masternoder2d lives
chmod +x masternoder2d
./masternoder2d
```

Background:

```bash
nohup /opt/masternoder2d/masternoder2d/masternoder2d >> /var/log/masternoder2d.log 2>&1 &
```

**systemd** (default datadir — **omit** `-datadir` in `ExecStart`):

```ini
ExecStart=/opt/masternoder2d/masternoder2d/masternoder2d
User=root
```

Then: `sudo systemctl daemon-reload && sudo systemctl enable --now masternoder2d`

**4. Verify RPC:**

```bash
curl -s -u 'mn2rpc:YOUR_RPC_PASSWORD' \
  -d '{"jsonrpc":"1.0","id":"1","method":"getblockcount","params":[]}' \
  -H 'Content-Type: application/json' \
  http://127.0.0.1:9332/
```

You should see JSON with a numeric `"result"` (block height). If the process exits right away, check `~/.masternoder2/debug.log` or run `./masternoder2d` in the foreground to see errors.

---

### Generic: run from the folder that contains the `masternoder2d` binary

### Windows

The v1.2.2.0 release does **not** include a headless `masternoder2d.exe` on Windows — only **MasterNoder2-qt-win.zip** (GUI wallet). The GUI wallet may not expose RPC on port 9332 the same way as the Linux daemon.

- **Option A — Use WSL:** Install [WSL](https://aka.ms/wslinstall), then in WSL download and run the **Linux** `masternoder2d.tar.gz` daemon (steps in “Linux / WSL” below). The backend on Windows can then connect to `127.0.0.1:9332` if the daemon is running in WSL.
- **Option B — Qt wallet:** The project can download the Windows Qt wallet to `tools/mn2-daemon/` (this folder is gitignored). Run `tools\mn2-daemon\MasterNoder2-win\masternoder2-qt.exe` for the GUI; ensure `%APPDATA%\MasterNoder2\masternoder2.conf` exists with `server=1` and your RPC settings (copy from `config/masternoder2.conf`). RPC may only be available when the wallet is fully synced; if port 9332 is still not open, use the Linux daemon in WSL.

### Linux / WSL

The binary is inside the extracted directory: `~/mn2-daemon/masternoder2d/masternoder2d`.

```bash
cd ~/mn2-daemon/masternoder2d
chmod +x masternoder2d
./masternoder2d
```

To run in the background:

```bash
cd ~/mn2-daemon/masternoder2d
nohup ./masternoder2d > ~/mn2-daemon/nohup.out 2>&1 &
```

If the process exits immediately (`[n]+ Done`), check `cat ~/mn2-daemon/nohup.out`. Often the daemon needs `~/.masternoder2/masternoder2.conf` with `server=1` and valid `rpcuser`/`rpcpassword` before it will keep running and bind to port 9332. For a persistent service, consider a systemd unit or screen/tmux.

---

## 5. Check that it’s running

- **From the machine where the daemon runs:**

  ```bash
  curl -u mn2rpc:YOUR_RPC_PASSWORD -d '{"jsonrpc":"1.0","id":"mn2","method":"getblockcount","params":[]}' -H "Content-Type: application/json" http://127.0.0.1:9332
  ```

  You should get a JSON response with a `result` (block height).

- **From the Masternoder.dk app:**  
  Call `/api/health/system` and confirm `mn2_rpc.status` is `"healthy"` and `mn2_rpc.block_height` is a number.

---

## 5b. Troubleshooting: “Cannot obtain a lock” / daemon not responding

**Symptom:** `nohup` reports `[n]- Exit 1` and `nohup.out` says:
```text
Error: Cannot obtain a lock on data directory /root/.masternoder2. MasterNoder2 Core is probably already running.
```
Nothing listens on port 9332 and `curl` to 127.0.0.1:9332 gets “Connection refused”.

**Cause:** A lock file in `~/.masternoder2` (or another MasterNoder2 process) is holding the data directory. New daemon processes then exit immediately and never bind RPC. You may also see **“Unable to bind to 0.0.0.0:17646”** — that is the P2P port; another MasterNoder2 process (e.g. the Qt wallet) is already using it. Stop **all** MasterNoder2 processes (daemon and Qt), then remove the lock and start a single daemon.

**Fix on the server:**

1. **Find and stop every MasterNoder2 process** (daemon and Qt wallet both use the same data dir and ports; the Qt wallet or an old process can hold the lock and port 17646):
   ```bash
   ps aux | grep -i masternoder    # see what is running
   ss -tlnp | grep -E '9332|17646' # RPC 9332, P2P 17646
   pkill -9 -f masternoder2        # kill daemon and Qt wallet
   rm -f ~/.masternoder2/.lock
   sleep 3
   ps aux | grep -i masternoder    # must show nothing (only grep itself)
   ```
   If you have a script like `masternoder2-auto.sh` that starts the Qt wallet or daemon (e.g. from cron or systemd), disable or stop it so only one instance runs.

2. **Start the daemon again** (use the same password you set in `~/.masternoder2/masternoder2.conf`):
   ```bash
   cd ~/mn2-daemon/masternoder2d
   nohup ./masternoder2d >> ~/mn2-daemon/nohup.out 2>&1 &
   sleep 10
   cat ~/mn2-daemon/nohup.out
   ss -tlnp | grep 9332
   ```

3. **Test RPC** (replace `your_actual_password_here` with the real `rpcpassword` from `~/.masternoder2/masternoder2.conf`):
   ```bash
   curl -u mn2rpc:your_actual_password_here -d '{"jsonrpc":"1.0","id":"mn2","method":"getblockcount","params":[]}' -H "Content-Type: application/json" http://127.0.0.1:9332
   ```
   You should get JSON with a `result` (block height). If you still get “Connection refused”, the daemon may be syncing; check `nohup.out` for errors.

---

## 6. Run only the daemon (no Qt) on the server

To use the headless daemon for RPC and **not** the Qt wallet on the same machine:

1. **Stop all MasterNoder2 processes** (Qt wallet and any existing daemon) so they release the data directory and ports (9332, 17646).
2. **Disable auto-start of the Qt wallet** if you have a script or service that starts it (e.g. `~/masternoder2-auto.sh`, cron, systemd). Otherwise it may start again and block the daemon.
3. **Remove the lock** and start **only** the daemon.

Run the following on the server as root (replace `your_actual_password_here` with the `rpcpassword` from `~/.masternoder2/masternoder2.conf`):

```bash
# --- Stop everything and disable Qt auto-start ---
pkill -9 -f masternoder2 || true
sleep 2

# Disable auto-start script if present (so Qt doesn't start again)
[ -f ~/masternoder2-auto.sh ] && chmod -x ~/masternoder2-auto.sh
crontab -l 2>/dev/null | grep -v masternoder2 | crontab - 2>/dev/null || true
systemctl --user list-units 2>/dev/null | grep -qi masternoder2 && systemctl --user stop masternoder2* 2>/dev/null || true

# Remove lock and start only the daemon
rm -f ~/.masternoder2/.lock
sleep 2
cd ~/mn2-daemon/masternoder2d
nohup ./masternoder2d >> ~/mn2-daemon/nohup.out 2>&1 &

# Wait and verify
sleep 15
cat ~/mn2-daemon/nohup.out
ss -tlnp | grep -E '9332|17646'
curl -u mn2rpc:your_actual_password_here -d '{"jsonrpc":"1.0","id":"mn2","method":"getblockcount","params":[]}' -H "Content-Type: application/json" http://127.0.0.1:9332
```

- If `ss` shows **9332** (and optionally 17646), the daemon is running.
- If `curl` returns JSON with a `result` (block height), RPC is working. Set in the app's `.env`: `MN2_RPC_URL=http://127.0.0.1:9332`, `MN2_RPC_USER=mn2rpc`, `MN2_RPC_PASSWORD=your_actual_password_here`.

---

## Summary

| Step        | Windows                    | Linux / WSL                          |
|------------|----------------------------|--------------------------------------|
| Download   | `Invoke-WebRequest` (see above) | `wget` or `curl` (see above)        |
| Extract    | `tar -xzf` or 7-Zip        | `tar -xzf masternoder2d.tar.gz` → binary at `masternoder2d/masternoder2d` |
| Config     | Use **`config/masternoder2.conf`** (set `rpcpassword`), then copy to daemon data dir or create on server with `cat > ~/.masternoder2/masternoder2.conf` (see §3 and §6) |
| Start      | `.\masternoder2d.exe`      | `cd ~/mn2-daemon/masternoder2d && ./masternoder2d` or `nohup ./masternoder2d &` |
| Match .env | Set `MN2_RPC_USER=mn2rpc`, `MN2_RPC_PASSWORD=` (same as in `.conf`) |

---

## 7. Full server sequence (copy-paste)

Run this on the server (e.g. after SSH). Replace `YOUR_STRONG_PASSWORD` with a strong RPC password and set the same in the app’s `.env` as `MN2_RPC_PASSWORD`.

```bash
# 1) Daemon directory and download
mkdir -p ~/mn2-daemon && cd ~/mn2-daemon
wget -q https://github.com/jonK341/MasterNoder2/releases/download/v1.2.2.0/masternoder2d.tar.gz
tar -xzf masternoder2d.tar.gz

# 2) Config (daemon reads ~/.masternoder2/masternoder2.conf)
mkdir -p ~/.masternoder2
cat > ~/.masternoder2/masternoder2.conf << 'EOF'
server=1
rpcuser=mn2rpc
rpcpassword=YOUR_STRONG_PASSWORD
rpcport=9332
rpcallowip=127.0.0.1
rpcbind=127.0.0.1
EOF
# Edit the password: sed -i 's/YOUR_STRONG_PASSWORD/your_actual_password/' ~/.masternoder2/masternoder2.conf

# 3) Start daemon (binary is inside masternoder2d/masternoder2d)
cd ~/mn2-daemon/masternoder2d
chmod +x masternoder2d
nohup ./masternoder2d > ~/mn2-daemon/nohup.out 2>&1 &

# 4) Check it’s running and listening
sleep 5
cat ~/mn2-daemon/nohup.out
ss -tlnp | grep 9332 || netstat -tlnp | grep 9332
```

Then set in the app’s `.env` on the server: `MN2_RPC_URL=http://127.0.0.1:9332`, `MN2_RPC_USER=mn2rpc`, `MN2_RPC_PASSWORD=your_actual_password`.

---

If the daemon’s config path or options differ for your build, check the [MasterNoder2 repo](https://github.com/jonK341/MasterNoder2) or release notes. For integration details see [MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md). For runbooks, scanner cron, and reconciliation see [MN2_OPS.md](MN2_OPS.md).
