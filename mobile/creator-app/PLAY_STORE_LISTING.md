# MasterNoder Super Encoder — Play Store Listing

**Package:** `dk.masternoder.creator`  
**Landing page:** https://masternoder.dk/  
**App URL:** https://masternoder.dk/creator/

## Short description
Create music, songs & videos with one-click Super Encode. Rate creators with MN2 crypto.

## Full description
MasterNoder Super Encoder is the mobile music and video creator from masternoder.dk.

- One-click Super Encode: AI lyrics, voice audio, video clips, synchronized mux
- Spotify-style track library (max 125 videos stored)
- Rate tracks with MN2 crypto — creators earn
- Uses your existing MasterNoder wallet on profile
- Specialized AI per task (LLM, ElevenLabs, video providers)

## Build (Windows)

**Prerequisites:** Node 18+, JDK 21 (`winget install EclipseAdoptium.Temurin.21.JDK`), Android SDK.

```powershell
cd mobile/creator-app
npm install
powershell -ExecutionPolicy Bypass -File scripts/setup-android-sdk.ps1   # once
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
npm run build:debug
```

Debug APK: `android\app\build\outputs\apk\debug\app-debug.apk`  
Release: sign `app-release-unsigned.apk` for Play Store upload.
