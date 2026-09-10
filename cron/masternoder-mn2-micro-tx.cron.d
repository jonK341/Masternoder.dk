# MN2 micro-tx batch sweep — copy to /etc/cron.d/masternoder-mn2-micro-tx
# Runs nightly at 03:15 UTC (marks balances above threshold; in-app credits stay instant).
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

15 3 * * * root /var/www/html/cron/mn2_micro_tx_batch.sh
