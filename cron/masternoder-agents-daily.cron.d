# MasterNoder.dk — agent cron daily (maintenance + automation + LLM provider snapshot)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
35 3 * * * root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/agents_cron_daily.sh
