# Fix uwsgi.service "…fail!" on the server

The `uwsgi` service is an **LSB init script** that starts uWSGI using configs from `/etc/uwsgi/apps-enabled/`. If that directory is empty or the config is wrong, you only see `...fail!` in journalctl.

---

## Quick fix (run on server as root)

SSH into the server and run:

```bash
# 1. Ensure apps-enabled has the vidgenerator config
sudo mkdir -p /etc/uwsgi/apps-enabled
sudo ln -sf /var/www/html/vidgenerator/uwsgi.ini /etc/uwsgi/apps-enabled/vidgenerator.ini
ls -la /etc/uwsgi/apps-enabled/

# 2. Allow www-data to use the venv
sudo chmod 755 /var/www/html/vidgenerator/.venv
sudo chmod 755 /var/www/html/vidgenerator/.venv/bin
sudo chmod 755 /var/www/html/vidgenerator/.venv/bin/*

# 3. Start uwsgi
sudo systemctl start uwsgi
sudo systemctl status uwsgi
```

If it still fails, run uwsgi by hand to see the real error:

```bash
sudo -u www-data /usr/bin/uwsgi --ini /var/www/html/vidgenerator/uwsgi.ini
```

(Ctrl+C to stop. Fix any Python/import/permission errors shown, then `sudo systemctl start uwsgi` again.)

---

## 1. Run these on the server (SSH as root)

### See what the service runs
```bash
cat /etc/init.d/uwsgi | head -80
```
or
```bash
systemctl cat uwsgi
```

### Allow www-data to use the venv (fix "permission denied" on .venv/bin)
```bash
# 755 = rwxr-xr-x so www-data can traverse and execute
sudo chmod 755 /var/www/html/vidgenerator/.venv
sudo chmod 755 /var/www/html/vidgenerator/.venv/bin
sudo chmod 755 /var/www/html/vidgenerator/.venv/bin/*
```

### Ensure the app config is used by the init script
```bash
# Create dir if missing
sudo mkdir -p /etc/uwsgi/apps-enabled

# Point the service at the vidgenerator config
sudo ln -sf /var/www/html/vidgenerator/uwsgi.ini /etc/uwsgi/apps-enabled/vidgenerator.ini

# Verify
ls -la /etc/uwsgi/apps-enabled/
```

### See the real error (run uwsgi by hand)
Use **system uwsgi** (venv often has no uwsgi binary). This prints the actual Python/uwsgi error:

```bash
cd /var/www/html/vidgenerator
sudo -u www-data /usr/bin/uwsgi --ini /var/www/html/vidgenerator/uwsgi.ini
```
(Ctrl+C to stop. The ini has `virtualenv = /var/www/html/vidgenerator/.venv` so the app still uses the venv.)

If you prefer uwsgi from the venv, install it then use it:
```bash
/var/www/html/vidgenerator/.venv/bin/pip install uwsgi
sudo -u www-data /var/www/html/vidgenerator/.venv/bin/uwsgi --ini /var/www/html/vidgenerator/uwsgi.ini
```

### Start the service again
```bash
sudo systemctl start uwsgi
sudo systemctl status uwsgi
```

---

## 2. If the service still fails

Run uwsgi manually in the foreground (command above). Typical causes:

- **Module/import error** – fix `pythonpath` or dependencies in the venv.
- **Permission** – `chdir`/log file must be writable by `www-data`.
- **Port in use** – `ss -tlnp | grep 5000`; stop the process using 5000 or change the port in `uwsgi.ini`.

After fixing, run:
```bash
sudo systemctl start uwsgi
```

---

## 3. When `systemctl start uwsgi` keeps failing

After `stop` + `restart` the service may still fail with "control process exited with error code". Do this **on the server as root**:

### A. Free port 5000 and fix permissions

```bash
# Stop everything that might use 5000
sudo systemctl stop uwsgi
sudo pkill -f uwsgi
sleep 2
sudo fuser -k 5000/tcp 2>/dev/null || true
sleep 1

# So www-data can chdir and write uwsgi.log
sudo chmod 755 /var/www /var/www/html /var/www/html/vidgenerator
sudo touch /var/www/html/vidgenerator/uwsgi.log
sudo chown www-data:www-data /var/www/html/vidgenerator/uwsgi.log
```

### B. See the real error (run uwsgi by hand)

```bash
cd /var/www/html/vidgenerator
sudo -u www-data /usr/bin/uwsgi --ini /var/www/html/vidgenerator/uwsgi.ini
```

- If you see **chdir(): Permission denied** – fix parent dirs (e.g. `chmod 755 /var/www /var/www/html`) and ensure `www-data` can traverse into `vidgenerator`.
- If you see **Address already in use** – something still has port 5000; run `ss -tlnp | grep 5000` and kill that process.
- If uwsgi **starts and keeps running** (no immediate exit) – the app is OK; stop it with Ctrl+C, then run `sudo systemctl start uwsgi` again.
- If it **exits right after** "getting INI configuration" – the failure is after config load (e.g. chdir, uid drop, or Python import). Check `journalctl -xeu uwsgi.service` for the same message.

### C. Optional: run the fix script on the server

From your machine, copy the script to the server and run it there:

```bash
# On your machine (from project root), copy script to server
scp scripts/server_fix_uwsgi.sh root@masternoder.dk:/tmp/

# On the server
ssh root@masternoder.dk "bash /tmp/server_fix_uwsgi.sh"
```

Or paste the contents of `scripts/server_fix_uwsgi.sh` into a file on the server and run `bash /path/to/that/file`.

---

## 4. From your Windows machine (optional)

Run the project script that does the symlink and restart:

```bash
python fix_502.py
```

Or run the diagnostic script to inspect and fix over SSH:

```bash
python scripts/diagnose_uwsgi_server.py
python scripts/diagnose_uwsgi_server.py --fix
```
