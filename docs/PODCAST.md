# MasterNoder Podcast

Podcast hub at `/podcast` — channels, AI generation, crypto rewards, social comments, **verified sound**, and **Blue Bubble Cheese Gum (BBCG)** extended visuals.

## Features

| Area | API / UI |
|------|----------|
| Channels | `GET /api/podcast/channels` |
| Episodes + play | `GET /api/podcast/episodes`, `POST .../play` |
| **Sound stream** | `GET /api/podcast/episodes/<id>/audio` (TTS/tone fallback) |
| **Sound check** | `GET/POST /api/podcast/sound-check` |
| News & comments | `GET /api/podcast/news`, `POST /api/podcast/news/<id>/comments` |
| Social | likes, follows, episode comments, activity feed |
| AI generate | `POST /api/podcast/generate` + encoder profiles |
| Portal max | `GET /api/podcast/portal-lines?site=<id>` + `podcast-portal-lines.js` on 20+ pages |

## Blue Bubble Cheese Gum (BBCG)

Visual identity: bubbly blue gradients (`#4fc3f7`), cheese-gold accents (`#ffd54f`), floating bubble background, extended player stage with canvas visualizer, glossy rounded cards.

## Sound pipeline

1. Episode configured `audio_url` under `static/audio/podcast/`
2. On miss → TTS + encode via `podcast_encode_service`
3. Fallback → FFmpeg tone WAV→MP3 via `podcast_audio_service`
4. Frontend always uses `audio_play_url` (`/api/podcast/episodes/<id>/audio`)

Run repair: `POST /api/podcast/sound-check?repair=1`

Deep diagnostics: `GET /api/podcast/sound-lab`

## 10 podcast expansions (v2)

| # | Expansion | API / UI |
|---|-----------|----------|
| 1 | **Sound Lab** | `GET /api/podcast/sound-lab` — per-episode format, bytes, status |
| 2 | **BBCG flavor synth** | Multi-tone repair audio in `podcast_audio_service` |
| 3 | **Playback speed** | 0.75×–2× on player |
| 4 | **Episode queue** | Local queue + auto-play next |
| 5 | **RSS syndication** | `GET /api/podcast/rss.xml` |
| 6 | **Transcripts** | `GET /api/podcast/episodes/<id>/transcript` |
| 7 | **Chapter markers** | `GET /api/podcast/episodes/<id>/chapters` — skip navigation |
| 8 | **Leaderboard** | `GET /api/podcast/leaderboard` — comments, news, likes |
| 9 | **Bubble visualizer** | Toggle bar vs bubble BBCG canvas mode |
| 10 | **Visualizer fix** | Single MediaElementSource — no reconnect crash |

## Portal integration

Add to any page:

```html
<link rel="stylesheet" href="/static/css/podcast-portal-strip.css">
<script src="/static/js/podcast-portal-lines.js" data-site="generator"></script>
```

Site lines: `data/podcast_portal_lines.json` (20+ surfaces).

## Google Play Store app — **saved for later**

> **Status: deferred** — do not implement until explicitly scheduled. Tracked in `data/todos/todos.json` id `a1b2c3d4-e5f6-7890-abcd-ef1234567890`.

When resumed:

1. **Shell:** TWA or Capacitor wrapper → `masternoder.dk` with offline podcast cache
2. **Core tabs:** Podcast (background audio), Generator, Game, MN2 wallet, Social
3. **Play Console:** privacy policy, content rating, signed AAB, internal → production track
4. **Mobile parity:** push (episode/news drops), deep links `/podcast#news`, Google OAuth
5. **Compliance:** MN2 / shop flows vs Play billing policy — document before listing

See also: `docs/PLATFORM_TODO.md` (pointer only — details live here).

## Config

- `data/mn2_config.json` → `podcast` (earn rates including `earn_on_news_comment_mn2`)
- `data/podcast_channels.json`, `podcast_episodes.json`, `podcast_portal_lines.json`

## Tests

```bash
python -m pytest tests/unit/test_podcast.py tests/unit/test_podcast_routes.py -q
```
