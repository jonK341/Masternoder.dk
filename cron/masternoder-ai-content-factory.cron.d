# AI content factory (fresh video ideas/jobs + optional live trigger)
# Copy to /etc/cron.d/masternoder-ai-content-factory
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Every 10 hours (offset so trading report refresh can complete first)
10 */10 * * * root /var/www/html/cron/ai_content_factory.sh >> /var/log/masternoder-ai-content-factory.log 2>&1
