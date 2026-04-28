# MasterNoder.dk — reporter_agent knowledge-sharing ingredients (daily)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 6 * * * root KNOWLEDGE_REPORT_ENV_FILE=/var/www/html/.env /var/www/html/cron/knowledge_sharing_report.sh
