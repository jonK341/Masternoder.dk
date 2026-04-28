# Star Map 25 — AIs that can improve gameplay

**Purpose:** Audit of existing AIs in the codebase that can enhance Star Map 25 (investigation, levels, buildup, daily reset, invasion). Each item is a concrete improvement.

---

## 1. Game AI Coach (`/api/game/ai-coach`)

**Current:** Uses `llm_service.chat()` with level, XP, and generic "systems" (point counters). Does not include Star Map 25.

**Improvement:** Add Star Map 25 context to the coach prompt:
- `investigated_count` (X/25), `total_points_earned`, `system_levels` summary (e.g. "3 systems at max level"), `pending_points`, `in_daily_reset_bonus_window`.
- System prompt: mention "Star Map 25: investigate systems, build structures, level up 1–5 per system, collect buildup; daily reset at midnight UTC gives 2× on high-level structures for 12h."

**Result:** Coach can give tips like "Collect your buildup now—you're in the 2× bonus window" or "Level Mars to 3 to unlock Forge Shrine."

**Status:** Implemented (context + system prompt in `game_ai_coach` in `missing_endpoints_routes.py`).

---

## 2. Star Map 25–specific AI hint endpoint

**Current:** No dedicated AI for starmap25 tactics.

**Improvement:** New endpoint `GET/POST /api/star-map/25/ai-hint?user_id=` that:
- Fetches user's status (investigated, levels, buildup, next_daily_reset, in_bonus_window).
- Calls `llm_service.complete()` or `chat()` with a short prompt: "Given this Star Map 25 state, give 2–3 specific tactical tips (one sentence each): e.g. which system to level next, when to collect, which building to build."
- Returns `{ "success", "hints": ["…", "…"], "provider" }`.

**Result:** Game tab and Star Map 25 monitor can show an "AI tips" box that updates with contextual advice.

**Status:** Implemented: `GET/POST /api/star-map/25/ai-hint` in `star_map_routes.py`; Game tab Star Map 25 section shows "AI tips" and fetches hints in `loadStarMap25Tab()`.

---

## 3. Invasion blurb (when you add POST /invade)

**Current:** Design doc mentions optional "AI-generated invasion blurb" per invasion. Not yet implemented.

**Improvement:** When `POST /api/star-map/25/invade` is called, optionally call a small LLM prompt: "In one short sentence (max 20 words), describe the invasion of [point_name] by [unit_name]." Store in user's invasion blurbs. Use `video_ai_bridge.complete_for_stage('speed', …)` or `llm_service.complete()`.

**Result:** Each invasion gets a unique one-liner (e.g. "The 3rd Fleet secured Hydraphur after a brutal void battle.").

---

## 4. Lore expansion (content_generator_agent)

**Current:** `star_map_25.json` has `lore` per point; optional `lore_long` in 50-projects list.

**Improvement:** Use `video_generator_service._ai_generate_enhanced_descriptions()` or `llm_service.complete()` in a batch or on-demand job to generate 2–4 sentence `lore_long` for each of the 25 points. Store in data or per-user. Assign "expand lore for point X" to content_generator_agent via the 50 projects / calendar.

**Result:** "Read more" on the monitor shows AI-expanded lore.

---

## 5. Agent AI Intelligence (strategy / prediction)

**Current:** `agent_ai_intelligence.develop_strategy()`, `predict_outcome()`, `make_decision()` take generic context. No starmap25-specific context.

**Improvement:** When developing strategy for "content_agent" or "learning_agent", inject starmap25 context (e.g. `starmap25_investigated`, `starmap25_levels`, `starmap25_pending`) into `context`. Optionally add a strategy type `starmap25_buildup` so the agent can suggest "build Barracks on Mars next" or "deploy Fleet to Hydraphur."

**Result:** Assigned agents' strategies can consider Star Map 25 state.

---

## 6. Shop AI recommendations

**Current:** Shop recommendations use LLM with user profile; may not weight starmap25.

**Improvement:** Include in the recommendation context: `starmap25_investigated_count`, `starmap25_systems_at_max_level`, `starmap25_has_pending_collect`. So the model can suggest "Level Skip Token" or "Daily Reset Bonus" when relevant.

**Result:** Shop can recommend Star Map 25 items when the user is actively building.

---

## 7. Generator AI ideas

**Current:** `_ai_generate_prompt_ideas(topic)` used for video prompt ideas.

**Improvement:** Expose or reuse for "lore ideas" with `topic` like "Warhammer 40K Terra" or "Star Map 25 Mars" to get 3–5 short lore expansion sentences. Could be used by content_generator_agent for the 50-project task "Extended lore paragraphs."

**Result:** AI-generated lore ideas for starmap25 points.

---

## Summary

| AI / component           | Improvement                                      | Impact                          |
|--------------------------|--------------------------------------------------|---------------------------------|
| Game AI Coach            | Add starmap25 context to prompt                  | High — one place for all tips   |
| New: starmap25 AI hint   | Dedicated endpoint for 2–3 tactical hints       | High — UI can show in Game tab |
| Invasion blurb           | LLM one-liner on invade                         | Medium — when invade exists     |
| Lore expansion           | AI-generated lore_long per point                | Medium — content depth          |
| Agent AI Intelligence    | Inject starmap25 into strategy context          | Medium — agent coherence        |
| Shop recommendations     | Include starmap25 in recommendation context     | Low–medium — better offers     |
| Generator AI ideas       | Lore ideas for starmap25 topics                 | Low — content pipeline         |

Implementing **Game AI Coach** (starmap25 context) and **Star Map 25 AI hint** endpoint gives the largest gameplay improvement with minimal new surface area.
