# Google Play — MasterNoder Casino Social

Package: **`dk.masternoder.casino`**

## Listing copy (draft)

**Title:** MasterNoder Casino Social  
**Short description:** Social casino lounge — virtual coins, crews, crash & slots.  
**Full description:**

> Play crash, slots, plinko, mines, and more in the MasterNoder social casino lounge. Earn quests, climb leaderboards, join crews, and share big wins — virtual coins first.
>
> • Provably fair crash and instant games  
> • Daily wheel, tournaments, and hall of fame  
> • Friends, crews, and social feed  
> • Same account as masternoder.dk  
>
> Real-money MN2/USD stakes are available on the website with age and region checks. This app focuses on the social virtual-coin experience.

**Category:** Game → Casino  
**Content rating:** Simulated gambling — complete IARC questionnaire honestly.

## Graphics checklist

- [ ] Hi-res icon 512×512 PNG (run `npm run assets` in `mobile/casino-app/`)
- [ ] Feature graphic 1024×500
- [ ] Phone screenshots (portrait): lobby, crash, social tab
- [ ] 7″ and 10″ tablet screenshots (optional)

## Technical checklist

- [ ] Upload AAB from Capacitor (`android/app/build/outputs/...`) **or** Bubblewrap TWA build
- [ ] Play App Signing enabled
- [ ] Copy **SHA-256** cert fingerprint into `static/.well-known/assetlinks.json` and deploy
- [ ] Verify: `https://masternoder.dk/.well-known/assetlinks.json`
- [ ] Start URL resolves: `https://masternoder.dk/casino/?app=casino-twa&tab=lobby` (TWA) or `?app=casino-capacitor` (Capacitor)
- [ ] Privacy policy URL on masternoder.dk
- [ ] Data safety form (account IDs in localStorage, no extra PII in shell)

## Policy notes

- Disclose simulated gambling / virtual currency
- Do not market real-money play inside the Play listing if policy requires web-only RMG
- Target countries: match `casino_config.json` geo rules

## Internal testing

1. Internal testing track → add testers
2. Confirm Digital Asset Links (`adb shell pm get-app-links dk.masternoder.casino`)
3. Promote to production after crash-free week
