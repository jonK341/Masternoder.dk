# App Store — MasterNoder Casino Social

Bundle ID: **`dk.masternoder.casino`**

## Listing copy (draft)

**Name:** MasterNoder Casino Social  
**Subtitle:** Social lounge & provably fair games  
**Promotional text:** Crash, slots, crews, and daily quests — virtual coins on MasterNoder.

**Description:**

> MasterNoder Casino Social is the mobile home for the MasterNoder casino lounge. Play crash, plinko, slots, and arcade hits with virtual coins, track quests, and share wins with friends and crews.
>
> Features:
> • Provably fair crash and instant games  
> • Leaderboards, tournaments, daily wheel  
> • Social tab with crews and share cards  
> • Universal links to specific games  
>
> Uses the same MasterNoder account as the website. Real-money options, where permitted, are handled on the web with verification.

**Category:** Games  
**Age rating:** 17+ (Frequent/Intense Simulated Gambling) — verify with App Store Connect questionnaire.

## Graphics checklist

- [ ] App icon 1024×1024 (no alpha) — `npm run assets` in `mobile/casino-app/`
- [ ] Screenshots 6.7″ and 6.5″ iPhone (portrait)
- [ ] Optional iPad screenshots

## Technical checklist

- [ ] Xcode archive with bundle `dk.masternoder.casino`
- [ ] **Associated Domains:** `applinks:masternoder.dk`
- [ ] Deploy `static/.well-known/apple-app-site-association` with real **Team ID** (`TEAMID.dk.masternoder.casino`)
- [ ] Verify AASA: `curl -I https://masternoder.dk/.well-known/apple-app-site-association` (no redirect, `application/json`)
- [ ] URL scheme `masternoder` in Info.plist (Capacitor ios.scheme)
- [ ] Test Universal Link: `https://masternoder.dk/casino/?game=crash`
- [ ] Test custom scheme: `masternoder://casino?game=crash`
- [ ] Privacy nutrition labels — account identifier, usage data as applicable

## App Store Connect

- [ ] Create app record → link bundle ID
- [ ] Upload build from Xcode Organizer or Transporter
- [ ] Export compliance: no encryption beyond HTTPS → exempt
- [ ] Review notes: login uses existing site session / `game_user_id` in localStorage; demo account instructions if needed

## Ops vs code

| Item | Owner |
|------|--------|
| Team ID in AASA | Ops / Apple Developer |
| App Store URL in manifest & API | Ops after app approval |
| Screenshots & copy | Product |
| Capacitor project & deep links | Code (this repo) |

Replace placeholder `https://apps.apple.com/app/id0000000000` in `casino/manifest.webmanifest` and `GET /api/casino/mobile/config` once the app is live.
