# Every 2 minutes — retry paid slots + maintain_ping_loop (via provision-pending API)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/2 * * * * root /var/www/html/cron/mn2_masternode_provision.sh >> /var/www/html/logs/mn2_masternode_provision.log 2>&1
