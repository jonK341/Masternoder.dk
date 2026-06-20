# MasterNoder Compendium — Rulebook V1–V15

**Full rulebook collection.** Complete rules for galaxy-oriented intelligence, Hunters game, unified points, sync mechanisms, and platform systems.  
Index version: **V15** (catalog includes **V16**) · Last updated: 2026-06-17

**Readers & progress:** [RULEBOOK_READERS.md](./RULEBOOK_READERS.md)

---

## Canonical Compendium URLs (web)

Rulebooks and Communication Psychology pages are served at **`/compendium/...`** on the site root (not under `/vidgenerator/`). Both trailing `.html` and extensionless URLs work where the Flask routes define them.

| Version | Viewer / page URL |
|---------|---------------------|
| V1 | `/compendium/rulebook-v1` |
| V2 Hunters | `/compendium/hunters-rulebook` |
| V3 (25 theories) | `/compendium/page-1.html` … `/compendium/page-10.html` |
| V3.2 | `/compendium/rulebook-v3-2` |
| V4–V14 | `/compendium/rulebook-v4` … `/compendium/rulebook-v14` |
| V15 Master index | `/compendium/` (compendium page **24**) |
| V16 Sync | `/compendium/rulebook-v16` (compendium page **25**) |

**API (unchanged):** `GET /api/rulebooks/index` returns each entry’s `url_path` aligned with the table above.

**Cross-rulebook routing** (shop, monthly themes, MN2, which volume owns which prose) is defined in `data/rulebook_v9_shop.json` under `cross_rulebook_routing` and summarized for humans in `docs/RULEBOOK_CANON.md`.

---

## Agent schema (all rulebooks)

| Field | Purpose |
|-------|---------|
| **agent_prompt** | Instruction text for agent system prompts. Undergoing knowledge. |
| **tech_spec** | Technical specs, APIs, endpoints. For agent tool use. |
| **user_guide** | User-facing guidance. Agents cite when helping users. |
| **manual** | Agent manual section. How to behave, what to do. |
| **documentation** | Closing documentation and references. Synced from agent learning. |
| **finish_lines** | Closing notes and references for the rulebook. |

**API:** `GET /api/rulebooks/index` · `GET /api/rulebooks/<version>` · `GET /api/rulebooks/agent-context`

---

# V1 — Core Rules & Foundation

**Name:** Core Rules & Foundation  
**Version:** V1  
**Description:** Grundlæggende mekanikker, profiler og onboarding.

**Agent prompt:** Always use user_id (game_user_id) for all user-specific operations. Use user_index for generation and account control. Profiles are created per user via onboarding.

**Tech spec:**  
`user_id: string` · `user_index: SHA256(user_id) mod 1000000` · `GET /api/user/index?user_id=` · `GET /api/user/account-control?user_id=` · `user_onboarding.get_user_profile(user_id)`

**User guide:** Din profil bruger game_user_id. Bruger-index bruges til generation. Profil oprettes ved første besøg.

**Manual:** Agent manual V1: Resolve user_id from request context. Use user_index when passing to generator or account-control APIs.

### Rules

| ID | Name | Text |
|----|------|------|
| profile | Brugerprofil | Hver bruger har en profil med preferences, scraped_info og assigned_agent_ids. |
| onboarding | Onboarding | Nye brugere gennemgår onboarding. Profil oprettes ved første besøg. |
| user_id | Bruger-ID | Stabil bruger-ID (game_user_id) bruges til points, trophies og alle bruger-specifikke data. |
| user_index | Bruger-index | Numerisk index afledt af user_id for generation og account control. |

---

# V2 — Trophy Hunters Rulebook

**Name:** Trophy Hunters Rulebook  
**Version:** V2.1  
**Description:** Theme-based spells and sectors for Hunters game. 19 spells in 5 sectors: Galactic, Verification, Combat, Support, Utility.

**Agent prompt:** Trophy Hunters: 19 spells in 5 sectors (Galactic, Verification, Combat, Support, Utility). Spells reference star map, verification, DNA, checkpoint, geo_ref, speaker_ruler.

**Tech spec:** `GET /api/game/hunters/rulebook` · sectors: I_galactic, II_verification, III_combat, IV_support, V_utility · all_spell_ids · spell cost and effect

**User guide:** 19 spells i 5 sektorer. Galactic, Verification, Combat, Support, Utility. Køb og cast spells.

**Manual:** Agent manual V2: Hunters rulebook. List spells by sector. Explain cost and effect. Link to star map and verification.

### Sectors and spells

#### I — Galactic
| Spell | Effect | Cost | Icon |
|-------|--------|------|------|
| Star Map | view_star_map | 10 | 🌟 |
| Proxima B Beacon | proxima_b_beacon | 25 | 🪐 |
| Sirius B Pulse | sirius_b_pulse | 30 | ⚡ |
| Earth B Shield | earth_b_shield | 15 | 🛡️ |

#### II — Verification
| Spell | Effect | Cost | Icon |
|-------|--------|------|------|
| Run Verification | run_verification | 20 | ✔️ |
| DNA Test | run_dna_test | 25 | 🧬 |
| Integrity Scan | integrity_scan | 18 | 🔍 |

#### III — Combat
| Spell | Effect | Cost | Icon |
|-------|--------|------|------|
| Trophy Strike | trophy_strike | 22 | 🏆 |
| Hunter Fury | hunter_fury | 35 | 🔥 |
| Precision Shot | precision_shot | 12 | 🎯 |

#### IV — Support
| Spell | Effect | Cost | Icon |
|-------|--------|------|------|
| Heal Trophy | heal_trophy | 20 | 💚 |
| Buff Creativity | buff_creativity | 15 | 🎨 |
| Buff Knowledge | buff_knowledge | 15 | 📚 |

#### V — Utility
| Spell | Effect | Cost | Icon |
|-------|--------|------|------|
| Clickthrough | clickthrough | 5 | 👆 |
| Extend Session | extend_session | 28 | ⏱️ |
| Checkpoint | checkpoint | 40 | 📌 |
| Aggregator Fill | aggregator_fill | 32 | 📦 |
| Geo Reference | geo_reference | 18 | 📍 |
| Speaker Ruler | speaker_ruler | 50 | 🗣️ |

**All spell IDs:** spell_star_map, spell_proxima_b, spell_sirius_b, spell_earth_b, spell_run_verification, spell_dna_test, spell_integrity_scan, spell_trophy_strike, spell_hunter_fury, spell_precision_shot, spell_heal_trophy, spell_buff_creativity, spell_buff_knowledge, spell_clickthrough, spell_extend_session, spell_checkpoint, spell_aggregator_fill, spell_geo_ref, spell_speaker_ruler

---

# V3 — Communication Psychology

**Name:** Communication Psychology — 25 Theories  
**Version:** V3  
**Description:** Theories for understanding influence, framing, and platform authority. Integrated with Masternoder.dk starmap, DNA theory, and unified points.

**Agent prompt:** Communication Psychology: 25 theories in 6 categories. Power dynamics, social influence, rhetoric, psychological warfare, digital power, monetization. Study unlocks theories and awards communication_psychology_points.

**Tech spec:** `GET /api/communication-psychology/theories` · `POST study` · categories · theories[].id, short, description, point_value · get_user_progress(user_id)

**User guide:** 25 teorier i 6 kategorier. Studer for at låse op og få point. Integreret med trophies.

**Manual:** Agent manual V3: When user asks about influence or framing, cite theories. Study awards points. Link to trophies Comm. Psychology tab.

### Categories
- **power_dynamics** — Grundlæggende Magtdynamikker ⚡
- **social_influence** — Social Indflydelse & Stammetænkning 👥
- **rhetoric** — Retorik & Overtalelse 🎭
- **psychological_warfare** — Psykologisk Krigsførelse & Myter 🧠
- **digital_power** — Digital Magt & Viralitet 📡
- **monetization** — Monetarisering & Kontrol 💎

### 25 theories

| # | ID | Name | Short | Category | Point |
|---|-----|------|-------|----------|-------|
| 1 | agenda_setting | Agenda-Setting Theory | Du bestemmer ikke hvad folk tænker, men hvad de tænker på. | power_dynamics | 40 |
| 2 | spiral_of_silence | The Spiral of Silence | Modstandere tier når de tror de er i mindretal. | power_dynamics | 40 |
| 3 | framing_theory | Framing Theory | Indramning ændrer hele præmissen for hvordan budskaber læses. | power_dynamics | 40 |
| 4 | cultivation_theory | Cultivation Theory | Gentagelse ændrer opfattelse af virkeligheden over tid. | power_dynamics | 40 |
| 5 | in_group_out_group | In-group/Out-group Bias | Os mod dem — stærk tribalism. | social_influence | 35 |
| 6 | social_proof | Social Proof | Folk følger mængden. | social_influence | 35 |
| 7 | sleeper_effect | The Sleeper Effect | Budskabet sætter sig; kilden glemmes. | social_influence | 35 |
| 8 | cognitive_dissonance | Cognitive Dissonance | Ubehag ved modstrid — tilbyd løsning. | social_influence | 35 |
| 9 | rhetorical_triangle | The Rhetorical Triangle (Ethos, Pathos, Logos) | Autoritet, følelser og logik i balance. | rhetoric | 38 |
| 10 | anchor_point | Anchor Point Theory | Præsenter ekstrem først — din teori virker rationel bagefter. | rhetoric | 38 |
| 11 | inoculation_theory | Inoculation Theory | Vacciner mod kritik ved selv at nævne den først. | rhetoric | 38 |
| 12 | elaboration_likelihood | Elaboration Likelihood Model (ELM) | Perifer rute vs central rute — tilpas til publikum. | rhetoric | 38 |
| 13 | illusory_truth | The Illusory Truth Effect | Gentagelse gør budskabet 'sandt' i hjernen. | psychological_warfare | 42 |
| 14 | confirmation_bias | Confirmation Bias | Servér præcis det indhold brugerne leder efter. | psychological_warfare | 42 |
| 15 | narrative_transportation | Narrative Transportation | Historier slår fakta til overbevisning. | psychological_warfare | 42 |
| 16 | authority_bias | Authority Bias | Titler og symboler skaber adlydelse. | psychological_warfare | 42 |
| 17 | network_effects | Network Effects | Jo flere brugere, jo mere værdifuld platformen. | digital_power | 36 |
| 18 | echo_chamber | The Echo Chamber Effect | Kun indhold der understøtter din sag. | digital_power | 36 |
| 19 | gamification_of_belief | Gamification of Belief | Stig i graderne — lær mere, få højere status. | digital_power | 36 |
| 20 | scarcity_principle | Scarcity Principle | Hemmelige teorier kun for elite eller betalende. | digital_power | 36 |
| 21 | reciprocity | Reciprocity (Gengældelse) | Giv gratis viden — folk vil give tilbage. | monetization | 45 |
| 22 | us_vs_institution | Us vs. The Institution Marketing | Markedsfør produkter som våben mod undertrykkelse. | monetization | 45 |
| 23 | symbolic_convergence | Symbolic Convergence Theory | Egne ord, udtryk og symboler skaber fælles bevidsthed. | monetization | 45 |
| 24 | fud | Fear, Uncertainty, and Doubt (FUD) | Skab tvivl om strukturer; tilbyd anker i kaosset. | monetization | 45 |
| 25 | halo_effect | The Halo Effect | Succes på ét område overfører tillid til andre. | monetization | 45 |

---

# V4 — Star Map & Verification

**Name:** Star Map & Verification  
**Version:** V4  
**Description:** 7 nærmeste stjerner, host→life-bearing b navngivning, Electric Magnet specials.

**Agent prompt:** Star map: 7 nearest stars. Use host→b naming (e.g. Proxima Centauri → Proxima b). Specials: run_verification, run_dna_test, view_star_map.

**Tech spec:** `GET /api/star-map` · `GET /vidgenerator/api/star-map` · data/star_map.json · stars[].life_label, life_bearing · specials: run_verification, run_dna_test, view_star_map

**User guide:** Stjernemap viser 7 nærmeste stjerner. Brug verification og DNA test til integritet.

**Manual:** Agent manual V4: When user asks about stars or verification, call star-map API. Offer run_verification and run_dna_test when relevant.

### Rules
| ID | Name | Text |
|----|------|------|
| host_b | Host → B navngivning | Life-bearing planeter navngives som host → b (f.eks. Proxima Centauri → Proxima b). |
| run_verification | Run Verification | Electric Magnet special. Integritetsscan af indhold og platform. |
| run_dna_test | Run DNA Test | Electric Magnet special. DNA-verifikation og test. |
| view_star_map | View Star Map | Electric Magnet special. Viser 7 nærmeste stjerner og life-bearing b planeter. |
| integrity_scan | Integrity Scan | Hunters spell. Relateret til verification. |

---

# V5 — Effect Clusters

**Name:** Effect Clusters  
**Version:** V5  
**Description:** 5 effektklynger der aligner med Hunters rulebook V2 sektorer.

**Agent prompt:** Effect clusters: Galactic, Verification, Combat, Support, Utility. Align with Hunters rulebook V2 sectors.

**Tech spec:** `GET /api/game/hunters/effect-clusters` · clusters: galactic, verification, combat, support, utility

**User guide:** Effektklynger grupperer spells i 5 sektorer. Brug dem til at forstå Hunters game.

**Manual:** Agent manual V5: Effect clusters map to Hunters sectors. Use when explaining game mechanics.

### Clusters
| Cluster | Effects |
|---------|---------|
| galactic | view_star_map, proxima_b_beacon, sirius_b_pulse, earth_b_shield |
| verification | run_verification, run_dna_test, integrity_scan |
| combat | trophy_strike, hunter_fury, precision_shot |
| support | heal_trophy, buff_creativity, buff_knowledge |
| utility | clickthrough, extend_session, checkpoint, aggregator_fill, geo_reference, speaker_ruler |

---

# V6 — Electric Magnet

**Name:** Electric Magnet  
**Version:** V6  
**Description:** Specials og tech tree. Electric Magnet tech integration.

**Agent prompt:** Electric Magnet specials: run_verification, run_dna_test, view_star_map. Shared with Hunters game and agents.

**Tech spec:** Specials: run_verification, run_dna_test, view_star_map · agent_electric_magnet · skillsets.json · electric_magnet_tech

**User guide:** Electric Magnet specials: verification, DNA test, stjernemap. Tilgængelige i Hunters game.

**Manual:** Agent manual V6: Agents with specials use these three. Expose via execute or view_star_map.

### Specials
- run_verification
- run_dna_test
- view_star_map

### Rules
| ID | Name | Text |
|----|------|------|
| specials | Electric Magnet Specials | Tre specials deles mellem Electric Magnet, Hunters game og agent skillsets. |
| tech_tree | Tech Tree | electric_magnet_tech inkluderer view_star_map og star_map path. |
| agent_share | Agent Integration | Agents med specials bruger samme liste. Debugger og profile viser dem konsistent. |

---

# V7 — Unified Points

**Name:** Unified Points  
**Version:** V7  
**Description:** Alle pointtyper og triggers i det forenede pointsystem.

**Agent prompt:** Unified points: xp_points, game_points, trophy_points, dna_manipulation_points, dna_cloning_points, communication_psychology_points, compendium_points. Use add_points for awards.

**Tech spec:** unified_points_db.add_points(user_id, point_type, amount, source, metadata) · unified_points_trigger_integration · triggers map activities to point types

**User guide:** Forenede points: XP, game, trophy, DNA, comm. psych, compendium. Aktiviteter giver point.

**Manual:** Agent manual V7: When awarding points, use add_points. Include source and metadata. Triggers fire on video_gen, study_theory, compendium_view.

### Point types
xp_points, game_points, trophy_points, dna_manipulation_points, dna_cloning_points, communication_psychology_points, compendium_points

### Rules
| ID | Name | Text |
|----|------|------|
| add_points | Add Points | unified_points_db.add_points(user_id, point_type, amount, source, metadata). |
| triggers | Triggers | unified_points_trigger_integration mappes til aktiviteter (video_gen, study_theory, compendium_view, osv.). |
| profile_display | Profile Display | get_profile_display inkluderer alle pointtyper fra unified points. |

---

# V8 — Agents & Skillsets

**Name:** Agents & Skillsets  
**Version:** V8  
**Description:** Agent specials, skillsets, Electric Magnet integration.

**Agent prompt:** Agents use specials (run_verification, run_dna_test, view_star_map) and skillsets. Skillsets are additive. Debugger shows tech and skills.

**Tech spec:** logs/agent_skillsets/skillsets.json · specials additive to skills · agent_electric_magnet, agent_event_tracker · debugger agent tab

**User guide:** Agenter har specials og skills. Debugger viser agent tech og skills.

**Manual:** Agent manual V8: You are an agent. Use this rulebook as context. Follow specials and skillsets. Debugger exposes your capabilities.

### Specials
run_verification, run_dna_test, view_star_map

### Rules
| ID | Name | Text |
|----|------|------|
| skillsets | Skillsets | logs/agent_skillsets/skillsets.json. Specials additive til skills. |
| agent_tech | Agent Tech | agent_electric_magnet, agent_event_tracker. Specials deles på tværs. |
| debugger | Debugger | Tech og skills eksponeres i debugger. Skills feature til agent-valg. |

---

# V9 — Shop & Monetization

**Name:** Shop & Monetization  
**Version:** V9  
**Description:** Shop items, purchases, inventory, monetization flows.

**Agent prompt:** Shop: Electric Magnet, Star Map, Lab, Verification, DNA, Rulebook, Communication Psychology packs. Purchases update inventory.

**Tech spec:** shop_routes · purchase flow · inventory · items reference rulebooks and specials

**User guide:** Shop: køb Electric Magnet, Star Map, Lab, Rulebook, Comm. Psych. Køb opdaterer inventory.

**Manual:** Agent manual V9: When user asks about shop, list available items. Do not process purchases; direct to shop UI.

### Rules
| ID | Name | Text |
|----|------|------|
| shop_items | Shop Items | Electric Magnet, Star Map, Lab, Verification, DNA, Rulebook, Communication Psychology packs. |
| purchases | Purchases | Shop purchase flow. Inventory opdateres ved køb. |
| monetization | Monetization | Monetization flows integreret med unified points og profile. |

---

# V10 — Battle & Leaderboard

**Name:** Battle & Leaderboard  
**Version:** V10  
**Description:** Hunters profiling, leaderboard, geo_ref, aggregator-fulfill.

**Agent prompt:** Hunters profiling, leaderboard, geo_ref. Aggregator-fulfill fills missing Hunters data. Rulebook spell aggregator_fill.

**Tech spec:** `GET /api/game/hunters/profiling?user_id=` · agent_geo_refs · aggregator-fulfill · geo_ref in profiling

**User guide:** Hunters profiling viser level, specials. Geo-ref og leaderboard tilgængelige.

**Manual:** Agent manual V10: Profiling returns agent_tech, specials, level_info. Use geo_ref when location context needed.

**Documentation:** Battle rulebook: agent battle skill set is wired via get_battle_skill_set_for_rulebook(). All agents have battle skills; compendium and rulebooks stay in sync via agent knowledge API.

**Finish lines:**
- Agent Battle Skill Set: applied to all agents; export for rulebooks via agent_skillset.get_battle_skill_set_for_rulebook().
- Unified Points Sync Device: single source of truth for points; use for battle_points and leaderboard consistency.
- Agent learning: POST /api/rulebooks/agent-knowledge to append learned technology; GET for compendium display.

### Rules
| ID | Name | Text |
|----|------|------|
| profiling | Hunters Profiling | GET /api/game/hunters/profiling. Returnerer agent_tech, specials, level_info, geo_ref. |
| geo_ref | Geo Reference | agent_geo_refs table. Geo-ref i profiling. Schema klar. |
| aggregator_fulfill | Aggregator Fulfill | Fylder manglende Hunters data. Rulebook spell aggregator_fill. |

---

# V11 — DNA Theory

**Name:** DNA Theory  
**Version:** V11  
**Description:** DNA manipulation points, cloning, verification integration.

**Agent prompt:** DNA: dna_manipulation_points, dna_cloning_points. run_dna_test is Electric Magnet special. Integrates with lab and verification.

**Tech spec:** dna_manipulation_points, dna_cloning_points · run_dna_test · lab integration · verification

**User guide:** DNA: manipulation og cloning points. Brug DNA test via Electric Magnet.

**Manual:** Agent manual V11: DNA points awarded on DNA-related activities. run_dna_test available as special.

### Point types
dna_manipulation_points, dna_cloning_points

### Rules
| ID | Name | Text |
|----|------|------|
| manipulation | DNA Manipulation | dna_manipulation_points tildeles ved DNA-relaterede aktiviteter. |
| cloning | DNA Cloning | dna_cloning_points. Integreret med verification og lab. |
| run_dna_test | Run DNA Test | Electric Magnet special. DNA-verifikation. |

---

# V12 — Generator & Video

**Name:** Generator & Video  
**Version:** V12  
**Description:** Video generator, content categories, conspiracy/alternative_theories triggers.

**Agent prompt:** Video generator: content_category conspiracy/alternative_theories/religious_conspiracy/theory awards communication_psychology_points. Pass user_id and user_index to generation.

**Tech spec:** video_generator_service · content_category: conspiracy, alternative_theories, religious_conspiracy, theory · GET /api/user/account-control for user context

**User guide:** Generator: vælg kategori. Visse kategorier giver comm. psych points. Bruger-kontekst bruges i generation.

**Manual:** Agent manual V12: When starting generation, fetch user context from account-control. Pass user_id and user_index in metadata.

### Rules
| ID | Name | Text |
|----|------|------|
| content_categories | Content Categories | conspiracy, alternative_theories, religious_conspiracy, theory trigger communication_psychology_points. |
| video_gen | Video Generation | video_generator_service. Awards points baseret på content_category. |
| user_context | User Context | user_id og user_index fra account-control bruges i generation metadata. |

---

# V13 — Geo & Session

**Name:** Geo & Session  
**Version:** V13  
**Description:** geo_reference, checkpoint, extend_session, aggregator_fill.

**Agent prompt:** Geo & Session: geo_reference (GPS), checkpoint (generator on/off), extend_session, aggregator_fill. Hunters utility spells.

**Tech spec:** geo_reference cost 18 · checkpoint cost 40 · extend_session cost 28 · aggregator_fill cost 32 · agent_geo_refs · aggregator-fulfill API

**User guide:** Geo-ref, checkpoint, session length. Hunters utility spells.

**Manual:** Agent manual V13: geo_ref for location. checkpoint and extend_session for session hooks. aggregator_fill for missing data.

### Spells (cost)
| Spell | Cost |
|-------|------|
| geo_reference | 18 |
| checkpoint | 40 |
| extend_session | 28 |
| aggregator_fill | 32 |

### Rules
| ID | Name | Text |
|----|------|------|
| geo_reference | Geo Reference | Hunters spell. Cost 18. GPS/geo-ref i agent_geo_refs. |
| checkpoint | Checkpoint | Hunters spell. Cost 40. Generator on/off placeholder. |
| extend_session | Extend Session | Hunters spell. Cost 28. Session length hooks. |
| aggregator_fill | Aggregator Fill | Hunters spell. Cost 32. Fylder manglende Hunters data. |

---

# V14 — Analytics & Dashboard

**Name:** Analytics & Dashboard  
**Version:** V14  
**Description:** Event tracker, analytics, dashboard, agent_event_tracker.

**Agent prompt:** Analytics: event tracker, agent_event_tracker/track_new_task, analytics dashboard, unified dashboard. Track agent tasks and events.

**Tech spec:** agent_event_tracker · track_new_task · analytics · unified_dashboard · points and stats display

**User guide:** Analytics dashboard viser tracking og stats. Event tracker for agent tasks.

**Manual:** Agent manual V14: Report tasks via track_new_task. Analytics dashboard aggregates. Use for debugging and monitoring.

### Rules
| ID | Name | Text |
|----|------|------|
| event_tracker | Event Tracker | agent_event_tracker/track_new_task. Tracks agent tasks og events. |
| analytics | Analytics | Analytics dashboard. Tracking af brug og konvertering. |
| unified_dashboard | Unified Dashboard | Points, stats og oversigt samlet i dashboard. |

---

# V15 — Master Index

**Name:** MasterNoder Rulebook Index  
**Version:** V15  
**Description:** Complete rulebook catalog V1–V15. All rules needed for galaxy-oriented intelligence, Hunters game, unified points, and platform systems.

**Agent prompt:** V15 Master Index. Load agent context via /api/rulebooks/agent-context.

**Tech spec:** GET /api/rulebooks/agent-context

**User guide:** Overblik over alle rulebooks. Plads til idéer.

**Manual:** Agent manual V15: Use agent-context API. Extend as needed.

### Catalog (V1–V15)

| Order | Version | Name | Short |
|-------|---------|------|-------|
| 1 | V1 | Core Rules & Foundation | Grundlæggende mekanikker, profiler og onboarding. |
| 2 | V2 | Trophy Hunters Rulebook | 19 tema-baserede spells i 5 sektorer. |
| 3 | V3 | Communication Psychology | 25 teorier om indflydelse, framing og platformautoritet. |
| 4 | V4 | Star Map & Verification | 7 nærmeste stjerner, verification og DNA test. |
| 5 | V5 | Effect Clusters | 5 effektklynger til Hunters game. |
| 6 | V6 | Electric Magnet | Specials og tech tree. |
| 7 | V7 | Unified Points | Alle pointtyper og triggers. |
| 8 | V8 | Agents & Skillsets | Agent specials og skills. |
| 9 | V9 | Shop & Monetization | Items, køb og inventory. |
| 10 | V10 | Battle & Leaderboard | Profiling og leaderboard. |
| 11 | V11 | DNA Theory | Cloning og manipulation. |
| 12 | V12 | Generator & Video | Content creation og kategorier. |
| 13 | V13 | Geo & Session | Geo-ref, checkpoint og session length. |
| 14 | V14 | Analytics & Dashboard | Tracking og analytics. |
| 15 | V15 | Master Index | Overblik over alle rulebooks V1–V15. |
| 16 | V16 | Sync Mechanisms | Unified sync device, domain sync, status API. |

---

# V16 — Sync Mechanisms

**Name:** Sync Mechanisms  
**Version:** V16  
**Description:** Unified sync device, domain sync, status API, and dashboard integration.

**Agent prompt:** Sync device: unified_points_sync_device. Use record_domain_sync(domain) when your system writes data.

**Tech spec:** GET /api/sync/status · POST /api/sync/now · unified_points_sync_device.record_domain_sync(domain, count?, extra?)

**User guide:** Sync status vises på dashboards (unified, profile, stats). Points, users, profiles, rulebooks, agents og knowledge er synkroniseret.

**Manual:** Agent manual V16: When implementing a new feature that writes data, add record_domain_sync(domain) after successful write.

### Rules
| ID | Name | Text |
|----|------|------|
| sync_device | Unified Points Sync Device | unified_points_sync_device in backend/services/unified_points_sync.py |
| domain_sync | Domain Sync | Call record_domain_sync after successful write |
| sync_status_api | Sync Status API | GET /api/sync/status returns domains, rulebooks, agent_skillsets |
| dashboard_widget | Dashboard Widget | sync-status-widget.js on unified_dashboard, profile, stats |

**Data file:** `data/rulebook_v16_sync.json` · **Reader:** `/compendium/rulebook-v16` · **Compendium page:** 25

---

## Data files reference

| Version | Data file |
|---------|-----------|
| V1 | data/rulebook_v1_core.json |
| V2 | data/hunters_rulebook_v2.json |
| V3 | data/communication_psychology_theories.json |
| V3.2 | data/rulebook_v3_2_systemic_protocols.json |
| V4 | data/rulebook_v4_star_map.json |
| V5 | data/rulebook_v5_effect_clusters.json |
| V6 | data/rulebook_v6_electric_magnet.json |
| V7 | data/rulebook_v7_unified_points.json |
| V8 | data/rulebook_v8_agents.json |
| V9 | data/rulebook_v9_shop.json |
| V10 | data/rulebook_v10_battle.json |
| V11 | data/rulebook_v11_dna.json |
| V12 | data/rulebook_v12_generator.json |
| V13 | data/rulebook_v13_geo_session.json |
| V14 | data/rulebook_v14_analytics.json |
| V15 | data/rulebook_index_v15.json |
| V16 | data/rulebook_v16_sync.json |

---

*End of Compendium — Rulebook V1–V16*
