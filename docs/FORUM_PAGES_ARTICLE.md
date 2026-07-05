# MasterNoder Forum — complete pages article

**Published:** 2026-07-05  
**Hub URL:** `/forum/`

This document describes every portal page and how community, documentation, and rulebook features were unified under the Forum.

---

## Why one Forum?

Previously, news, chat, podcast, compendium, rights-law paragraphs, achievement guides, and agent support were scattered across separate portal pages with duplicate navigation and podcast portal strips. The **Forum** (`/forum/`) consolidates them into one user-friendly hub with tabs.

### Redirected into Forum

| Old URL | Forum tab |
|---------|-----------|
| `/news/` | `#news` |
| `/chat/` | `#chat` |
| `/podcast/` | `#podcast` |
| `/compendium/` (index only) | `#rulebooks` |
| `/rights-law/` | `#paragraphs` |
| `/time-achievement-guides/` | `#docs` |
| `/agent_support/` | `#support` |

Deep compendium links (`/compendium/rulebook-v9`, `/compendium/page-3.html`) still work.

---

## Forum tabs

| Tab | Features |
|-----|----------|
| **Home** | Mixed feed of articles + news |
| **News** | `GET /api/forum/news` — platform announcements |
| **Articles** | User-written posts via `POST /api/forum/articles` |
| **Chat** | Social room + AI assistant |
| **Podcast** | Channels & episodes; full player at `/podcast/` legacy files |
| **Rulebooks** | Index of V1–V16; links to compendium reader |
| **Paragraphs** | Rights & citation reference (§1–§4) |
| **Docs** | Curated guides linking to game, lab, compendium |
| **Support** | Agent Support + FAQ |
| **Social** | Share to Discord, Facebook, Instagram, Snapchat, X, LinkedIn, WhatsApp |
| **Wikipedia** | `GET /api/forum/wikipedia?title=` — REST summary proxy |

---

## Writing rules

Loaded from `data/forum_rules.json` via `GET /api/forum/rules`:

1. Be respectful — no harassment or hate speech  
2. Original articles with attribution  
3. Mark spoilers and NSFW content  
4. No guaranteed crypto returns  
5. Moderation may hide posts or ban repeat offenders  
6. Paragraphs tab is reference, not legal advice  

---

## Remaining portal pages (not in Forum)

### Create
- `/generator/` — AI video generator  
- `/gallery/` — video library  
- `/editor/` — content tools  

### Play
- `/game/` — Hunters, walkthroughs, guides  
- `/battle/`, `/casino/`, `/battlegrounds/`  

### Account & economy
- `/profile/`, `/shop/`, `/trophies/`, `/exchange/`, `/market/`  

### Platform tools
- `/lab/`, `/debugger/`, `/aggregator/`, `/explorer/`, `/command-center/`  

### Social (friends/guilds)
- `/social/` — friends, crews, challenges (distinct from Forum social *share* tab)  

---

## API reference

```
GET  /api/forum/overview
GET  /api/forum/feed
GET  /api/forum/news
GET  /api/forum/articles
POST /api/forum/articles
GET  /api/forum/articles/<id>
GET  /api/forum/rules
GET  /api/forum/paragraphs
GET  /api/forum/docs
GET  /api/forum/rulebooks/index
GET  /api/forum/social-networks
POST /api/forum/share
GET  /api/forum/wikipedia?title=
```

---

## Social media integrations

| Network | Integration |
|---------|-------------|
| Discord | Share + `/api/discord/link` |
| Facebook | Sharer URL + OAuth `/api/auth/facebook/start` |
| Instagram | Share link (profile/post) |
| Snapchat | Scan attachment URL template |
| X, LinkedIn, WhatsApp | From `data/social_networks.json` |
| Wikipedia | REST API v1 summary proxy |

---

## Navigation change

The main toolbar now shows **Forum** instead of separate News, Podcast, Library, Chat, and Agent Support links.

See also: `docs/SITE_STRUCTURE.md`
