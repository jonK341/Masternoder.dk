# Google Play listing draft — MasterNoder Casino Social

Package: `dk.masternoder.casino` · TWA shell: `mobile/casino-twa/`

## Store listing

| Field | Draft |
|-------|-------|
| **Title** | MasterNoder Casino Social |
| **Short description** | Social casino lounge — crash, slots, plinko, tournaments, and big-win sharing. |
| **Full description** | MasterNoder Casino Social is the mobile home for the MasterNoder virtual casino. Play crash, plinko, mines, wheel, slots, and classic arcade games with virtual coins. Climb tournament leaderboards, follow the live winners feed, and share big wins to Discord and Facebook. Same account as masternoder.dk — friends, crews, and casino progress stay in sync. MN2 and PayPal USD rails remain on the website with full policy disclosure; the Play build focuses on virtual-currency entertainment. Play responsibly. 18+ where online gambling is licensed. |
| **Category** | Casino (simulated) / Entertainment |
| **Content rating** | Simulated gambling disclosure required |
| **Contact** | https://masternoder.dk |
| **Privacy policy** | https://masternoder.dk (site privacy page) |

## Screenshots checklist

- [ ] Lobby / featured games grid
- [ ] Crash game in play (multiplier rising)
- [ ] Slots with jackpot meter visible
- [ ] Tournaments panel with countdown
- [ ] Social tab — Discord opt-in + Google Play badge
- [ ] Big-win celebration overlay
- [ ] Phone + tablet form factors (7" and 10")

## Pre-upload ops

1. Build AAB with Bubblewrap (`mobile/casino-twa/README.md`)
2. Copy **Play App Signing** SHA-256 into `static/.well-known/assetlinks.json`
3. Deploy web slice: manifest, assetlinks, casino HTML/JS/CSS
4. Set `DISCORD_CHANNEL_ID_CASINO` webhook URL on server (not in repo)
5. Cron: `cron/discord_casino_fanout.sh` every 15 minutes
6. Internal testing track → closed testing → production

## Deep links (verified in web)

- `https://masternoder.dk/casino/?game=crash` — opens Crash tab
- `https://masternoder.dk/casino/?tab=social` — Social tab
- `https://masternoder.dk/casino/?app=casino-twa&tab=lobby` — TWA start URL
