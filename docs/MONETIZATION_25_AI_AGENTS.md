# Monetization 25 — update and upgrade with AI and agents

The **25 monetization levers** are installed as agent skills (e.g. `master_fix_agent_top25_01_conversion_orchestration` through `top25_25_scale_readiness`). This upgrade hooks them to a **new way to make money** by wiring AI and agents into a single system.

## What’s installed

- **25 levers** in `data/monetization_levers.json`: conversion orchestration, offer architecture, pricing intelligence, bundle engineering, checkout optimization, cart reactivation, cross-sell matrix, upsell sequence, retention automation, lifecycle revenue, segment personalization, creative performance, landing page velocity, CTA precision, social proof systems, trust signal stack, paywall refinement, subscription uplift, profit margin guard, refund risk control, funnel diagnostics, KPI forecasting, sales copy adaptation, campaign compounding, scale readiness.
- Each lever has:
  - **category**: conversion, offers, pricing, retention, creative, trust, analytics, scale
  - **suggested_agents**: which of `content_generator_agent`, `learning_agent`, `analytics_agent` are best suited
  - **shop_category_hook**: optional shop category to drive revenue (e.g. premium, currency, boosts)
  - **revenue_hook**: paypal, shop, subscription, or data

## How AI and agents are hooked to make money

1. **AI recommendations**  
   `GET /api/monetization/ai-recommendations?user_id=`  
   The LLM gets the user’s level, game_points, battle_points, coins and returns **which of the 25 levers** to focus on to increase revenue (for that user). Used on profile and anywhere you want “AI says: focus on these levers”.

2. **Assign an agent to a lever**  
   `POST /api/monetization/levers/<lever_id>/assign-agent`  
   Body: `{ "user_id", "agent_id" }` with `agent_id` one of `content_generator_agent`, `learning_agent`, `analytics_agent`.  
   Assignments are stored in `data/monetization_agent_assignments.json`. Agents can then be used to “work on” that lever (e.g. content for offers, analytics for pricing, learning for retention).

3. **List levers and assignments**  
   `GET /api/monetization/levers?user_id=`  
   Returns all 25 levers plus, per lever, `assigned_agent` for that user (if any). Lets the UI show “Lever X — assigned: Content Generator”.

4. **Upgrade summary**  
   `GET /api/monetization/upgrade`  
   Returns description, lever count, `revenue_hooks`, `agent_roles`, and the main monetization API endpoints.

## Revenue hooks (how the 25 levers make money)

- **paypal** — Direct real-money conversion (checkout, coin packs, premium).
- **shop** — In-app shop (coins, points, items, bundles, cosmetics).
- **subscription** — Recurring or subscription-style revenue.
- **data** — Funnel/KPI insights that inform where to push paywall/shop.

Levers are linked to shop categories via `shop_category_hook` so that “assign agent to lever” can later drive:
- Promoted shop categories or items.
- AI-generated copy/offers for that lever.
- Analytics on which levers drive the most revenue.

## Profile and generator

- **Profile**  
  “Monetization 25” card: shows AI recommendations (top levers + short reasoning), dropdown to pick a lever and an agent, “Assign” to call the assign API, and link to “Upgrade summary (API)”.

- **Generator**  
  Can call the same APIs (levers, ai-recommendations, assign-agent) to show recommendations and assign agents from the generator flow.

## Files

| File | Purpose |
|------|--------|
| `data/monetization_levers.json` | 25 levers with domain, name, category, suggested_agents, shop_category_hook, revenue_hook |
| `data/monetization_agent_assignments.json` | Per-user assignments: `user_id -> lever_id -> agent_id` |
| `backend/services/monetization_levers_service.py` | load_levers, assign_agent_to_lever, get_ai_recommendations |
| `backend/routes/missing_endpoints_routes.py` | Routes: levers, ai-recommendations, levers/<id>/assign-agent, upgrade |
| `docs/MONETIZATION_25_AI_AGENTS.md` | This document |

## Existing monetization endpoints (unchanged)

- `GET /api/monetization/top50` — Leaderboard (e.g. top 50 by XP/cash).
- `GET /api/monetization/top-6` — Top 6 for the monetization frame.
- `GET /api/monetization/cash` — User cash / monetization points.

The 25 levers and AI/agent hooks **add** a new layer on top: they guide **which** monetization levers to use and **which agents** to assign so the platform can make money in a structured, AI-driven way.
