# MasterNoder venue cycle circles — backup tick when profit daemon is down.
# Primary loop lives inside scripts/all_profit_daemons.py (cycle_circles thread).
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
* * * * * root /var/www/html/cron/venue_cycle_circles_tick.sh >> /var/www/html/logs/cycle_circles_cron.log 2>&1
