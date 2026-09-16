# MN2 pool light tick — every 3 min (no heavy agent sweep)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/3 * * * * root /var/www/html/cron/mn2_pool_agent_light_tick.sh >> /var/log/masternoder-mn2-pool-light.log 2>&1
