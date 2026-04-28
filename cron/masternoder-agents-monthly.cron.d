# MasterNoder.dk — agent cron monthly (skillset rebalance)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
15 4 1 * * root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/agents_cron_monthly.sh
