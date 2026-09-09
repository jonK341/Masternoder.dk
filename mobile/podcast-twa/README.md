# MasterNoder Podcast — Trusted Web Activity (TWA)

Google Play shell for the MasterNoder Podcast PWA. Pairs with **Create App** (`/create-app/`) and **Super Encoder nr. 1** (E1 hardware + AI audio profiles).

## Package

- **Package ID:** `dk.masternoder.podcast`
- **Start URL:** `/podcast/?app=podcast-twa`
- **Web manifest:** `/podcast/manifest.webmanifest`

## Build (Bubblewrap)

1. Install [Bubblewrap CLI](https://github.com/GoogleChromeLabs/bubblewrap).
2. From this directory: `bubblewrap init --manifest=https://YOUR_HOST/podcast/manifest.webmanifest`
3. Or merge `twa-manifest.json` with your signing key.
4. `bubblewrap build` → upload AAB to Play Console **Internal testing**.

## Play Store checklist

See `PLAY_STORE_LISTING.md`. Link **Digital Asset Links** SHA-256 after first signed build.

## Related

- Create App wizard: `/create-app/`
- Podcast hub: `/podcast/`
- Casino TWA (sibling app): `../casino-twa/`
- Lab seed project: `data/lab_projects_seed.json` → `lseed_create_app_super_encoder`
