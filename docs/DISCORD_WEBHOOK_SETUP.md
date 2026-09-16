# Discord webhook setup (casino & related channels)

Beginner-friendly guide for posting casino big wins, jackpots, and tournaments to your Discord server. This covers **outbound webhooks** only (messages *from* MasterNoder *to* Discord). Slash commands and the Interactions Endpoint are documented in [DISCORD_INTERACTIONS.md](DISCORD_INTERACTIONS.md).

**Casino deploy checklist:** [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) § C.3.

---

## Quick answer: what goes in `.env`?

| Variable | Webhook URL or ID? | Purpose |
|----------|-------------------|---------|
| `DISCORD_CHANNEL_ID_CASINO` | **Full webhook URL** | Casino big wins, jackpots, tournament start/end/prizes → `#casino` |
| `DISCORD_WEBHOOK_URL` | **Full webhook URL** | Default fallback when a per-channel var is empty |
| `DISCORD_CHANNEL_ID_MARKET` | **Full webhook URL** (optional) | Trader market spotlight posts → `#market` |
| `DISCORD_CHANNEL_ID_GAME` | **Full webhook URL** (optional) | Game hub posts |
| `DISCORD_CHANNEL_ID_GENERATOR` | **Full webhook URL** (optional) | Generator news |
| `DISCORD_CHANNEL_ID_ANNOUNCEMENTS` | **Full webhook URL** (optional) | Announcements |
| `DISCORD_CHANNEL_ID_OPS` | **Full webhook URL** (optional) | Ops / internal alerts |
| `DISCORD_GUILD_ID` | **Numeric server ID** | Bot role grants, linked roles (not a webhook) |
| `DISCORD_BOT_TOKEN` | **Bot token** | Discord API (roles, linked roles) — never a webhook |
| `DISCORD_PUBLIC_KEY` | **64-char hex** | Interactions endpoint verification — not a webhook |
| `DISCORD_CLIENT_ID` | **Application ID** | OAuth / linked roles — not a webhook |
| `DISCORD_OPS_SECRET` | **Your own secret string** | Protects `POST /api/discord/*` cron and ops routes |

Despite the `DISCORD_CHANNEL_ID_*` naming, those variables expect a **full webhook URL**, not a channel snowflake. The code rejects bare numeric IDs with `invalid_webhook:… is a numeric channel ID` (see `backend/services/discord_service.py`).

If `DISCORD_CHANNEL_ID_CASINO` is empty, casino fan-out falls back to `DISCORD_WEBHOOK_URL` — posts may land in the wrong channel.

---

## How Discord webhooks work (30 seconds)

A **webhook** is a private URL Discord gives you for one channel. Anyone who has the URL can post messages there. MasterNoder stores the URL in server `.env` and POSTs JSON when casino events happen (via cron fan-out).

**Never** commit webhook URLs to git, paste them in chat, or screenshot them. If a URL leaks, delete the webhook in Discord and create a new one.

---

## Step-by-step: create a webhook in Discord

### 1. Open your server

1. Open the **Discord** desktop or web app.
2. In the left sidebar, select your MasterNoder server.
   - Guild ID (if you need to confirm): `1061038150920704112` should match `DISCORD_GUILD_ID` in `.env`.
3. You need **Manage Webhooks** permission (Server owner or Admin).

**What you should see:** Your server name at the top of the channel list; channels like `#general`, `#casino`, etc.

### 2. Open Server Settings → Integrations

1. Click the **server name** at the top of the channel list.
2. Choose **Server Settings**.
3. In the left menu, click **Integrations**.
4. Click **Webhooks** (or **View Webhooks**).

**What you should see:** A list of existing webhooks (may be empty) and a **New Webhook** or **Create Webhook** button.

### 3. Create the casino webhook

1. Click **New Webhook** (or **Create Webhook**).
2. **Name:** e.g. `MasterNoder Casino`.
3. **Channel:** pick `#casino`.
   - If `#casino` does not exist: create it first (right-click channel list → **Create Channel** → Text → name `casino`).
4. Optional: click the webhook avatar to set an icon.
5. Click **Copy Webhook URL**.

**What you should see:** A URL like:

```
https://discord.com/api/webhooks/1234567890123456789/AbCdEfGhIjKlMnOpQrStUvWxYz1234567890_AbCdEfGh
```

That is two parts: numeric webhook ID + secret token. Treat the whole string as a password.

### 4. Paste into server `.env`

On the **production server** (SSH), edit `.env`:

```bash
nano /var/www/html/.env
```

Add or update this line (use your real URL from step 3):

```env
DISCORD_CHANNEL_ID_CASINO=https://discord.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN
```

**Do not** wrap the URL in quotes unless your deploy tooling requires it. Put comments on their own line above the variable — not inline after the URL.

**Optional — dedicated market webhook:** repeat steps 3–4 for `#market` and set:

```env
DISCORD_CHANNEL_ID_MARKET=https://discord.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN
```

**Optional — default fallback** (used when a per-channel var is empty):

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN
```

### 5. Reload the app so uWSGI picks up `.env`

From your dev machine (after uploading `.env` if needed):

```bash
python scripts/deploy_all_and_restart_uwsgi.py --no-upload
```

Or on the server directly:

```bash
systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
# or: touch /var/www/html/.uwsgi_touch_reload
```

See [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) for full casino deploy steps.

---

## Which code uses which variable?

| Feature | Env var | Code path |
|---------|---------|-----------|
| Casino big win / jackpot / tournament embeds | `DISCORD_CHANNEL_ID_CASINO` | `casino_discord_fanout.py` → `post_message("casino", …)` |
| Market spotlight fan-out | `DISCORD_CHANNEL_ID_MARKET` | `market_discord_fanout.py` |
| Default channel when no override | `DISCORD_WEBHOOK_URL` | `discord_service._webhook_for_channel` |
| Cron / ops API auth | `DISCORD_OPS_SECRET` | `POST /api/discord/casino/fanout`, other `/api/discord/*` |

Config reference: `data/casino_config.json` → `discord_integration.webhook_env` = `DISCORD_CHANNEL_ID_CASINO`.

---

## Test the webhook (without exposing the URL)

### Direct POST (on server — URL stays in env)

```bash
# Load URL from .env without printing it
source <(grep '^DISCORD_CHANNEL_ID_CASINO=' /var/www/html/.env | sed 's/^/export /')

curl -sS -X POST "$DISCORD_CHANNEL_ID_CASINO" \
  -H "Content-Type: application/json" \
  -d '{"content":"Casino webhook test from MasterNoder"}'
```

**Success:** HTTP 204 (no body) or 200; a test message appears in `#casino`.

**Failure:** `401` / `404` → wrong or deleted webhook; create a new webhook and update `.env`.

### Test via MasterNoder API (dry run — no Discord post)

```bash
SECRET=$(grep '^DISCORD_OPS_SECRET=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')

curl -sS -X POST https://masternoder.dk/api/discord/casino/fanout \
  -H "X-Ops-Secret: $SECRET" \
  -H "Content-Type: application/json" \
  -d '{"dry_run":true}'
```

`dry_run: true` processes events but does not POST to Discord. Use this to confirm auth and fan-out logic before going live.

### Masked local audit (safe — no secrets printed)

```bash
python scripts/_discord_env_audit_masked.py
```

Reports `empty` vs `set (webhook URL, masked)` for each `DISCORD_*` line in local `.env`.

---

## Cron: automatic casino posts

After the webhook is set, enable the fan-out cron (every 5 minutes):

```bash
chmod +x /var/www/html/cron/discord_casino_fanout.sh
crontab -l 2>/dev/null | grep -v discord_casino_fanout
echo '*/5 * * * * /var/www/html/cron/discord_casino_fanout.sh' | crontab -
```

The script calls `POST /api/discord/casino/fanout` with `DISCORD_OPS_SECRET` (or `MN2_OPS_SECRET`). See [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) § C.3.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Posts go to wrong channel | `DISCORD_CHANNEL_ID_CASINO` empty | Set dedicated `#casino` webhook URL |
| `invalid_webhook:… numeric channel ID` | Bare channel snowflake in `DISCORD_CHANNEL_ID_*` | Use full `https://discord.com/api/webhooks/…` URL |
| `webhook_not_configured` in outbox | Both per-channel and `DISCORD_WEBHOOK_URL` empty | Set at least one webhook URL |
| `HTTP 403` on POST | Cloudflare or revoked webhook | Regenerate webhook; code sends `User-Agent: MasternoderBot/1.0` |
| Fan-out API returns 401 | Wrong `DISCORD_OPS_SECRET` | Match header `X-Ops-Secret` to server `.env` |
| Messages never appear | Cron not installed or cursor stuck | Check `logs/discord_outbox.jsonl` and cron logs |

---

## Security reminders

1. **Rotate** any webhook URL that was ever pasted in chat, committed to git, or shared in a screenshot. Discord → Integrations → Webhooks → delete old → create new → update `.env`.
2. **Never** put webhook URLs in the repository. `.env` is gitignored.
3. `DISCORD_OPS_SECRET` is separate from the webhook — protect both.
4. For interactions / slash commands (inbound from Discord), see [DISCORD_INTERACTIONS.md](DISCORD_INTERACTIONS.md). For linked roles OAuth, see [DISCORD_LINKED_ROLES.md](DISCORD_LINKED_ROLES.md).

---

## Related docs

- [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) — full casino production checklist
- [DISCORD_INTERACTIONS.md](DISCORD_INTERACTIONS.md) — Interactions Endpoint (inbound)
- [MN2_OPS.md](MN2_OPS.md) — market fan-out and ops secrets
- `.env.example` — commented list of all `DISCORD_*` variables
