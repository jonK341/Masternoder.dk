# Agent trader market-making tick (P2P internal market)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
*/15 * * * * root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/agents_trader.sh >> /var/log/masternoder-agents-trader.log 2>&1
