# P2P market agent demo (listings + simulated trades)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
*/2 * * * * root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/agents_p2p_market.sh
