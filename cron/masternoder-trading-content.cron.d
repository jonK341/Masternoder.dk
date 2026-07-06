# Trading content report + platform news publish
# Copy to /etc/cron.d/masternoder-trading-content
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Every 10 hours
0 */10 * * * root /var/www/html/cron/trading_content_news.sh >> /var/log/masternoder-trading-content.log 2>&1
