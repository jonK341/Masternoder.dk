# Discord server + Developer Portal setup

## Why Interactions Endpoint URL verification failed

1. **Trailing slash** — Portal URL must be exactly `https://masternoder.dk/api/discord/interactions` (no `/` at end). Both paths work on the server, but enter the URL without a trailing slash in the Developer Portal.
2. **Route not deployed** — If GET returns `Endpoint auto-created` or 404, deploy `mn2_staking` (includes `discord_routes.py`) and restart uwsgi.
3. **PING must return PONG** — Discord sends a signed POST `{"type":1}`. The server must respond within 3 seconds with HTTP 200 and body `{"type":1}`. `DISCORD_PUBLIC_KEY` must be set in server `.env` (General Information → Public Key) for non-PING slash commands; PING is answered before signature checks.
4. **Wrong Application ID** — `DISCORD_APPLICATION_ID` must be the **Application ID** from General Information (17–20 digit snowflake), **not** `DISCORD_HOSTING_VIP_ROLE_ID`. Check: `GET /api/discord/setup/portal-urls` — if `issues` contains “looks like a role ID”, fix `.env` and redeploy `mn2_env`.
5. **Re-save after deploy** — If the endpoint was broken when you first saved the URL, fix deploy/env then click **Save** again in the Developer Portal.

## Interactions Endpoint URL (Developer Portal)

```
https://masternoder.dk/api/discord/interactions
```

## Terms of Service URL

```
https://masternoder.dk/legal/terms/
```

## Privacy Policy URL

```
https://masternoder.dk/legal/privacy/
```

## Linked Roles Verification URL

```
https://masternoder.dk/api/discord/role-connection/callback
```

Also add the same URL under **OAuth2 → Redirects** in the Developer Portal.

User-friendly page: `https://masternoder.dk/discord/verify/`

**Role connection metadata keys** (define in Portal → Linked Roles):

| Key | Type | Meaning |
|-----|------|---------|
| `linked` | string | `1` when Discord is linked to a site account |
| `hosting_customer` | `1` when user has paid masternode hosting |

Copy all URLs: `GET https://masternoder.dk/api/discord/setup/portal-urls`

## How to find the Discord bot token

1. Open [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your app (**MasterNoder2 casino Stream**)
3. Left sidebar → **Bot**
4. Click **Reset Token** → confirm
5. **Copy immediately** (Discord only shows it once)
6. Paste into server `.env`:
   ```
   DISCORD_BOT_TOKEN=paste_here
   ```
7. Restart uwsgi: `sudo systemctl restart uwsgi`

Never commit the token to git or share it in chat.

Health check (browser):

```
https://masternoder.dk/api/discord/interactions
```

Returns JSON with `service: discord_interactions` when deployed.

## App description & tags

Copy from `GET /api/discord/setup/profile` or `data/discord_app_profile.json`.

**Description:** Official MasterNoder controller for casino play, MN2 masternode hosting, shop checkout, and daily quests. Slash commands open the full site — PayPal deposits, MN2/crypto buy-ins, Discord play-earn, and hosting VIP rewards.

**Tags:** casino, crypto, mn2, masternode, gaming, play-to-earn, paypal, staking, ai, generator

## Icon & banner (PNG + GIF)

Assets live in `static/discord-branding/`:

| File | Use |
|------|-----|
| `discord-app-icon.png` | 1024×1024 app icon |
| `discord-app-icon.gif` | Animated icon (optional) |
| `discord-app-banner.png` | 680×240 banner |
| `discord-app-banner.gif` | Animated banner |

Regenerate locally:

```bash
python scripts/build_discord_branding.py
```

Upload in Developer Portal → **Bot** → Icon / Banner.

## Server channel layout

See `data/discord_server_setup.json` or `GET /api/discord/setup/server`.

Categories: **Announcements**, **Casino & Play**, **Hosting & Market**, **Create & Quest**, **Community**.

Create webhooks per channel → set full webhook URLs in `.env`:

- `DISCORD_CHANNEL_ID_CASINO`
- `DISCORD_CHANNEL_ID_ANNOUNCEMENTS`
- `DISCORD_CHANNEL_ID_GENERATOR`
- `DISCORD_CHANNEL_ID_GAME`
- `DISCORD_CHANNEL_ID_MARKET`
- `DISCORD_CHANNEL_ID_MN2`

(`DISCORD_CHANNEL_ID_*` values must be **webhook URLs**, not numeric channel IDs.)

## MN2 channel (terminal)

Config: `data/discord_mn2_channel.json` · CLI: `scripts/discord_mn2_channel.py`

```bash
python scripts/discord_mn2_channel.py show
python scripts/discord_mn2_channel.py set-channel YOUR_CHANNEL_SNOWFLAKE
python scripts/discord_mn2_channel.py set-topic "MN2 hub — /mn2 for status" --apply
python scripts/discord_mn2_channel.py set-webhook "https://discord.com/api/webhooks/..."
python scripts/discord_mn2_channel.py set-stream market on
python scripts/discord_mn2_channel.py test-post
python scripts/discord_mn2_channel.py reload
python scripts/discord_mn2_channel.py post-info --force
```

Slash command `/mn2` shows live service status + earn links. Re-register commands after deploy:

```bash
python scripts/discord_register_commands.py
```

## Deploy + register commands

**From Windows (PowerShell)** — deploy code + `.env`, then restart uwsgi on the server:

```powershell
cd C:\Users\jonkh\UsecaseSampler\Masternoder.dk
python scripts/deploy.py mn2_staking mn2_env --ask-pass
```

`chmod +x` is **Linux-only**; do not run it in PowerShell. On the server (SSH), or from Windows:

```powershell
python scripts/mn2_ops_optionals_remote.py --ask-pass --all
```

**On server (SSH)** after deploy:

```bash
sudo systemctl restart uwsgi
cd /var/www/html && python3 scripts/discord_register_commands.py
```

Register slash commands (ops):

```bash
curl -X POST -H "X-Ops-Secret: YOUR_DISCORD_OPS_SECRET" \
  https://masternoder.dk/api/discord/setup/register-commands
```

## Required `.env` keys

| Key | Source |
|-----|--------|
| `DISCORD_BOT_TOKEN` | Developer Portal → Bot → Reset Token |
| `DISCORD_APPLICATION_ID` | General Information → Application ID (= Client ID) |
| `DISCORD_PUBLIC_KEY` | General Information → Public Key |
| `DISCORD_GUILD_ID` | Right-click server → Copy Server ID |
| `DISCORD_HOSTING_VIP_ROLE_ID` | Server Settings → Roles → Copy role ID |
| `DISCORD_OPS_SECRET` | Your ops secret for cron/admin routes |

## Verify (before re-saving Portal URL)

**PowerShell** — use `curl.exe` (PowerShell aliases `curl` to `Invoke-WebRequest`):

```powershell
# GET health — expect service: discord_interactions
curl.exe -s https://masternoder.dk/api/discord/interactions

# POST PING — expect {"type":1} and HTTP 200
'{"type":1}' | Out-File -Encoding ascii -NoNewline tmp_ping.json
curl.exe -s -w "`nHTTP:%{http_code}`n" -X POST https://masternoder.dk/api/discord/interactions -H "Content-Type: application/json" -d "@tmp_ping.json"
Remove-Item tmp_ping.json

# Env / portal URL checklist (no secrets in response)
curl.exe -s https://masternoder.dk/api/discord/setup/portal-urls
curl.exe -s https://masternoder.dk/api/discord/controller/status
```

**Linux / SSH:**

```bash
curl -s https://masternoder.dk/api/discord/interactions
curl -s -X POST https://masternoder.dk/api/discord/interactions -H "Content-Type: application/json" -d '{"type":1}'
curl -s https://masternoder.dk/api/discord/setup/portal-urls | python3 -m json.tool
```

Expect GET: `"service":"discord_interactions"`. POST PING: `{"type":1}`. `portal-urls` → `env.issues` should be empty (fix `DISCORD_APPLICATION_ID` if it mentions role ID). Not `auto_fixed: true` or `Endpoint auto-created`.
