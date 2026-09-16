# MN2 Wallet — App Store / TestFlight (draft)

Use when publishing `dk.masternoder.wallet` from `mobile/wallet-app/` (Capacitor iOS).

## Store metadata

| Field | Value |
|-------|-------|
| App name | MN2 Wallet |
| Subtitle | MN2 send, receive & monitors |
| Category | Finance |
| Age rating | Complete questionnaire — crypto / virtual assets |
| Privacy policy | Link to site privacy page |

## TestFlight placeholder

Until App Store review:

1. Archive in Xcode → **Distribute App** → **TestFlight**
2. Add internal testers (team Apple IDs)
3. Document TestFlight public link in `docs/WALLET_DOWNLOAD.md` when available

## PWA fallback (no TestFlight)

iPhone users can **Add to Home Screen** from Safari on `/wallets` — see [iOS section in WALLET_DOWNLOAD.md](../../docs/WALLET_DOWNLOAD.md#ios).

## Associated Domains

- `applinks:[REDACTED]` — deploy `static/.well-known/apple-app-site-association` with wallet paths under `/wallets/*`
- Replace `TEAMID` in AASA with Apple Developer Team ID

## URL scheme

- `masternoder://wallet?tab=send` — handled by `@capacitor/app` + `wallet-mobile.js`
