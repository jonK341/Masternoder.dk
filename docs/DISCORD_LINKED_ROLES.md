# Discord Linked Roles (MasterNoder2 / casino)

Linked Roles let a Discord server grant roles when users connect their MasterNoder account and meet criteria (MN2 balance, casino VIP, hosting VIP).

This repo implements the [Discord Linked Roles](https://docs.discord.com/developers/tutorials/configuring-app-metadata-for-linked-roles) OAuth flow — **not** a passive JSON metadata poll URL.

---

## Verification URL (paste in Developer Portal)

**General Information → Linked Roles Verification URL:**

```
https://masternoder.dk/api/discord/linked-role
```

Local/staging override: set `DISCORD_LINKED_ROLE_VERIFICATION_URL` in `.env`.

---

## OAuth redirect (also required)

Add this redirect under **OAuth2 → Redirects**:

```
https://masternoder.dk/api/discord/linked-role/callback
```

Override with `DISCORD_LINKED_ROLE_REDIRECT_URI` if needed.

---

## Setup checklist

1. **Discord app** — same application as `DISCORD_CLIENT_ID` / bot (`DISCORD_BOT_TOKEN`).
2. **OAuth2 credentials** — set in server `.env`:
   - `DISCORD_CLIENT_ID`
   - `DISCORD_CLIENT_SECRET`
3. **Bot** — install bot on your guild; set `DISCORD_GUILD_ID`, `DISCORD_BOT_TOKEN`.
4. **Verification URL** — paste `https://masternoder.dk/api/discord/linked-role` in Developer Portal → General Information.
5. **Redirect URI** — add `/api/discord/linked-role/callback` under OAuth2 → Redirects.
6. **Register metadata schema (one-time)** — after deploy:

```bash
curl -sS -X POST \
  -H "X-Ops-Secret: $DISCORD_OPS_SECRET" \
  https://masternoder.dk/api/discord/linked-role/register-metadata | jq .
```

7. **Create linked role** — Server Settings → Roles → your role → **Links** → Add requirement → select your app → pick metadata fields (see below).
8. **User flow** — User opens server → Linked Roles → Connect → OAuth → metadata pushed → role granted if requirements match.

Optional: user can link on-site first at `/profile#discord-link` so `account_linked` and balances resolve correctly.

---

## Required env vars

| Variable | Purpose |
|----------|---------|
| `DISCORD_CLIENT_ID` | OAuth app ID (same as Application ID) |
| `DISCORD_CLIENT_SECRET` | OAuth secret for token exchange |
| `DISCORD_BOT_TOKEN` | Register metadata schema (`Bot` auth) |
| `SOCIAL_AUTH_BASE_URL` | Base URL for verification + callback (default `https://masternoder.dk`) |
| `DISCORD_OPS_SECRET` | Protects `POST /api/discord/linked-role/register-metadata` |
| `CASINO_DISCORD_VIP_MIN_MN2` | Min MN2 for `casino_vip` (default `100`) |
| `DISCORD_HOSTING_VIP_ROLE_ID` | Used by bot role grant path (separate from linked roles) |

Optional overrides:

- `DISCORD_LINKED_ROLE_VERIFICATION_URL`
- `DISCORD_LINKED_ROLE_REDIRECT_URI`

---

## Metadata fields (admin-configurable in Discord)

Registered via `PUT /applications/{id}/role-connections/metadata`:

| Key | Name | Type | Source |
|-----|------|------|--------|
| `mn2_balance` | MN2 balance | number greater than | Linked account MN2 balance |
| `casino_vip` | Casino VIP | boolean equals `1` | Linked + min MN2 + geo (`casino_social_service`) |
| `hosting_vip` | Hosting VIP | boolean equals `1` | Paid hosting + linked Discord |
| `account_linked` | Account linked | boolean equals `1` | Discord ID mapped in `logs/user_identifiers/` |

Inspect live schema:

```bash
curl -sS https://masternoder.dk/api/discord/linked-role/schema | jq .
```

---

## Example metadata pushed to Discord

After OAuth, the app `PUT`s to Discord:

`PUT /users/@me/applications/{DISCORD_CLIENT_ID}/role-connection`

```json
{
  "platform_name": "MasterNoder2",
  "metadata": {
    "account_linked": 1,
    "mn2_balance": 250,
    "casino_vip": 1,
    "hosting_vip": 0
  }
}
```

Booleans use `1` / `0`. If the Discord user is not linked to a site account:

```json
{
  "platform_name": "MasterNoder2",
  "metadata": {
    "account_linked": 0,
    "mn2_balance": 0,
    "casino_vip": 0,
    "hosting_vip": 0
  }
}
```

---

## API routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/discord/linked-role` | **Verification URL** — redirects to Discord OAuth (`role_connections.write identify`) |
| `GET` | `/api/discord/linked-role/callback` | OAuth redirect; pushes metadata |
| `GET` | `/api/discord/linked-role/schema` | Verification URL, redirect URI, schema JSON |
| `POST` | `/api/discord/linked-role/register-metadata` | One-time schema registration (ops secret) |
| `GET` | `/api/discord/link/status?user_id=` | On-site link + VIP eligibility |
| `POST` | `/api/discord/link` | Manual Discord ID link |
| `POST` | `/api/discord/link/unlink` | Remove link |

Implementation: `backend/services/discord_linked_roles_service.py`, `backend/routes/discord_routes.py`.

---

## Example linked role requirements

**Casino VIP channel**

- App: MasterNoder
- `account_linked` = `1`
- `casino_vip` = `1`
- Optional: `mn2_balance` > `100`

**Hosting VIP**

- `hosting_vip` = `1`

---

## Related docs

- `docs/CASINO_DEPLOY_OPS.md` — casino Discord fan-out cron
- `docs/MN2_OPS.md` — Discord ops routes and secrets
- Discord tutorial: [Configuring App Metadata for Linked Roles](https://docs.discord.com/developers/tutorials/configuring-app-metadata-for-linked-roles)
