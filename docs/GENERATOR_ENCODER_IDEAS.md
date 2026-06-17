# Generator — Encoder Ideas

**Purpose:** Backlog of encoding pipeline upgrades beyond Phase 1–2 UI work.  
**Last updated:** 2026-06-17  
**Pipeline:** `backend/services/video_generator_service.py` · MoviePy · optional AI video providers

---

## Shipped encoders (today)

| Mode | Profile | Output | When |
|------|---------|--------|------|
| Rich segments | `fast_ai` / default | 854×480 or 1280×768 MP4 | Documentary default |
| Animated segment | Ken Burns + particles + text overlay | Per-segment clip | When image_path set |
| AI video segment | ModelsLab / Runway / Pika / HeyGen / Replicate | Injected clip | When provider configured |
| Fallback | ColorClip + text overlay | Single MP4 | LLM/plan failure |
| Sample copy | File copy | MP4 | MoviePy unavailable |

---

## Priority encoder ideas (implement next)

| # | Idea | Benefit | Effort |
|---|------|---------|--------|
| E1 | **Hardware encode profile** — detect NVENC/QSV via ffmpeg, `-c_name` path for concat step | 3–5× faster on GPU hosts | Medium | ✅ Done |
| E2 | **Two-pass quality ladder** — draft 480p preview in &lt;30s, optional 1080p upsell (MN2 ultra) | Faster perceived completion | Medium |
| E3 | **Segment parallel encode** — encode segments to temp MP4s in thread pool, concat at end | Better CPU use on multi-core | High |
| E4 | **Audio bed mixer** — royalty-free bed per `audio_style` (cinematic, documentary, energetic) | Richer output without TTS cost | Low | ✅ Done |
| E5 | **TTS narration track** — Groq/Gemini TTS or edge-tts per segment description | True documentary voiceover | Medium | ✅ Done |
| E6 | **Thumbnail sprite** — extract 3 frames → WebP poster for gallery cards | Gallery looks alive | Low | ✅ Done |
| E7 | **WebM/VP9 export** — optional second artifact for web embed (smaller than H.264) | Bandwidth savings | Low |
| E8 | **CRF presets table** — `fast_ai=28`, `premium=23`, `ultra=18` mapped to encode_profile | Predictable quality tiers | Low | ✅ Done |
| E9 | **Progressive sidecar stages** — write `planning` → `enhancing` → `segment_N` → `concat` → `mux` | Finer UI progress | Low | ✅ Done |
| E10 | **Stale job reaper** — kill subprocess older than duration×3 + mark failed | Fewer zombie encodes | Low | ✅ Done |
| E11 | **Watermark tier** — free = small MN2 watermark; paid MN2 = clean export | Monetization | Low |
| E12 | **Chapter markers** — export `chapters.json` from segment titles for gallery/editing | Re-use in players | Low |
| E13 | **Batch clip pack** — one job → N aspect ratios (16:9, 9:16, 1:1) from same plan | Social export | High |
| E14 | **AI B-roll injection** — Pollinations/Stability image per segment when no video AI | Visual variety | Medium |
| E15 | **Cold-start cache** — reuse last successful segment palette/fonts for user_id | Consistent brand clips | Medium |

---

## Crypto reward tie-ins (encoder × MN2)

| Trigger | MN2 bonus | Notes |
|---------|-----------|-------|
| Finish any video | Base `earn_on_finish_mn2` | Already live |
| Multi-AI (2+ providers) | +0.001 MN2 per extra provider (cap 0.005) | **Shipped** |
| First video of UTC day | +0.01 MN2 | **Shipped** |
| Staking | +0.5% earn per 1000 MN2 staked (cap 15%) | **Shipped** |
| Ultra encode complete | +0.01 MN2 (future) | Tie to E2 1080p tier |
| Share to Discord showcase | +0.002 MN2 (future) | M8 #59 engagement |

Config: `data/mn2_config.json` → `generator.crypto_rewards`.

---

## Recommended build order

1. ~~**E9 + E6** — better progress + gallery thumbnails (quick wins)~~ ✅ Shipped 2026-06-17
2. ~~**E4 + E8** — audio bed + CRF presets (quality tiers without new providers)~~ ✅ Shipped 2026-06-17
3. ~~**E1 or E3** — performance (pick based on server: GPU vs CPU-only)~~ E1 ✅ · E3 pending
4. ~~**E5** — narration (biggest UX jump for documentary mode)~~ ✅ Shipped 2026-06-17
5. **E2** — two-pass preview ladder · **E12** — chapter markers (quick wins)
