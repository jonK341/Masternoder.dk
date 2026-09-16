# Google Play listing draft — MasterNoder2 Casino

Package: **`dk.masternoder.casino`** · Shell: **Capacitor** — `mobile/casino-app/`  
Alt shell: [TWA listing](../casino-twa/PLAY_STORE_LISTING.md)

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

## Graphics checklist

- [ ] Hi-res icon 512×512 PNG (`npm run assets` in `mobile/casino-app/`)
- [ ] Feature graphic 1024×500 — `/static/img/casino/banner-masternoder2-casino.png`
- [ ] Phone screenshots (portrait): lobby with banner, crash, social tab
- [ ] 7″ and 10″ tablet screenshots (optional)

---

## Technical checklist

- [ ] Upload AAB from Capacitor (`android/app/build/outputs/...`) **or** Bubblewrap TWA build
- [ ] Play App Signing enabled
- [ ] Copy **SHA-256** via `python scripts/casino_play_assetlinks_update.py "<SHA>"` and deploy `well_known`
- [ ] Verify: `https://masternoder.dk/.well-known/assetlinks.json`
- [ ] Start URL: `https://masternoder.dk/casino/?app=casino-capacitor` or `?app=casino-twa&tab=lobby`
- [ ] Data safety form (account IDs in localStorage, no extra PII in shell)

---

## Policy notes

- Disclose simulated gambling / virtual currency
- Do not market real-money play inside the Play listing if policy requires web-only RMG
- Target countries: match `casino_config.json` geo rules

---

## Internal testing

1. Internal testing track → add testers
2. Confirm Digital Asset Links (`adb shell pm get-app-links dk.masternoder.casino`)
3. Promote to production after crash-free week
