# MN2 explorer health probe + Discord alert
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
*/15 * * * * root /var/www/html/cron/mn2_explorer_probe.sh
