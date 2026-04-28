# Hunters & platform rulebook (canonical summary)

This document is the **short canon** for rules that also surface in the Battle page **Rulebooks** tab and in Profile. Long-form narrative lives in Compendium HTML (`/compendium/…`) and Hunters rulebook pages.

## Identity and progress

- **One active profile per browser** via `game_user_id` (see Profile → Account). Shop purchases, unified points, trophies, and lab agent runs all attribute to this ID.
- **Unified points** are stored in `logs/unified_points/<user_id>.json` and merged with database snapshots on read so the UI shows a single consistent total.

## Fair play

- Do not manipulate client-side counters to claim rewards; the server records purchases and point changes.
- Switching user ID in Profile starts a separate progress line for that ID.

## Battle (competitive)

- Rankings and battle points feed the same unified system as Hunter Game and Shop where applicable.
- Seasonal text in the Battle UI is descriptive; authoritative seasonal data is whatever the backend exposes for the current build.

## Shop (V.9)

- **UI / config version** is **9.0.0** (`SHOP_UI_VERSION` in `backend/routes/shop_routes.py`, echoed as `shop_ui_version` on `GET /api/shop/config`). Older references to Shop v4/v5 or `4.0.0` in docs and scripts mean the **same product line** pre-relabel; behavior is unchanged aside from naming and storage key preference.
- **Client shadow backup**: primary key `shop_v9_shadow_{user_id}` in `localStorage`. If present, legacy `shop_v4_shadow_{user_id}` is read once and copied forward when the shop loads. Purchases dispatch **`shop-v9-purchase`** and **`shop-v4-purchase`** so Profile stays compatible.
- **Front-end API**: `window.ShopV9` on `/shop` ( **`ShopV4` is an alias** to `ShopV9` for backward compatibility). Inventory merge and “Run checks” use the same JSON list as `data/shop_v4_api_line_checks.json` (filename kept for tooling).
- **Rulebook data**: `data/rulebook_v9_shop.json` is the long reference. **V5.0** adds `guides[]` for clusters + shop navigation. **V6.1–V6.8** in `data/rulebook_v6_electric_magnet.json` under `shop_rulebook_patches[]` document shop categories **backwards** by `shop_slot` (8 = inventory … 1 = themes). **V4** notes `shop_ui_alignment` to Shop V.9.
- **Themes (wave v6)** include a single **D&D** tabletop line (the old **D6D** catalog entry is merged into `theme-dnd`; legacy `theme-d6d` inventory still resolves via `shop_item_media.json`), plus Magic: The Gathering–style, Mafia noir, AI Core, Christmas, and Home Base — cosmetic catalog lines with fan-tribute disclaimers where relevant; see `rules` in V1, V5, V6, V9 JSON.
- **Themes (wave v7 — monthly)**: twelve fixed SKUs `theme-january` … `theme-december` are documented in `data/rulebook_v9_shop.json` under **`monthly_theme_catalog`**; still cosmetic unless product code auto-equips by calendar.
- **Where shop themes live across rulebooks**: **`rulebook_v9_shop.json`** holds **`cross_rulebook_routing`** (index of responsibilities). **V1** = profile / MN2 surface + pointer to V9; **V4** = star data unchanged by UI themes; **V5** = `monthly_cluster_hints` (pedagogy, not new spells); **V6** = shop category ↔ specials / `mn2_5d` does not extend specials; **V7** = points vs MN2 + `monthly_theme_points`; **V8** = agent shop-help routing; **V10** = battle/profiling independent of shop themes; **`lab_research`** = Lab grid / exploration / co-tech share the same `game_user_id` and unified points as Shop (see **Lab** below).
- **MN2 five-day chart**: Profile’s MN2 card shows the last five UTC days of in/out activity. Shop SKUs tagged **`mn2_5d`** are narrative tie-ins to that UI; balances remain authoritative from MN2 APIs.
- Prices may be in coins, MN2, or unified point bundles. Each completed purchase is written to `shop_purchases` when tables exist, with balances before/after snapshots when the migration is applied.

## Lab (research, exploration, co-tech)

- **`/lab`** — Chapters II–III **research nodes** (catalog-driven unlocks), **exploration pulse** (unified points + hunter XP, profile cooldown), and **co-created technologies** (drafts + agent refine with their own cooldowns). Uses the same **`game_user_id`** as Shop, Profile, and Battle (see **Identity and progress**).
- **Handbook (operators + agents):** **`docs/LAB.md`** — HTTP API table, `hunters_profiles.profile_data` keys, `data/lab_progression_catalog.json`, cooldown tiers, troubleshooting, deploy file list, **ideas backlog**.
- **Rulebook data:** Shop rulebook **V9** (`data/rulebook_v9_shop.json`) includes **`cross_rulebook_routing.lab_research`** and a **`lab_handbook`** rule row pointing here and to `/lab`.
- **Game bridge:** Where implemented, `battle-bridge-snapshot` / HUD helpers may surface **lab tier** and counts so progression stays visible outside the Lab page.

## Changes

- Update this file when you change cross-cutting rules; keep the Battle **Rulebooks** tab in sync with one or two sentences pointing here, to **§ Lab** / **`docs/LAB.md`**, and to Compendium for detail.
