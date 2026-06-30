# Google Play — Tuesday checklist ($25 developer account)

After the **$25 Google Play developer registration fee** is paid (scheduled **Tuesday**), follow these steps to fix Digital Asset Links and ship the Android TWA/Capacitor shell.

Related: [CASINO_INTEGRATIONS_CHECKLIST.md](CASINO_INTEGRATIONS_CHECKLIST.md) · [mobile/casino-app/PLAY_STORE_LISTING.md](../mobile/casino-app/PLAY_STORE_LISTING.md) · [CASINO_DEPLOY_OPS.md § C.1](CASINO_DEPLOY_OPS.md)

---

## Why assetlinks was broken

Production served a **truncated** SHA (`305253597`) instead of a full **64-character hex** SHA-256 fingerprint. Google Digital Asset Links require the complete App Signing certificate fingerprint for package `dk.masternoder.casino`.

The repo now uses placeholder `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` in `static/.well-known/assetlinks.json` until the real Play App Signing SHA is available.

---

## After Tuesday — get the real SHA

1. **Pay $25** at [Google Play Console](https://play.google.com/console/signup) and complete developer account setup.
2. **Create the app** with package name `dk.masternoder.casino` (must match `assetlinks.json` and Capacitor/TWA config).
3. **Upload first AAB** to an internal testing track (Capacitor: `mobile/casino-app/` or TWA: `mobile/casino-twa/`).
4. In Play Console → **Your app** → **Setup** → **App integrity** → **App signing**:
   - Copy **App signing key certificate** → **SHA-256 certificate fingerprint**
   - Format is either `AA:BB:CC:…` (with colons) or 64 hex chars without colons — both are valid in `assetlinks.json`.
5. **Update the repo** (local):

```powershell
cd C:\Users\jonkh\UsecaseSampler\Masternoder.dk
$sha = "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB"
(Get-Content static\.well-known\assetlinks.json -Raw) `
  -replace 'REPLACE_WITH_PLAY_APP_SIGNING_SHA256', $sha |
  Set-Content static\.well-known\assetlinks.json -NoNewline
```

6. **Deploy well-known files**:

```powershell
python scripts/deploy.py well_known --ask-pass
```

7. **Verify** with [Google Digital Asset Links tester](https://developers.google.com/digital-asset-links/tools/generator):
   - Site: `https://masternoder.dk`
   - Package: `dk.masternoder.casino`
   - Relation: `delegate_permission/common.handle_all_urls`

```bash
curl -sS https://masternoder.dk/.well-known/assetlinks.json | jq .
```

---

## Before Play upload — debug keystore (local TWA testing only)

Until the app is on Play, use your **debug or upload keystore** SHA for **local Trusted Web Activity** testing. This is **not** valid for production Play-verified links.

### Get debug keystore SHA (Windows)

```powershell
keytool -list -v -keystore "$env:USERPROFILE\.android\debug.keystore" -alias androiddebugkey -storepass android -keypass android
```

Look for `SHA256:` under **Certificate fingerprints**. Copy the full value into `assetlinks.json` **only on a dev/staging host** — replace with Play App Signing SHA before public launch.

### Capacitor release keystore

If you built a release keystore for Capacitor:

```powershell
keytool -list -v -keystore path\to\release.keystore -alias your_alias
```

Use **upload key** SHA for pre-Play testing; after Play App Signing is enabled, always use **App signing key** SHA from the console.

---

## Deploy commands summary

| Step | Command |
|------|---------|
| Deploy casino slice (routes, agents, UI) | `python scripts/deploy.py casino --ask-pass` |
| Deploy assetlinks + AASA | `python scripts/deploy.py well_known --ask-pass` |
| Restart uWSGI (if env changed) | `python scripts/deploy_all_and_restart_uwsgi.py` or server `systemctl restart uwsgi-vidgenerator` |

---

## Do not commit real SHAs to public repos

Paste the production Play SHA into `assetlinks.json` on the server or in a private deploy branch. The placeholder in git is intentional until Tuesday.
