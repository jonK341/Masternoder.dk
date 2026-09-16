# Agent wallet sweeper — every 30 min
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/30 * * * * root /var/www/html/cron/agent_sweeper_tick.sh >> /var/log/masternoder-agent-sweeper.log 2>&1
