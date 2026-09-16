# MN2 Wallet — Google Play listing (draft)

Use when publishing `dk.masternoder.wallet` from `mobile/wallet-app/` or `mobile/wallet-twa/`.

## Store metadata

| Field | Value |
|-------|-------|
| App name | MN2 Wallet |
| Short description | Send, receive, and monitor MN2 — trophies, staking, and network stats in one app. |
| Full description | MasterNoder MN2 Wallet v2 — custodial wallet with send/receive, trophy gallery, 4D/5D monitors, peer health, and staking snapshot. Requires a MasterNoder account; same balances as the web wallet at /wallets. |
| Category | Finance |
| Content rating | Complete questionnaire — disclose crypto / virtual asset handling |
| Privacy policy | Link to site privacy page |

## Assets checklist

- [ ] Hi-res icon 512×512 (from `resources/icon.svg` via `npm run assets`)
- [ ] Feature graphic 1024×500
- [ ] Phone screenshots (Overview, Send, Receive, 4D Monitor)
- [ ] Signed AAB or APK from release build

## Package

- **Application ID:** `dk.masternoder.wallet`
- **Version:** `0.1.0-preview` (versionCode 1)

## Digital Asset Links

Add Play App Signing SHA256 to `static/.well-known/assetlinks.json` for package `dk.masternoder.wallet`, then deploy `wallet_mobile` manifest.

## Internal testing

1. Upload AAB to Internal testing track
2. Add tester emails
3. Share opt-in link alongside GitHub Release APK for sideload testers
