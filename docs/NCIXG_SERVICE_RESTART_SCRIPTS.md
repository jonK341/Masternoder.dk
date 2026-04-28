# Ncixg Service Restart Scripts

**Date:** 2025-01-20  
**Status:** ✅ COMPLETE  
**Type:** Service Management Scripts

---

## 🎯 Overview

Simple scripts to stop (`./off`) and start (`./on`) the Ncixg service (nginx and related services).

---

## 📁 Files Created

### Linux/Unix Scripts
- **`off`** - Stop nginx and related services
- **`on`** - Start nginx and related services

### Windows Scripts
- **`off.bat`** - Stop nginx and related services (Windows)
- **`on.bat`** - Start nginx and related services (Windows)

### Python Script
- **`restart_ncixg.py`** - Cross-platform Python script for stop/start/restart

---

## 🚀 Usage

### Linux/Unix

**Stop Service:**
```bash
./off
```

**Start Service:**
```bash
./on
```

**Make executable (if needed):**
```bash
chmod +x off on
```

### Windows

**Stop Service:**
```cmd
off.bat
```

**Start Service:**
```cmd
on.bat
```

### Python (Cross-platform)

**Stop Service:**
```bash
python restart_ncixg.py off
```

**Start Service:**
```bash
python restart_ncixg.py on
```

**Restart Service:**
```bash
python restart_ncixg.py restart
```

---

## 🔧 Services Managed

The scripts manage these services:

1. **nginx** - Main web server (Ncixg)
2. **uwsgi-vidgenerator.service** - uWSGI application server
3. **python-proxy.service** - Python proxy service

---

## 📋 Script Details

### `off` / `off.bat`
- Stops nginx
- Stops uwsgi-vidgenerator
- Stops python-proxy
- Verifies services are stopped

### `on` / `on.bat`
- Starts python-proxy (first)
- Starts uwsgi-vidgenerator (second)
- Starts nginx (last)
- Waits for services to initialize
- Verifies all services are running

### `restart_ncixg.py`
- Cross-platform Python script
- Supports: `off`, `on`, `restart` commands
- Handles both systemctl and service commands
- Provides detailed status output

---

## ⚠️ Requirements

### Linux/Unix
- `sudo` access for systemctl commands
- `systemctl` or `service` command available

### Windows
- Administrator privileges
- Services must be installed as Windows services

---

## ✅ Status Verification

After running `./on`, the script verifies:
- ✅ python-proxy: active
- ✅ uwsgi-vidgenerator: active
- ✅ nginx: active

If nginx fails to start, the script will:
- Show error message
- Exit with error code
- Suggest checking logs: `sudo journalctl -u nginx -n 20`

---

## 🔍 Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status nginx

# Check logs
sudo journalctl -u nginx -n 50

# Check configuration
sudo nginx -t
```

### Permission Denied
```bash
# Make scripts executable
chmod +x off on

# Run with sudo if needed
sudo ./off
sudo ./on
```

### Service Not Found
- Verify services are installed
- Check service names match your system
- Update script with correct service names

---

## 📝 Notes

- Scripts use `systemctl` first, fallback to `service` command
- 2-second delays between service starts for initialization
- Scripts are idempotent (safe to run multiple times)
- Windows scripts use `net start/stop` commands

---

**Last Updated:** 2025-01-20  
**Status:** ✅ COMPLETE AND READY TO USE
