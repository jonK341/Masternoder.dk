# MasterNoder.dk — monetization retention (daily 09:00 UTC)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 9 * * * root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/monetization_cron.sh
