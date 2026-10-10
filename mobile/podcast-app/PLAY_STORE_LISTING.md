# Google Play listing draft — MasterNoder Podcast

Package: **`dk.masternoder.podcast`** · Shell: **Capacitor** — `mobile/podcast-app/`  
Alt shell: [TWA listing](../podcast-twa/PLAY_STORE_LISTING.md)

---

## Store listing

| Field | Draft |
|-------|-------|
| **Title** | MasterNoder Podcast |
| **Short description** | AI podcast episodes, Super Encoder audio, and Create App distribution. |
| **Tagline** | Listen. Create. Ship. |
| **Full description** | MasterNoder Podcast — AI-generated episodes, premium audio encode profiles (Super Encoder nr. 1), and Create App integration for Play Store + podcast distribution. |
| **Category** | Music & Audio / Entertainment |
| **Contact** | Site support page |
| **Privacy policy** | Site privacy page |

---

## Technical checklist

- [ ] Upload AAB from Capacitor (`android/app/build/outputs/...`) **or** Bubblewrap TWA build
- [ ] Play App Signing enabled
- [ ] Digital Asset Links for `dk.masternoder.podcast`
- [ ] Start URL: `/podcast/?app=podcast-capacitor&tab=episodes`

---

## Internal testing

1. Internal testing track → add testers
2. Confirm Digital Asset Links (`adb shell pm get-app-links dk.masternoder.podcast`)
3. Promote to open testing after crash-free week
