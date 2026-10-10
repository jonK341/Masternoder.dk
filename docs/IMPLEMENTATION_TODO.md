# Implementation TODO — Full Plan

**Date:** 2026-01-27  
**Source:** PHD Final Conclusion, user request, deployment plan.

---

## 1. Star Map & Electric Magnet

- [x] Star map: 7 nearest stars (Sun, Proxima, Alpha Cen, Barnard's, Lalande, Sirius, Eps Eri, Ross 128) — `data/star_map.json`
- [x] Electric Magnet specials: `run_verification`, `run_dna_test`, `view_star_map`
- [x] Add star map to Trophy Hunters game (tab + specials UI + info/flyers)
- [x] Verification + DNA test wired in agents and Hunters specials API (Specials buttons in Star Map tab)

## 2. Theme / Layout

- [x] **Skabelon:** `page-layout-metrics.css` — standard header-to-main spacing
- [x] Apply to all pages; fix “big space” and “too little space” (shop, gallery, profile, generator, battle, social, unified_dashboard, lab)
- [ ] Misdirection header: audit and fix page starts

## 3. Navigation

- [x] Purple background, light neon green text
- [x] Remove: Metal, Theme Points, Stats (move stats to Profile)
- [x] Remove: Champions League (merge into Battle)
- [x] Add: Trophies (Hunter Game)
- [x] Lab: placeholder page added; nav link in toolbar; all_page route
- [ ] Check new pages for nav inclusion

## 4. Social

- [ ] Prepare for social networking; account creation & login (big providers)
- [ ] Maintain accounts flow

## 5. Analytics & Debugger

- [ ] Flatten analytics with debugger
- [x] Debugger: fix line between header and main (more space via page-layout-metrics)

## 6. Battle & Champions League

- [x] Remove Champions League from nav (merge into Battle pending)
- [ ] Battle: hardtest URL, snapshot, fix plugins

## 7. Shop

- [x] Add goods; game/shop + shop-v3 items API with 100+ seed items
- [x] Purchase placeholder; currency API
- [ ] Valued Sellers Choice, link boosters, game time (extend as needed)

## 8. Gallery

- [x] Gallery API: `/vidgenerator/api/gallery/list`, `/video/<id>`, `/video/<id>/download`; categories list; sample videos when no files

## 9. Generator

- [ ] Divide: clip (4–6 s) vs 30 s vid service
- [ ] Add service_worker to generation process
- [ ] Unified points in generator
- [ ] Checkpoint on/off feature
- [ ] Hardtest free/empty space; div content if needed

## 10. Lab

- [x] Lab placeholder page; nav link; all_page route; fix visibility

## 11. Unified Dashboard

- [ ] Verification; apply plugins; link checks
- [x] Tech + agent service everywhere; point triggers (EM/ET in debugger; triggers on specials)

## 12. Database

- [x] A++ migrations: `migrations/hunters_star_map_ground_level.py` (player_levels, rewards, user_rewards, xp_history, star_map_visits, hunters_*, knowledge_base)
- [x] Knowledge base (knowledge_base table in migration)
- [x] Hunters tables (player_levels, rewards, user_rewards, xp_history) created by migration

## 13. Agents & Game

- [x] Agent tech + skills in debugger; skill feature (Agent Tech & Skills tab)
- [x] Add game to profile page (Trophy Hunters block + Game/Trophies links)
- [x] Event tracker; GPS/geo-ref in profile (track_new_task, geo-ref API + profile UI)
- [x] Aggregator (fulfill API) for Hunter game missing parts (/api/game/hunters/aggregator-fulfill)
- [x] 19 theme-based spells (Rulebook V.2/V.3); effect clusters
- [x] Game points → unified point system (triggers, award-game-points, add_points)
- [ ] Clickthrough, longevity, game-time hooks (partial; extend session etc. in rulebook)

## 14. Vidgenerator

- [x] New triggers to dashboards (galaxy/hunters triggers, point triggers on specials)
- [x] 3D monitor placeholder (data/config_3d_monitor.json)
- [ ] Extra test data in API for context

## 15. Deploy

- [ ] Verify all routes before deploy
- [ ] No restart until all ready
- [x] Upload/update/deploy in single connection
- [x] 502 fix: gateway-safe restart (python-proxy → uwsgi-vidgenerator → nginx reload); upstream check before nginx

---

*Redefine and reconclude; align with PHD_FINAL_CONCLUSION.md.*
