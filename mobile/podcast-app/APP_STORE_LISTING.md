# App Store — MasterNoder Podcast

Bundle ID: **`dk.masternoder.podcast`**

## Listing copy (draft)

**Name:** MasterNoder Podcast  
**Subtitle:** Social lounge & provably fair games  
**Promotional text:** Crash, slots, crews, and daily quests — virtual coins on MasterNoder.

**Description:**

> MasterNoder Podcast is the mobile home for the MasterNoder casino lounge. Play crash, plinko, slots, and arcade hits with virtual coins, track quests, and share wins with friends and crews.
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

- [ ] Xcode archive with bundle `dk.masternoder.podcast`
- [ ] **Associated Domains:** `applinks:[REDACTED]`
- [ ] Deploy `static/.well-known/apple-app-site-association` with real **Team ID** (`TEAMID.dk.masternoder.podcast`)
- [ ] Verify AASA: `curl -I https://[REDACTED]/.well-known/apple-app-site-association` (no redirect, `application/json`)
- [ ] URL scheme `masternoder` in Info.plist (Capacitor ios.scheme)
- [ ] Test Universal Link: `https://[REDACTED]/podcast/?game=crash`
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

Replace placeholder `https://apps.apple.com/app/id0000000000` in `casino/manifest.webmanifest` and `GET /api/podcast/mobile/config` once the app is live.
