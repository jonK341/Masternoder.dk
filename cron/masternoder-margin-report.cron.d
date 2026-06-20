# MasterNoder.dk — weekly Phase C margin report (Tue 10:00 UTC)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 10 * * 2 root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/margin_report_cron.sh
