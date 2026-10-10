# Ubuntu OS upgrade — masternoder.dk production

Use this when upgrading the **server OS** (e.g. `do-release-upgrade`). This is separate from the **MN2 daemon** upgrade (`mn2_daemon_upgrade_remote.py`).

**Critical paths**

| Path | Why |
|------|-----|
| `/var/www/html/config/` | **Wallet + chain data** — back up before any major OS change |
| `/var/www/html/.env` | RPC passwords, PayPal, Discord, ops secrets |
| `/var/www/html/data/` | App JSON state (performers, unlocks, tips, fleet) |
| `/etc/nginx/sites-enabled/` | Site proxy config |
| `/etc/systemd/system/uwsgi-vidgenerator*.service` | App workers |

**Do not use** legacy `uwsgi.service` (Debian emperor). Use **`uwsgi-vidgenerator`** + **`uwsgi-vidgenerator-5001`** only.

---

## Before upgrade (prep)

### From your PC (recommended)

```powershell
# Upload prep scripts if not on server yet
python scripts/deploy.py --files scripts/ubuntu_upgrade_prep.sh scripts/ubuntu_upgrade_post_verify.sh scripts/ubuntu_upgrade_prep_remote.py --ask-pass

# Run backup + stop uwsgi workers on server
python scripts/ubuntu_upgrade_prep_remote.py --ask-pass
```

### On the server (SSH)

```bash
cd /var/www/html
sudo bash scripts/ubuntu_upgrade_prep.sh
```

This will:

1. Check disk space (warn if &lt; 5 GB free)
2. Stop **uwsgi-vidgenerator** and **uwsgi-vidgenerator-5001** (site will 502 until restart or reboot)
3. Create `/root/mn2-pre-ubuntu-upgrade/mn2-critical-*.tar.gz` (`.env`, `config/`, `data/`, cron, systemd templates, uwsgi ini)
4. Snapshot nginx sites and systemd unit definitions

**Optional:** copy the tarball off-server:

```bash
scp root@masternoder.dk:/root/mn2-pre-ubuntu-upgrade/mn2-critical-*.tar.gz .
```

### Free disk if needed

```powershell
python scripts/server_cleanup_scan.py --clean --yes
```

### Upgrade command

```bash
sudo apt update
sudo apt install -y update-manager-core
sudo do-release-upgrade
# or LTS stepping: follow Ubuntu docs for your current → target version
```

Reboot when prompted.

---

## After reboot (verify)

### On the server

```bash
cd /var/www/html
sudo bash scripts/ubuntu_upgrade_post_verify.sh
```

### From your PC

```powershell
python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking
python scripts/camgirls_post_deploy_verify.py --base-url https://masternoder.dk
python scripts/shop_v4_production_smoke.py --full-line
```

**Expected after daemon/uwsgi restart:** wallet locked until `--restore-staking` — health may show **degraded** until then.

---

## If something breaks

| Symptom | Action |
|---------|--------|
| 502 / site down | `systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001` · `python scripts/ensure_site_up.py` |
| uWSGI exit 1 | `cd /var/www/html && sudo bash scripts/uwsgi_diagnose_server.sh` |
| Missing Python deps | `python scripts/install_requirements_on_server.py --production -y --ask-pass` |
| MN2 RPC dead | `systemctl status masternoder2d` · `journalctl -u masternoder2d -n 50` |
| Cron missing | `python scripts/mn2_next_ops_remote.py --ask-pass --optionals` |
| Restore wallet | `python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking` |

See also [SERVER_QUICK_REFERENCE.md](SERVER_QUICK_REFERENCE.md) · [UWSGI_EXIT1_TROUBLESHOOTING.md](UWSGI_EXIT1_TROUBLESHOOTING.md).

---

## Services checklist (systemd)

| Unit | Port / role |
|------|-------------|
| `nginx` | HTTPS front |
| `masternoder2d` | MN2 RPC **9332**, datadir `/var/www/html/config` |
| `uwsgi-vidgenerator` | Flask **5000** |
| `uwsgi-vidgenerator-5001` | Flask **5001** (nginx upstream) |

```bash
sudo systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
sudo systemctl restart masternoder2d
sudo systemctl reload nginx
```
