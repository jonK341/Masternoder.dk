# Discord Interactions Endpoint (MasterNoder2)

Discord can deliver slash commands, buttons, and other interactions via HTTP POST instead of the Gateway. This repo exposes the **Interactions Endpoint URL** used when you save that field in the [Discord Developer Portal](https://discord.com/developers/applications).

Reference: [Interactions and Activities](https://discord.com/developers/docs/interactions/overview) · [Request Verification](https://discord.com/developers/docs/interactions/receiving-and-responding#security-and-authorization)

---

## Interactions Endpoint URL (paste in Developer Portal)

**General Information → Interactions Endpoint URL:**

```
https://masternoder.dk/api/discord/interactions
```

When you save this URL, Discord sends a signed `PING` (`type: 1`). The server must respond with `{"type": 1}` (PONG). Signature verification uses your app **Public Key** from the same page.

---

## Required environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `DISCORD_PUBLIC_KEY` | **Yes (production)** | 64-character hex Ed25519 public key from Developer Portal → General Information. Used to verify `X-Signature-Ed25519` + `X-Signature-Timestamp` on every POST. |
| `DISCORD_CLIENT_ID` | For slash commands later | Same as **Application ID** in the portal. Not read by the interactions route today; needed when registering commands via Discord API. |

Optional (outbound Discord — not the interactions endpoint itself):

- `DISCORD_BOT_TOKEN` — bot API calls, linked roles, future command registration
- `DISCORD_WEBHOOK_URL` / `DISCORD_CHANNEL_ID_*` — outbound posts (news, casino fan-out)
- `DISCORD_OPS_SECRET` — cron/ops routes under `/api/discord/*`

**Webhook setup (casino, market, testing):** [DISCORD_WEBHOOK_SETUP.md](DISCORD_WEBHOOK_SETUP.md)

See `.env.example` (Discord section) and `docs/DISCORD_LINKED_ROLES.md` for linked-role OAuth vars.

**Public key format:** 64 hex chars; optional `0x` prefix and surrounding quotes are stripped. If unset locally, signature verify is skipped (tests only — **always set on production**).

---

## What the endpoint supports today

| Interaction `type` | Name | Response |
|--------------------|------|----------|
| `1` | PING | `200` + `{"type": 1}` |
| Other | — | `501` + `unsupported_interaction_type` |

**Slash commands:** not implemented yet. Casino activity reaches Discord via **webhook fan-out** (`POST /api/discord/casino/fanout` cron), not slash commands. Planned examples for a future pass: `/casino status`, `/casino jackpot`.

**Related routes (same blueprint):**

- `GET /api/discord/status` — webhook + interactions public-key diagnostics
- `POST /api/discord/post` — ops outbound message
- `POST /api/discord/casino/fanout` — casino activity → `#casino`
- Linked roles — see `docs/DISCORD_LINKED_ROLES.md`

Implementation: `backend/routes/discord_routes.py` · tests: `tests/unit/test_discord_interactions.py`

---

## Setup checklist

1. **Discord app** — use the same application as `DISCORD_CLIENT_ID` / bot.
2. **Copy Public Key** — Developer Portal → **General Information** → Public Key → set on server as `DISCORD_PUBLIC_KEY` (must match portal exactly).
3. **Deploy env + reload** — ensure production `.env` has the key, then reload uWSGI (e.g. `python scripts/deploy.py …` or your usual deploy path including `backend/routes/discord_routes.py`).
4. **Paste Interactions Endpoint URL** — `https://masternoder.dk/api/discord/interactions` → Save. Discord should show verification success (signed PING/PONG).
5. **Verify** — `GET https://masternoder.dk/api/discord/status` should show:
   - `interactions_public_key_configured: true`
   - `interactions_public_key_valid_length: true`
   - `interactions_endpoint: https://masternoder.dk/api/discord/interactions`
6. **Optional local signed probe** — `python scripts/_discord_signed_ping_local.py` (dev) or `python scripts/_discord_prod_signed_probe.py` (prod sanity check).

---

## Security notes

- Signatures are verified with Ed25519: `verify(signature, timestamp + raw_body)` per Discord docs.
- `signal_processor_middleware` skips JSON pre-processing on `/api/discord/interactions` so the raw body matches Discord’s signature.
- Nginx must forward `X-Signature-Ed25519` and `X-Signature-Timestamp` to uWSGI (inspect with `scripts/_nginx_discord_headers_remote.py` if verification fails behind the proxy).

---

## Deploy needed?

**Yes**, if production does not yet have:

- `backend/routes/discord_routes.py` (interactions route + signature verify), or
- `DISCORD_PUBLIC_KEY` in server `.env`, or
- a uWSGI reload after env changes.

After deploy, save the Interactions Endpoint URL in the portal (step 4 above). No separate Discord Gateway connection is required for HTTP interactions.

---

## Troubleshooting — “Interactions Endpoint URL could not be verified”

Discord shows this when its signed `PING` does not get `200` + `{"type":1}` back. Work through these checks in order.

### 1. Route deployed (not 404)

```bash
curl -sS -X POST "https://masternoder.dk/api/discord/interactions" \
  -H "Content-Type: application/json" -d "{}"
```

| Response | Meaning |
|----------|---------|
| `404` | Route not deployed — deploy `backend/routes/discord_routes.py` and restart uWSGI |
| `401` + `missing_signature_headers` | Route live; signature gate active (expected for unsigned curl) |
| `501` + `unsupported_interaction_type` | Route live but `DISCORD_PUBLIC_KEY` unset (verify skipped — set key in production) |

### 2. Public key diagnostics

```bash
curl -sS "https://masternoder.dk/api/discord/status"
```

After deploy of commit `1634531`+, expect:

- `interactions_public_key_configured: true`
- `interactions_public_key_valid_length: true`

If those fields are **missing**, production is on an older `discord_routes.py` — redeploy and restart uWSGI.

### 3. `DISCORD_PUBLIC_KEY` must match Developer Portal exactly

1. Open [Discord Developer Portal](https://discord.com/developers/applications) → your app → **General Information**.
2. Copy **Public Key** (64 hex chars, same application as **Application ID** / `DISCORD_CLIENT_ID`).
3. Set on server in `/var/www/html/.env`:

   ```
   DISCORD_PUBLIC_KEY=<64-char-hex-from-portal>
   ```

4. **Reload uWSGI** after any `.env` change (env is read at worker start):

   ```bash
   python scripts/deploy_all_and_restart_uwsgi.py --no-upload
   ```

5. Confirm local and server keys match (prints SHA-256 fingerprints only, not secrets):

   ```bash
   python scripts/_discord_public_key_fingerprint.py
   python scripts/_discord_public_key_remote_shape.py
   ```

Wrong key → Discord’s signed `PING` gets `401 invalid_signature` → portal verification fails.

### 4. Middleware must not parse JSON before the route

Deploy `backend/middleware/signal_processor_middleware.py` (skips `/api/discord/interactions`). On server, this line must exist:

```python
if request.path == "/api/discord/interactions":
    return
```

Check remotely: `grep discord/interactions /var/www/html/backend/middleware/signal_processor_middleware.py`

### 5. Nginx / proxy headers

Nginx `proxy_pass` to Flask forwards client headers by default. Discord sends `X-Signature-Ed25519` and `X-Signature-Timestamp` (hyphens, not underscores). Inspect with `python scripts/_nginx_discord_headers_remote.py` if needed.

### 6. Retry in Developer Portal

After env + deploy + uWSGI reload:

1. **General Information → Interactions Endpoint URL** → paste `https://masternoder.dk/api/discord/interactions`
2. Click **Save Changes** — Discord sends a fresh signed `PING`.

### 7. Safe to skip?

**Yes — optional for now.** The Interactions Endpoint is only required for **slash commands / buttons delivered over HTTP**. These still work without it:

- Outbound **webhooks** (`DISCORD_WEBHOOK_URL`, casino fan-out)
- **Linked roles** OAuth (`/api/discord/linked-role`)
- Account **link** routes

Add the endpoint when you register slash commands (e.g. `/casino status`).

---

## Related `.env` mistakes (outbound / roles — not interactions)

These do **not** block Interactions Endpoint verification but break other Discord features:

| Issue | Symptom | Fix |
|-------|---------|-----|
| `DISCORD_HOSTING_VIP_ROLE_ID` truncated (e.g. 18 digits, looks like Application ID minus last digit) | Bot `PUT …/roles/{role_id}` returns `404 Unknown Role` | Discord → Server Settings → Roles → right-click role → **Copy Role ID** (Developer Mode on). Must be the **role** snowflake, not Application ID. |
| `DISCORD_CHANNEL_ID_CASINO=` empty | Casino fan-out posts to `DISCORD_WEBHOOK_URL` default channel, not `#casino` | Create a webhook for `#casino` → set `DISCORD_CHANNEL_ID_CASINO=https://discord.com/api/webhooks/…` |
| Numeric value in `DISCORD_CHANNEL_ID_*` | `invalid_webhook:… is a numeric channel ID` in outbox | Vars named `DISCORD_CHANNEL_ID_*` expect a **full webhook URL**, not a channel snowflake (`discord_service._webhook_for_channel`). |
| `DISCORD_APPLICATION_ID` set but `DISCORD_CLIENT_ID` empty | OAuth / linked roles fail | Code reads `DISCORD_CLIENT_ID` only; `DISCORD_APPLICATION_ID` is redundant — set `DISCORD_CLIENT_ID` to Application ID. |
| Inline `# comment` on same line as a secret | Rare parsers include comment in value | Put comments on their own line above the variable. |

Confirm local vs server public key (fingerprints only):

```bash
python scripts/_discord_public_key_fingerprint.py
```
