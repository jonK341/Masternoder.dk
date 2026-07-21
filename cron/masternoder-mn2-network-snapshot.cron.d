# MN2 network history snapshot — curl overview every 10 min (server-side throttle).
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
*/10 * * * * root /var/www/html/cron/mn2_network_snapshot.sh >> /var/log/mn2-network-snapshot.log 2>&1
