# Exchange master daemon — copy to /etc/cron.d/masternoder-exchange-master
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/5 * * * * root /var/www/html/cron/exchange_master_tick.sh >> /var/log/masternoder-exchange-master.log 2>&1
