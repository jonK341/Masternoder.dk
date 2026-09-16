# MN2 pool full tick — every 15 min (includes agent sweep)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/15 * * * * root /var/www/html/cron/mn2_pool_agent_tick.sh >> /var/log/masternoder-mn2-pool-full.log 2>&1
