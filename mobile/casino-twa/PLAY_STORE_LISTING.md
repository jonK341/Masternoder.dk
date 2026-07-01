# Google Play listing draft — MasterNoder2 Casino

Package: **`dk.masternoder.casino`** · Shell: **TWA (Bubblewrap)** — `mobile/casino-twa/`  
Alt shell: [Capacitor listing](../casino-app/PLAY_STORE_LISTING.md)

Marketing: `docs/CASINO_MARKETING.md` · `data/casino_marketing.json` · `GET /api/casino/marketing`  
Ops: [CASINO_PLAY_STORE_TUESDAY.md](../../docs/CASINO_PLAY_STORE_TUESDAY.md) · [CASINO_DEPLOY_OPS.md](../../docs/CASINO_DEPLOY_OPS.md)

---

## Store listing

| Field | Draft |
|-------|-------|
| **Title** | MasterNoder2 Casino |
| **Short description** | MasterNoder2 Casino — crash, slots, plinko, tournaments & big wins on MN2. |
| **Tagline** | Ride the rocket. Hit the jackpot. Own the lounge. |
| **Full description** | MasterNoder2 Casino is the social gaming lounge on masternoder.dk — crash rockets, slots, plinko, mines, wheel, and classic instant games with friends, crews, and live leaderboards. Play with virtual coins first; MN2 and PayPal USD rails remain on the website with full policy disclosure. Daily wheel, tournaments, hall of fame, Discord big-win sharing. Same account as masternoder.dk. Play responsibly. 18+ where online gambling is licensed. |
| **Category** | Game → Casino (simulated) / Entertainment |
| **Feature graphic** | `/static/img/casino/banner-masternoder2-casino.png` (crop to 1024×500) |
| **Content rating** | Simulated gambling — complete IARC questionnaire honestly |
| **Contact** | https://masternoder.dk |
| **Privacy policy** | https://masternoder.dk (site privacy page) |

---

## Screenshots checklist

- [ ] Lobby / featured games grid with MasterNoder2 banner
- [ ] Crash game in play (multiplier rising)
- [ ] Slots with jackpot meter visible
- [ ] Tournaments panel with countdown
- [ ] Social tab — Discord opt-in + Google Play badge
- [ ] Big-win celebration overlay
- [ ] Phone + tablet form factors (7" and 10")

---

## Pre-upload ops

1. Build AAB with Bubblewrap (`mobile/casino-twa/README.md`) **or** Capacitor (`mobile/casino-app/`)
2. Pay $25 Play Console → create app `dk.masternoder.casino` → upload Internal AAB
3. Copy **Play App Signing** SHA-256 → `python scripts/casino_play_assetlinks_update.py "<SHA>"`
4. Deploy: `python scripts/deploy.py well_known --ask-pass` (+ `deploy.py casino` for web slice)
5. Set `DISCORD_CHANNEL_ID_CASINO` webhook URL on server (not in repo)
6. Cron: `cron/discord_casino_fanout.sh` (dry_run until `CASINO_FANOUT_LIVE=1`)
7. Internal testing → closed testing → production

---

## Deep links (verified in web)

- `https://masternoder.dk/casino/?game=crash` — opens Crash tab
- `https://masternoder.dk/casino/?tab=social` — Social tab
- `https://masternoder.dk/casino/?app=casino-twa&tab=lobby` — TWA start URL
