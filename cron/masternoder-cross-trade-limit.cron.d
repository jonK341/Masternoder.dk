# Limit-order cross-venue arb. Copy to /etc/cron.d/masternoder-cross-trade-limit
# Every minute: price-capped Binance/NonKYC pass. No order unless net edge clears the config.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

* * * * * www-data /var/www/html/cron/cross_trade_limit_tick.sh >> /var/www/html/logs/cross_trade_limit.log 2>&1
