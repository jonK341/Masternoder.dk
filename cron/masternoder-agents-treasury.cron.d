# Treasury pool → trader agent funding (scheduled)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
5 */6 * * * root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/agents_treasury_distribute.sh >> /var/log/masternoder-agents-treasury.log 2>&1
