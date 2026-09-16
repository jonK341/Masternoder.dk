# MN2 liquidity pool agent — copy to /etc/cron.d/masternoder-mn2-pool
# Every 3 min: top up MN2 pool inventory and rebalance USDT/USDC
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/3 * * * * root /var/www/html/cron/mn2_pool_agent_tick.sh >> /var/log/masternoder-mn2-pool.log 2>&1
