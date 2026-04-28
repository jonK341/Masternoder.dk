# Generator Buttons – Two Generators on One Page

## Current Layout

The generator page has **two main generators** in the main content area:

| Generator | Button | Purpose | API Endpoints |
|-----------|--------|---------|---------------|
| **AI Clip Generator** | "Generer Klip med AI" | Creates short AI-generated clips | `/api/ai-clips/generate`, `/api/generator/ai-clips` |
| **Video Generator** | "Generer Video Nu" | Creates full documentaries | `/api/unified/generate-video` |

Plus a third in the Summary tab:
| **Magic Generate** | "Magic Generate (1-click video)" | One-click short documentary | `/api/generator/magic-generate` |

## Recommendation: Keep Both

- **AI Clip Generator**: Short clips (e.g. 10s), single-scene, fast. Good for testing or quick clips.
- **Video Generator**: Full documentaries with multiple segments, themes, content categories, progress UI.

They serve different workflows. Both should be kept.

## Why Buttons May Not Work

1. **404 on API endpoints** – Production routes not registered (python-proxy/uwsgi PYTHONPATH).
2. **Path corrector** – Bad mappings (e.g. `/api/` → `/api/api/`) were breaking requests; now reset.

## Fixes Applied

- Deploy includes `ensure_flask_routes_registered.py` (sets PYTHONPATH, restarts services).
- Path corrector mappings reset to `{}`.
- Register Intelligence + route loader deployed for automatic route registration.
