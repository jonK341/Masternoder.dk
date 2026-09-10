# Exchange master daemon — copy to /etc/cron.d/masternoder-exchange-master
# Every 15 min with flock (tick script skips if previous still running).
# Do NOT run masternoder-exchange-master.service systemd unit at the same time.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/15 * * * * root /var/www/html/cron/exchange_master_tick.sh >> /var/log/masternoder-exchange-master.log 2>&1
