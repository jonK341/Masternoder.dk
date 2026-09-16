# MN2 liquidity pool agent — copy to /etc/cron.d/masternoder-mn2-pool
# Deprecated: use masternoder-mn2-pool-light.cron.d (3 min) + masternoder-mn2-pool-full.cron.d (15 min)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/3 * * * * root /var/www/html/cron/mn2_pool_agent_light_tick.sh >> /var/log/masternoder-mn2-pool.log 2>&1
