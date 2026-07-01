# Exchange master daemon — copy to /etc/cron.d/masternoder-exchange-master
# Every 2 min: live profit scan + auto PayPal sweep when pool >= min
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/2 * * * * root /var/www/html/cron/exchange_master_tick.sh >> /var/log/masternoder-exchange-master.log 2>&1
