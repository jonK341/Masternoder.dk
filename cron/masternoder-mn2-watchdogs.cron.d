# Config perms + staking unlock + ping stall watchdog (every 15 min)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/15 * * * * root /var/www/html/cron/mn2_ops_watchdog.sh >> /var/www/html/logs/mn2_watchdog.log 2>&1
