# Security sweep cron — conservation, drift, deposits, avatar backfill
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
15 */4 * * * root AGENTS_CRON_ENV_FILE=/var/www/html/.env /var/www/html/cron/security_sweep.sh >> /var/log/agents-security-sweep.log 2>&1
