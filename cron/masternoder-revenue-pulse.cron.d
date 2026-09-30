# MasterNoder.dk — weekly revenue pulse (Mon 10:00 UTC)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 10 * * 1 root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/revenue_pulse_cron.sh
