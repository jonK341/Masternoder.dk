# MasterNoder.dk — trader agent market-maker tick (every 15 min)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
*/15 * * * * root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/agents_trader.sh
