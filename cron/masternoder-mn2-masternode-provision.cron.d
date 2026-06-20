# Every 2 minutes — finish auto-provisioning paid masternode slots
*/2 * * * * root /var/www/html/cron/mn2_masternode_provision.sh >> /var/www/html/logs/mn2_masternode_provision.log 2>&1
