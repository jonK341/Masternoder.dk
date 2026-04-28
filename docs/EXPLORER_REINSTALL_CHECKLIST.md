# Block explorer reinstall — camgirls.masternoder.dk

**Purpose:** Bring **iquidus-style** explorer (`explorer@1.7.x`) back after a clean host or deleted `~/Iexplorer`, while keeping **masternoder2d** for later. Run these steps **on the Linux server** (as `root` or with `sudo`).

**Prerequisites:** `masternoder2.conf` with **`server=1`**, **`rpcuser` / `rpcpassword`**, **`rpcport=9332`**, **`rpcbind=127.0.0.1`** — same values you will put under **wallet** in `settings.json`. See [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md).

---

## Credential consistency — two separate systems (do not mix them)

| System | User / identity | Password | Must match |
|--------|-----------------|----------|------------|
| **A — MongoDB** (explorer index DB) | DB user, e.g. `iquidus` | Mongo user password you created in `explorerdb` | **Only** the URI in explorer **`settings.json`** (`db` / `mongo` / `database` URI depending on iquidus version). **Not** the MN2 RPC password. |
| **B — MN2 coin daemon (JSON-RPC)** | `rpcuser` (e.g. `mn2rpc`) | `rpcpassword` in `masternoder2.conf` | **`masternoder2.conf`** (daemon) · **Masternoder.dk** `/var/www/html/.env` → `MN2_RPC_USER` / `MN2_RPC_PASSWORD` · explorer **`settings.json`** **wallet** block (host `127.0.0.1`, port `9332`, same user/pass). |

**Common mistake:** pasting the **Mongo** password into the **wallet** section or vice versa. They are **different** products.

### Double-check on the dev PC (repo)

From project root (matches **B** only):

```bash
python scripts/verify_mn2_production_ready.py
# File-only, no daemon required:
python scripts/verify_mn2_production_ready.py --no-rpc
```

### Double-check on the server

**A — Mongo (explorer):** use the **exact** connection string from `settings.json` (redact when pasting in tickets):

```bash
mongosh 'mongodb://USER:PASSWORD@127.0.0.1:27017/explorerdb?authSource=explorerdb'
```

If login fails, fix **Mongo user** or **`authSource`** (`explorerdb` vs `admin`) or the URI in `settings.json`.

**B — MN2 RPC:**

```bash
curl -s -u 'mn2rpc:YOUR_RPC_PASSWORD' \
  -d '{"jsonrpc":"1.0","id":"1","method":"getblockcount","params":[]}' \
  -H 'content-type: application/json' \
  http://127.0.0.1:9332/
```

Compare `YOUR_RPC_PASSWORD` to **`rpcpassword`** in the same **`masternoder2.conf`** the daemon uses and to **`settings.json`** wallet fields.

**Files to align for B:**

1. `/var/www/html/config/masternoder2.conf` (or `~/.masternoder2/masternoder2.conf` if no `-datadir`) — `rpcuser`, `rpcpassword`
2. `/var/www/html/.env` — `MN2_RPC_USER`, `MN2_RPC_PASSWORD`
3. `/var/www/explorer/settings.json` — **wallet** RPC user/password (same as 1)

---

## Phase 0 — Order of operations

1. **MongoDB** up and accepting connections on `127.0.0.1:27017`.
2. **MongoDB user** for the explorer DB (or use `settings.json` without auth only on localhost — less secure).
3. **Explorer** app: `settings.json` + `npm install` + test `npm start`.
4. **masternoder2d** running (RPC reachable) — explorer sync needs it.
5. **Process manager** (PM2 or systemd) so Node survives logout/reboot.
6. **nginx** `proxy_pass` to the **port** in `settings.json` + TLS.

---

## 1. Base packages (Ubuntu/Debian)

```bash
apt update && apt install -y curl git build-essential nginx certbot python3-certbot-nginx
```

**Node.js LTS** (use NodeSource or your distro’s `nodejs` if version ≥ 18):

```bash
# Example: Node 20.x LTS — follow https://github.com/nodesource/distributions if needed
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
node -v && npm -v
```

**MongoDB** (official repo recommended; or `apt install mongodb-org` if you already added the repo):

```bash
systemctl enable --now mongod
systemctl status mongod
ss -tlnp | grep 27017
```

If replica set + `keyFile`: see [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) (keyfile path, `chmod 400`, `chown mongodb`).

---

## 2. MongoDB database and user

Create a **strong password**; store it only in `settings.json` on the server (not in git).

```bash
mongosh
```

```javascript
use explorerdb
db.createUser({
  user: "iquidus",
  pwd: "REPLACE_WITH_STRONG_PASSWORD",
  roles: [ { role: "readWrite", db: "explorerdb" } ]
})
exit
```

If `auth` is enabled and creation fails, run from `mongosh` as admin (e.g. `use admin` then `db.auth(...)` or `createUser` with `userAdminAnyDatabase`).

**Connection string** (used by iquidus):

```text
mongodb://iquidus:REPLACE_WITH_STRONG_PASSWORD@127.0.0.1:27017/explorerdb?authSource=explorerdb
```

If auth fails, try `authSource=admin` (if you created the user in `admin`).

---

## 3. Install explorer application

Pick a **single** directory (e.g. `/var/www/explorer` or `/root/explorer`):

```bash
mkdir -p /var/www/explorer
cd /var/www/explorer
```

**Option A — Git clone** (official iquidus lineage):

```bash
git clone https://github.com/iquidus/explorer.git .
git checkout 1.7.4   # or tag you used before
```

**Option B — Upload** from your repo backup if you do not use public git.

```bash
npm install
cp settings.json.template settings.json
nano settings.json
```

### `settings.json` essentials (names vary slightly by version)

- **Database:** URI matching §2 (user, password, database `explorerdb`).
- **Wallet / coin daemon:** `host` `127.0.0.1`, `port` **9332**, same **`rpcuser` / `rpcpassword`** as `masternoder2.conf`.
- **Web server:** `port` (e.g. **3000**) — this must match **nginx** `proxy_pass` below.
- **Coin-specific:** name, symbol, **txid** regex, **address** prefix — must match **MasterNoder2** coin params (see your coin’s `chainparams` or prior working `settings.json` backup).

---

## 4. Start masternoder2d (RPC for sync)

Before relying on the explorer, confirm RPC:

```bash
curl -s -u 'mn2rpc:YOUR_RPC_PASSWORD' \
  -d '{"jsonrpc":"1.0","id":"1","method":"getblockcount","params":[]}' \
  -H 'content-type: application/json' \
  http://127.0.0.1:9332/
```

If this fails, fix daemon first ([MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md), `systemd/masternoder2d.service.example`).

---

## 5. Test explorer manually

```bash
cd /var/www/explorer
npm start
```

- No **“Unable to connect to database”** → Mongo URI is correct.
- No **RPC auth errors** in log → wallet block matches `masternoder2.conf`.  
Stop with **Ctrl+C** after it listens.

---

## 6. PM2 (recommended)

```bash
npm install -g pm2
cd /var/www/explorer
pm2 start ./bin/cluster --name explorer --node-args="--stack-size=10000"
pm2 save
pm2 startup systemd -u root --hp /root
```

Adjust `--name` and user if you run as `www-data`.

---

## 7. nginx + TLS

**Find the `port` from `settings.json`** (e.g. 3000). Example `server` block:

```nginx
server {
    listen 80;
    server_name camgirls.masternoder.dk;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

```bash
nginx -t && systemctl reload nginx
```

### SSL certificate (Let's Encrypt) for `camgirls.masternoder.dk`

**You must run this on the Linux server** (not on your PC). Certbot proves you control the domain by talking to nginx on port 80.

**Before you start**

1. **DNS:** An **A** (or **AAAA**) record for `camgirls.masternoder.dk` must point to this server’s public IP. Wait until `dig +short camgirls.masternoder.dk` shows the correct IP.
2. **Firewall:** Ports **80** and **443** open to the internet (`ufw allow 'Nginx Full'` or equivalent).
3. **nginx:** A `server { ... server_name camgirls.masternoder.dk; listen 80; ... }` block must exist and load without errors (`nginx -t`).

**Install Certbot (Ubuntu/Debian) if missing**

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

**Issue or renew certificate (nginx plugin — recommended)**

```bash
sudo certbot --nginx -d camgirls.masternoder.dk
```

Follow the prompts (email, agree to terms). Certbot will adjust your nginx vhost to **listen 443 ssl** and set certificate paths under `/etc/letsencrypt/live/camgirls.masternoder.dk/`.

**Dry run (test renewal without changing certs)**

```bash
sudo certbot renew --dry-run
```

**Auto-renewal:** Ubuntu usually installs a **systemd timer** or **cron** for `certbot renew`. Check with:

```bash
systemctl list-timers | grep certbot
```

**If HTTP-01 fails:** Confirm nginx is the server on port 80, no CDN/proxy blocking Let’s Encrypt, and DNS has propagated.

---

## 8. Verification

```bash
curl -sI https://camgirls.masternoder.dk/
curl -sI https://camgirls.masternoder.dk/ext/getmoneysupply
```

Expect **HTTP 200** (not **502**).

---

## 9. If something fails

| Symptom | Check |
|--------|--------|
| **502** | `pm2 list` / `pm2 logs explorer`; `ss -tlnp` shows Node on **settings** port; nginx `proxy_pass` port matches. |
| **Database** | `mongosh` with same URI as `settings.json`; user/password/database `explorerdb`. |
| **RPC** | `getblockcount` curl §4; `rpcpassword` identical in `masternoder2.conf` and `settings.json` wallet. |
| **Sync slow** | Normal until chain is indexed; **masternoder2d** must be synced. |

---

## 10. Backup after it works

- `settings.json` (store securely; **no** git).
- MongoDB dump: `mongodump --db explorerdb` (or full backup policy).
- **Wallet** / `masternoder2.conf` per [MN2_OPS.md §6](MN2_OPS.md).

---

**Related:** [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) · [MN2_OPS.md](MN2_OPS.md) · [MN2_CONFIG_AND_PASSWORD_STEPS.md](MN2_CONFIG_AND_PASSWORD_STEPS.md)
