# Master content pipeline (report -> AI content factory -> YouTube)
# Copy to /etc/cron.d/masternoder-content-pipeline
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Every 10 hours
5 */10 * * * root /var/www/html/cron/content_pipeline_master.sh >> /var/log/masternoder-content-pipeline.log 2>&1
