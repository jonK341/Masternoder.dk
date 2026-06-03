# MN2 staking reward accrual — copy to /etc/cron.d/masternoder-mn2-accrue (deploy.py does this for mn2_env)
# Format: cron.d requires user column (root). Runs hourly to match accrual_interval_minutes (60).
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

0 * * * * root /var/www/html/cron/mn2_accrue_rewards.sh
