# MasterNoder.dk — casino agent play loop (leaderboard bots, coins rail)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
*/15 * * * * root AGENTS_CRON_ENV_FILE=/var/www/html/.env MN2_CRON_HOST=http://127.0.0.1:5000 /var/www/html/cron/casino_agents.sh
