# MN2 masternode hosting — retry provisioning + ping loop (every 2 minutes).
*/2 * * * * www-data /var/www/html/cron/mn2_masternode_provision.sh >> /var/log/mn2-masternode-provision.log 2>&1

# Root recovery when daemon RPC work queue is saturated (every 5 minutes).
*/5 * * * * root /var/www/html/cron/mn2_masternode_daemon_recover.sh >> /var/log/mn2-masternode-recover.log 2>&1
