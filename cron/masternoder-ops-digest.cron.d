# Ops digest — hourly health + gap alerts
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

0 * * * * root /var/www/html/cron/ops_digest_tick.sh >> /var/log/masternoder-ops-digest.log 2>&1
