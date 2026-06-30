# Google Play listing draft — MasterNoder2 Casino

Package: `dk.masternoder.casino` · TWA shell: `mobile/casino-twa/`

Marketing source: `docs/CASINO_MARKETING.md` · `data/casino_marketing.json` · `GET /api/casino/marketing`

## Store listing

| Field | Draft |
|-------|-------|
| **Title** | MasterNoder2 Casino |
| **Short description** | MasterNoder2 Casino — crash, slots, plinko, tournaments & big wins on MN2. |
| **Full description** | MasterNoder2 Casino is the premium social gaming lounge on masternoder.dk — crash rockets, slot jackpots, plinko drops, and classic instant games with friends, crews, and live leaderboards. Play with virtual coins first; MN2 and PayPal USD rails remain on the website with full policy disclosure. Daily wheel, tournaments, hall of fame, Discord big-win sharing. Same account as masternoder.dk. Play responsibly. 18+ where online gambling is licensed. |
| **Category** | Casino (simulated) / Entertainment |
| **Feature graphic** | `/static/img/casino/banner-masternoder2-casino.png` (crop to 1024×500) |
| **Content rating** | Simulated gambling disclosure required |
| **Contact** | https://masternoder.dk |
| **Privacy policy** | https://masternoder.dk (site privacy page) |

## Screenshots checklist

- [ ] Lobby / featured games grid with MasterNoder2 banner
- [ ] Crash game in play (multiplier rising)
- [ ] Slots with jackpot meter visible
- [ ] Tournaments panel with countdown
- [ ] Social tab — Discord opt-in + Google Play badge
- [ ] Big-win celebration overlay
- [ ] Phone + tablet form factors (7" and 10")

## Pre-upload ops

1. Build AAB with Bubblewrap (`mobile/casino-twa/README.md`)
2. Copy **Play App Signing** SHA-256 into `static/.well-known/assetlinks.json`
3. Deploy web slice: manifest, assetlinks, casino HTML/JS/CSS, banner assets
4. Set `DISCORD_CHANNEL_ID_CASINO` webhook URL on server (not in repo)
5. Cron: `cron/discord_casino_fanout.sh` every 15 minutes
6. Internal testing track → closed testing → production

## Deep links (verified in web)

- `https://masternoder.dk/casino/?game=crash` — opens Crash tab
- `https://masternoder.dk/casino/?tab=social` — Social tab
- `https://masternoder.dk/casino/?app=casino-twa&tab=lobby` — TWA start URL
