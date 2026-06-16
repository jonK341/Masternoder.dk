# MN2 TODO

Last updated: **2026-06-16** (treasury sign-off gate shipped in code). See [MN2_OPS.md](MN2_OPS.md), [MN2_EXPLORER_PLAN.md](MN2_EXPLORER_PLAN.md).

---

## Done — deployed 2026-06-16

- [x] Explorer overview + 5-day network monitor + Chainz links
- [x] Deposit self-heal, daemon policy, Health Ops Hub UI on `/staking-monitor`
- [x] News page → `GET /api/news/platform?channel=*` (`platform-news.js`)
- [x] Treasury cold-wallet **policy** (MN2_OPS §8.6)
- [x] Deploy manifest fix: `health_routes.py`, `discord_service.py`, `platform_news_routes.py` added to `mn2_staking`

**Live verified:** `/news` dynamic feed ✓ · `/staking-monitor` Health Ops Hub section ✓  
**Needs one more `mn2_staking` deploy** for extended `/api/mn2/health` JSON (`discord_outbox`, `daemon_staking`) — frontend already live.

---

## Done — M8 Discord (code 2026-06-16)

| # | Stream | Status |
|---|--------|--------|
| 51 | Role gating | Live (`/api/discord/casino/vip-check`, link route) |
| 52 | Promo codes | Live (`/api/casino/discord/promo/redeem`) |
| 53 | Alert funnel | **`discord_m8_streams.run_alert_funnel`** + `POST /api/discord/m8/alert-funnel` |
| 54 | Partner spotlight | **`publish_partner_spotlight`** + `POST /api/discord/m8/partner-spotlight` |
| 55 | Daily digest | Live (`run_daily_digest`, cron) |
| 56 | Quest bot | **`run_quest_bot_digest`** + `POST /api/discord/m8/quest-bot` |
| 57 | Affiliate rotator | **`affiliate_rotator_payload`** + `POST /api/discord/m8/affiliate-rotator` |
| 58 | Casino highlights | Live (`casino_discord_fanout`) |
| 59 | Generator showcase | **`post_generator_showcase`** (hook on clip job complete) |
| 60 | Support FAQ | **`GET /api/discord/support/faq?q=`** |

Deploy: `python scripts/deploy.py mn2_staking --ask-pass` (includes M8 + health backend).

---

## Critical (ops sign-off)

- [x] **Treasury cold-wallet sign-off (code)** — `treasury_signoff_service.py`, `GET/POST /api/agents/treasury/sign-off`, gate on `distribute` ≥100k MN2; CLI `scripts/treasury_signoff.py`

**Activate on production** (deploy + scan + distribute):

```powershell
python scripts/deploy.py mn2_staking --ask-pass
# on server: trigger deposit scan, then check pool:
# curl -s -H "X-Ops-Secret: $SECRET" http://127.0.0.1:5000/api/agents/treasury/address
# curl -s -X POST -H "X-Ops-Secret: $SECRET" http://127.0.0.1:5000/api/mn2/scan-deposits
# curl -s -X POST -H "X-Ops-Secret: $SECRET" http://127.0.0.1:5000/api/agents/treasury/distribute
```

Hot treasury deposit address (production): `JJi8g5CYTXL6NVW1za4tJtzC1X61M7WRZi` — send agent funding here (not cold wallet).

---

## Ops / daemon

- [ ] **Daemon staking active** — `mnsync` + minting (watch Health Ops Hub on `/staking-monitor`)
- [ ] **Standalone explorer E1** — verify address/tx/richlist on camgirls when index caught up

---

## Deferred

- [ ] Multi-source MN2 USD price median
- [ ] SSE live updates for `/explorer`
- [ ] Optional `explorer_use_local_stats: true` (tiles only; links stay Chainz)
