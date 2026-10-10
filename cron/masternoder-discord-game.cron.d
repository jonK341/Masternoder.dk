# MasterNoder.dk — game/battle Discord fan-out (every 15 min)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
*/15 * * * * root /var/www/html/cron/discord_game_fanout.sh
