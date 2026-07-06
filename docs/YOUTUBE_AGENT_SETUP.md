# YouTube Agent Setup (upload + livestream + monetization)

This project now includes a YouTube automation agent:

- `scripts/youtube_channel_agent.py`
- `cron/youtube_content_agent.sh`
- `cron/masternoder-youtube-agent.cron.d`

It generates content packages from:

- `reports/trading_content/trading_content_report_latest.json`

## 1) Channel setup fix checklist

1. Confirm channel ownership in YouTube Studio.
2. Enable 2FA on the Google account used for API access.
3. In Google Cloud Console:
   - Enable **YouTube Data API v3**
   - Create OAuth client credentials (Desktop app)
4. Save OAuth client secrets at:
   - `config/youtube_client_secrets.json`
5. Set environment variables:
   - `YOUTUBE_CHANNEL_ID=<your_channel_id>` (preferred)
   - or `YOUTUBE_CHANNEL_HANDLE=<@handle>`
6. For uploads/live automation:
   - `YOUTUBE_ENABLE_UPLOAD=1`
   - `YOUTUBE_ENABLE_LIVE=1` (optional)
7. First upload/live run must be interactive to mint token:
   - `config/youtube_token.json`

## 2) Generate content package

Run:

- `python3 scripts/youtube_channel_agent.py --print-json`

Outputs include:

- `reports/youtube_agent/latest/youtube_upload_metadata.json`
- `reports/youtube_agent/latest/video_script_30s.txt`
- `reports/youtube_agent/latest/shorts_script.txt`
- `reports/youtube_agent/latest/livestream_plan.txt`
- `reports/youtube_agent/latest/monetization_plan.txt`
- `reports/youtube_agent/latest/channel_fix_checklist.md`

## 3) Upload video (when credentials are ready)

Run:

- `python3 scripts/youtube_channel_agent.py --upload --video-file /path/to/video.mp4`

## 4) Schedule livestream event

Run:

- `python3 scripts/youtube_channel_agent.py --create-live --live-start-hours 24`

## 5) Cron automation (every 10 hours)

Install cron file:

- copy `cron/masternoder-youtube-agent.cron.d` to `/etc/cron.d/masternoder-youtube-agent`

Cron runner:

- `cron/youtube_content_agent.sh`

It always generates fresh content package.
Upload/livestream API writes run only when enabled via env vars.

## Monetization strategy baked into outputs

The agent writes a monetization plan for:

- Long-form weekly recap
- Daily Shorts top-of-funnel
- Live streams (super chats/memberships/sponsors)
- CTA conversion toward paid analytics/services
