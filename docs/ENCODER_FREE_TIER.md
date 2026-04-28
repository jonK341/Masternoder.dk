# Gratis AI-lyd og encoder (Free Tier)

Sådan kører du encoderen på masternoder.dk uden faste månedlige omkostninger ved at bruge open source og generøse free tiers.

## 1. Text-to-Speech (TTS)

**Prioritet i koden:** Piper (gratis, lokalt) → ElevenLabs (hvis API-nøgle) → gTTS → pyttsx3.

### Piper TTS (anbefalet – gratis, lokalt)

- Ingen API-nøgle, ingen begrænsninger.
- Installer: `pip install piper-tts`
- Download en stemme (f.eks. engelsk):  
  `python -m piper.download_voices en_US-lessac-medium`
- Sæt model-sti:
  - **Miljøvariabel:** `PIPER_MODEL_PATH=/sti/til/en_US-lessac-medium.onnx`
  - **Eller:** læg `.onnx` + `.onnx.json` i `piper_voices/` i projektroden (fx `piper_voices/en_US-lessac-medium.onnx`).

### ElevenLabs (valgfri)

- Free tier: 10.000 tegn/måned.
- Sæt `ELEVENLABS_API_KEY` i `.env` – bruges automatisk før gTTS hvis du har Piper eller ElevenLabs.

### gTTS (fallback)

- Allerede i brug; ingen konfiguration. Bruges hvis Piper ikke er konfigureret og ElevenLabs ikke er sat.

---

## 2. Lydforbedring og støjreduktion

### DeepFilterNet (valgfri)

- Open source AI-støjreduktion.
- Aktiver: `AUDIO_ENHANCE=1` eller `AUDIO_ENHANCE_NOISE=1`
- Installer: `pip install deepfilternet soundfile`
- Bruges på TTS-narrationen før den blandes ind i videoen.

### FFmpeg loudnorm (valgfri)

- Normalisering (EBU R128) og dynaudnorm-fallback.
- Aktiver: `AUDIO_ENHANCE=1` eller `AUDIO_ENHANCE_LOUDNORM=1`
- Kræver kun at `ffmpeg` er på PATH (ingen ekstra pip-pakker).

---

## 3. Encoding og mastering

- **FFmpeg** bruges allerede via MoviePy (pix_fmt, movflags, audio codec).
- **Loudnorm** kan slås til via `AUDIO_ENHANCE_LOUDNORM=1` (se ovenfor).
- **Matchering** (reference-baseret mastering) er ikke integreret endnu; kan tilføjes senere som ekstra script.

---

## Anbefalet gratis setup

| Komponent   | Valg              | Konfiguration                                      |
|------------|-------------------|----------------------------------------------------|
| TTS        | Piper             | `pip install piper-tts`, download stemme, `PIPER_MODEL_PATH` eller `piper_voices/` |
| Rensning   | DeepFilterNet     | `pip install deepfilternet soundfile`, `AUDIO_ENHANCE_NOISE=1` |
| Mastering  | FFmpeg loudnorm   | `AUDIO_ENHANCE_LOUDNORM=1` (ffmpeg på PATH)        |

---

## Pipeline og production

- **Pipeline:** De nye TTS (Piper først, så ElevenLabs/gTTS) og audio enhancement er **allerede i pipeline**:  
  `tts_service.generate_speech()` prøver Piper først; `video_generator_service` kalder `enhance_audio(narration_path)` på narration før mix.
- **Production / apply:** For at have dem aktiv på serveren:
  1. **Deploy koden:**  
     `python scripts/deploy.py tts`  
     (uploader tts_service, audio_enhancement_service, video_generator_service, system_overview, ai_providers, debugger, docs)
  2. **Sæt miljø på serveren (valgfrit):**
     - **Piper:** `PIPER_MODEL_PATH=/sti/til/en_US-lessac-medium.onnx` eller læg `.onnx` + `.onnx.json` i `piper_voices/` på serveren; installér `pip install piper-tts`.
     - **Lydforbedring:** `AUDIO_ENHANCE=1` eller `AUDIO_ENHANCE_NOISE=1` / `AUDIO_ENHANCE_LOUDNORM=1`.
  3. **Kør apply efter deploy:**  
     `python scripts/apply_updates.py`  
     (rydder cache, genstarter uwsgi/python-proxy/nginx så ny kode loades).

Uden Piper-model eller AUDIO_ENHANCE bruger pipeline stadig gTTS og uden lydforbedring; med env/pakker aktiveres de nye løsninger.

---

## Filer

- **TTS:** `backend/services/tts_service.py` – Piper, ElevenLabs, gTTS, pyttsx3.
- **Lydforbedring:** `backend/services/audio_enhancement_service.py` – DeepFilterNet + FFmpeg loudnorm.
- **Pipeline:** `backend/services/video_generator_service.py` – kalder TTS og (valgfrit) `enhance_audio()` på narration.

## Systemoversigt og debugger

Begge systemer er integreret i:
- **GET /api/system/overview** og **GET /vidgenerator/api/system/overview** – `tts` og `audio_enhancement` + health `tts_ready` / `audio_enhancement_ready`.
- **GET /api/ai/video-providers** – TTS (Piper / ElevenLabs / gTTS) og Audio Enhancement som separate providers med `detail`.
- **Mission Control / debugger** (`/vidgenerator/debugger/`) – TTS-kort viser Piper, ElevenLabs, gTTS, pyttsx3; nyt kort viser Audio Enhancement (DeepFilterNet, FFmpeg loudnorm).
