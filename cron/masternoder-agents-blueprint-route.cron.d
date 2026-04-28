# MasterNoder.dk — blueprint & route fixer audit (weekly, Register Intelligence)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
30 4 * * 1 root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/agents_blueprint_route_fixer.sh
