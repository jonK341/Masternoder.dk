# Agent skills and conclusions

Summary of agent skill types (including criticism) and conclusions for design, sync, and use.

---

## 1. Agent skill types

| Skill type | Service method | Power field | Purpose |
|------------|----------------|-------------|---------|
| **Battle** | `ensure_battle_skills_per_agent` | `battle_skill_power_total` | Combat, matchups, battle leaderboard. |
| **Sales** | `ensure_sales_skillsets_per_agent` | `sales_skill_power_total` | Monetization, conversion, offers. |
| **PayPal** | `ensure_paypal_skillsets_per_agent` | `paypal_skill_power_total` | Checkout, payments, coin packs. |
| **Top 25** | `ensure_top25_skill_upgrades_per_agent` | `top25_upgrade_power_total` | Curated monetization levers. |
| **Shared growth** | `ensure_shared_growth_skills` | (distributed) | Cross-agent growth skills. |
| **Knowledge** | `ensure_knowledge_skills_per_agent` | — | Rulebook, compendium, page info. |
| **AI** | `ensure_ai_skills_per_agent` | — | AI assist, learn, optimize. |
| **Criticism** | `ensure_criticism_skills_per_agent` | `criticism_skill_power_total` | Review, feedback, quality assessment. |

Criticism domains (examples): `code_review`, `logic_gaps`, `edge_case_audit`, `security_audit`, `performance_review`, `copy_review`, `tone_consistency`, `fact_check`, `bias_detection`, `accessibility_review`, `ux_critique`, `flow_analysis`, `assumption_challenge`, `risk_flag`, `alternative_suggest`, `documentation_quality`, `api_design_review`, `test_coverage_critique`, `refactor_priority`, `stakeholder_feedback`. All profiles use `constructive_only: True`.

---

## 2. Where skills are used

- **Profile / My agents:** Shows agents and their power totals (sales, PayPal, battle, etc.). Add `criticism_skill_power_total` to displays if you want to show criticism strength.
- **Shop:** Best agent for sale and agent offers use `paypal_skill_power_total`, `sales_skill_power_total`, `battle_skill_power_total`. Criticism can be used for “review” or “quality” offers.
- **Battle:** Agent-vs-agent battles use `battle_skill_profiles` and `battle_skill_power_total`.
- **Tasks / Rulebook:** Assignments and rulebook context can reference any skill set; criticism skills are available for review and feedback tasks.

---

## 3. Conclusions

- **Criticism completes the set.** Agents already had battle, sales, PayPal, top25, growth, knowledge, and AI skills. Adding **criticism** gives them an explicit capability for review and quality: code, content, UX, security, bias, and alternatives. Use it for quality gates, feedback loops, and “review this” agent tasks.
- **One place to extend.** New skill types follow the same pattern: add a constant (e.g. `DEFAULT_CRITICISM_SKILLS_PER_AGENT`), implement `_generate_*_skill_profiles` and `ensure_*_skills_per_agent`, call the ensure from `load_skillsets()`, and expose the power total where needed (profile, shop, battle).
- **Sync and consistency.** Global skill sets are in `agent_skillset`; per-user assignments in `user_agent_skills`. Keep them in sync by running the ensure methods on load or via dedicated endpoints. See `docs/AGENTS_SKILLS_SYNC.md`.
- **Constructive only.** Criticism skills are defined with `constructive_only: True` so agents are steered toward actionable feedback rather than purely negative critique. This should be reflected in prompts and task descriptions when using criticism skills.
- **Power totals are comparable.** Battle, sales, PayPal, top25, and now criticism each have a `*_power_total`. The UI and shop can rank or filter agents by these totals; adding criticism allows “best reviewer” or “quality lead” style selection.
- **Documentation.** When adding a new skill type, update this doc, `AGENTS_SKILLS_SYNC.md`, and any API/UI docs that list agent fields so conclusions and behavior stay clear for future changes.
