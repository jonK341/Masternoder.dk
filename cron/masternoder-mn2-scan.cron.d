# MN2 deposit scanner — copy to /etc/cron.d/masternoder-mn2-scan (deploy.py does this for mn2_env)
# Format: cron.d requires user column (root).
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/5 * * * * root /var/www/html/cron/mn2_scan_deposits.sh
