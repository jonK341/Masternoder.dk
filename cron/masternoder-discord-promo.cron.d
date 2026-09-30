# MasterNoder.dk — shop promo rotator (Mon/Wed/Fri 10:00 UTC)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 10 * * 1,3,5 root /var/www/html/cron/discord_promo_rotator.sh
