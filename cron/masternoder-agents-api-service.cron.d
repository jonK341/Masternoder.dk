# MasterNoder.dk — API service / API gap scan (weekly)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
45 4 * * 4 root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/agents_api_service_skill.sh
