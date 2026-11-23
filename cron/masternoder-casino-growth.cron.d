# Casino growth — weekly email digest + daily free-flip push
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=""

# Monday 10:00 UTC — win + Invite Party email digest
0 10 * * 1 root /var/www/html/cron/casino_win_digest.sh >/dev/null 2>&1

# Daily 16:00 UTC — free daily flip push reminder
0 16 * * * root /var/www/html/cron/casino_push_daily.sh >/dev/null 2>&1
