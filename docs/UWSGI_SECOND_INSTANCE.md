# Second uWSGI instance (port 5001)

**Policy (what to keep / retire / 5002):** see **`docs/BACKEND_PORTS_DECISION.md`**.

## Why it failed before

`uwsgi.ini` always binds **127.0.0.1:5000**. The 5001 unit passed `--http-socket 127.0.0.1:5001` on top of that, so uWSGI still tried to bind **5000** (already used by `uwsgi-vidgenerator`) and exited with status **1**.

Fix: use **`uwsgi_5001.ini`**, which includes shared `uwsgi_common.ini` and binds **only** 5001.

### Still `status=1/FAILURE` with correct `ExecStart`?

Both instances share **`chdir = /var/www/html`**. uWSGI’s default **`uwsgi.pid`** in that directory is used by the **first** master only; the second instance exits immediately unless it has its **own** `pidfile`. Repo fix:

- **`uwsgi.ini`** → `pidfile = /var/www/html/uwsgi.pid`
- **`uwsgi_5001.ini`** → `pidfile = /var/www/html/uwsgi_5001.pid`

Upload the updated `.ini` files, then `sudo systemctl restart uwsgi-vidgenerator` and `sudo systemctl restart uwsgi-vidgenerator-5001` (or `start`).

## Deploy on server

```bash
# Copy new files to /var/www/html/
# uwsgi_common.ini, uwsgi.ini, uwsgi_5001.ini, systemd/uwsgi-vidgenerator-5001.service

sudo touch /var/www/html/.uwsgi_touch_reload_5001
sudo chown www-data:www-data /var/www/html/.uwsgi_touch_reload_5001

sudo systemctl daemon-reload
sudo systemctl restart uwsgi-vidgenerator
```

## Start 5001 **without** enabling on boot

```bash
sudo systemctl disable uwsgi-vidgenerator-5001
sudo systemctl start uwsgi-vidgenerator-5001
sudo systemctl status uwsgi-vidgenerator-5001
```

`disable` only removes the unit from multi-user startup; you can still `start` / `stop` manually.

## Start from your PC (one command)

From the project root — SSHs to the server and manages the **`uwsgi-vidgenerator-5001`** systemd unit:

- `systemctl show` (ExecStart, etc.)
- `systemctl reset-failed uwsgi-vidgenerator-5001` (clears stuck **activating (auto-restart)** / failed state)
- `systemctl start uwsgi-vidgenerator-5001` + status (works even if the unit is **disabled** for boot)
- On failure: prints **journalctl** for that unit and **tail** of `/var/www/html/uwsgi_5001.log`

```bash
python scripts/start_uwsgi_5001.py
```

**Windows:** double-click `scripts\start_uwsgi_5001.bat` — sets `SYSTEMD_UNIT=uwsgi-vidgenerator-5001` and uses `.venv\Scripts\python.exe` when present (no venv `activate` needed).

- **Requires:** `pip install paramiko` (if missing).
- **Override:** `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PASS`, `SYSTEMD_UNIT` (default `uwsgi-vidgenerator-5001`).
- **Script:** `scripts/start_uwsgi_5001.py`

## Optional: nginx upstream

Point a second upstream server at `127.0.0.1:5001` for load spreading once 5001 is healthy.
