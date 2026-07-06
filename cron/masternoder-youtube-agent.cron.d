# YouTube content automation agent
# Copy to /etc/cron.d/masternoder-youtube-agent
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Every 10 hours: generate content package for YouTube agent.
# Optional upload/live are controlled by env vars in shell/.env:
#   YOUTUBE_ENABLE_UPLOAD=1
#   YOUTUBE_ENABLE_LIVE=1
20 */10 * * * root /var/www/html/cron/youtube_content_agent.sh >> /var/log/masternoder-youtube-agent.log 2>&1
