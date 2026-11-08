# Limit-order cross-venue arb. Copy to /etc/cron.d/masternoder-cross-trade-limit
# Every minute: price-capped Binance/NonKYC pass. No order unless net edge clears the config.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

* * * * * root /var/www/html/cron/cross_trade_limit_tick.sh >> /var/log/masternoder-cross-trade-limit.log 2>&1
