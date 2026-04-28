# Game Walkthroughs & Guides

**Updated:** 2026-02-21  
**Rulebook alignment:** V1–V15

## Overview

The Trophy Hunters game now includes walkthroughs and guides that align with the rulebooks. Play by the rulebook.

## Data Files

- **`data/game_walkthroughs.json`** — Step-by-step walkthrough in 5 phases
- **`data/game_guides.json`** — 7 guides (Getting Started, Spells, Star Map, Comm. Psych, Points, Compendium, Effect Clusters)

## APIs

| Endpoint | Description |
|----------|-------------|
| `GET /api/game/hunters/walkthroughs` | Returns walkthrough phases and steps |
| `GET /api/game/hunters/guides` | Returns guides with rulebook refs |
| `GET /api/game/hunters/aggregator-fulfill` | Returns `walkthroughs_ref` and `guides_ref` |

## Game Page

- **Walkthrough tab** — Loads phases from API, displays step-by-step
- **Guides tab** — Loads guides, links to compendium pages
- **Overview** — "Play by the Rulebook" banner with link to Compendium

## Trophies Page

- Compendium tab links to Walkthrough and Guides on game page

## Walkthrough Phases

1. **Getting Started** (V1) — Profile, user_id, onboarding
2. **Star Map & Verification** (V4) — View star map, run verification, DNA test
3. **Hunters Spells** (V2) — 19 spells, sectors, game_points
4. **Communication Psychology** (V3) — 25 theories, study, compendium
5. **Unified Points & Mastery** (V7) — All point types, compendium V1–V15, agent-context
