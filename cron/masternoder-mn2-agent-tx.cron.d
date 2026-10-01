# MN2 agent transaction cron — copy to /etc/cron.d/masternoder-mn2-agent-tx
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

*/2 * * * * root /var/www/html/cron/mn2_agent_transactions.sh
