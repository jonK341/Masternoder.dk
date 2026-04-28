# MasterNoder.dk — agent cron weekly (skillsets ensure, health, research rotation)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 5 * * 0 root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/agents_cron_weekly.sh
