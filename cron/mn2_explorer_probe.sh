#!/bin/bash
# Explorer probe + Discord alert — every 15 min (P4 #175).
cd /var/www/html || exit 0
/usr/bin/python3 scripts/mn2_explorer_probe_alert.py >> /var/log/mn2-explorer-probe.log 2>&1 || true
