# New ideas (technical and product only)

No marketing. Only implementation, data, and design ideas that are concrete and actionable.

---

## 1. Event log for all state changes

Every mutation (points awarded, purchase, agent assigned, investigation, battle result) writes one record to a single append-only log: `event_type`, `user_id`, `payload`, `ts`. Leaderboards, cash, and “recommendations” are derived by reading the log (or a materialized view). New “ways to earn or spend” = new event types and new readers. No special-case APIs for “monetization” vs “game” — just events and projections.

---

## 2. 25 levers as pure config → backend actions

In config, each of the 25 levers maps to a backend action id (e.g. `lever_05` → `apply_checkout_discount`, `lever_12` → `regenerate_creative`). The app never says “optimize conversion”; it only: “run action X for user Y.” Agents get tasks like “run action for lever 12”; the system executes the action and records the result. Revenue is an outcome of correct wiring, not copy.

---

## 3. Agent capacity queue, no “recommendations” UI

Agents have a fixed capacity (e.g. N tasks per day). When you assign a lever to an agent, the agent’s queue gets a task. When a slot is free, the agent pulls the next task and runs it (e.g. “generate copy for lever 12”). No “AI suggests you focus on X” — only: queue depth, tasks completed, and a log of what was done. The UI can show queue status and history only.

---

## 4. Star Map 25 as rule-based placement

Each system has explicit rules: e.g. “level 2 requires 1 building and 2 units; no two buildings of the same type.” The client (or an agent) only submits valid placements; the server validates against the rules and updates level. No narrative layer in the rules — just predicates and state. New content = new rule sets, not new copy.

---

## 5. Quiet mode for monetization

A user or env flag: “quiet mode.” When on: no banners, no “recommended levers,” no upsell copy. The 25 levers are still available as tools (e.g. “apply lever 17 to this session” or “assign agent to lever 5”). All revenue flows from actual use of levers and shop, not from persuasion UI. Lets you test and run “no marketing” by default.

---

## 6. Achievements unlock API access

Achievement definitions include an optional `unlocks_api`: e.g. “investigated_10” → `GET /api/star-map/25/export`. When the user earns the achievement, their token or role gets permission to call that endpoint. Progress directly gates power-user features. No “reward” copy — just a new allowed route.

---

## 7. Single “monetization” service boundary

One service (or module) owns: points, purchases, PayPal, and the 25-lever state. The rest of the app calls it via a small API (e.g. “record purchase,” “get balance,” “assign lever,” “run lever action”). New “ways to make money” = new endpoints or new callers into this boundary. No duplication of “cash” or “revenue” logic across the app.

---

## 8. Audit log for assignments

Every “assign agent to lever” (or “unassign”) writes: `user_id`, `lever_id`, `agent_id`, `previous_agent_id`, `ts`. No analytics copy — just a log. Used for support (“who changed what”) and for reverting or debugging. Same pattern for “apply lever” or “run lever action” if you add it.

---

## 9. Feature flags per lever

Each of the 25 levers has a flag: on/off by environment or by user segment. No A/B “stories” or marketing wording — just: lever X is enabled or disabled. Backend and UI respect the flag (no tasks, no UI for disabled levers). Lets you ship levers incrementally and kill them without code churn.

---

## 10. Cold vs warm read path

Points and leaderboards are read from a cache or a read replica (warm path). Writes go to the primary and then invalidate or stream to the cache. The “top50” and “cash” and “levers” reads never hit the write path. Lets you add more derived views (e.g. “revenue per lever”) without slowing writes.

---

## 11. Explicit agent ledger

Whenever an agent does something that can affect revenue (e.g. “task completed for lever 12,” “copy generated”), append to an agent ledger: `agent_id`, `lever_id`, `action`, `result_ref`, `ts`. No attribution or “impact” copy — just rows. Enables debugging (“what did this agent do?”) and later analytics without touching the UI.

---

## 12. One config file: lever_id → backend_action

A single JSON (or table): `lever_id` → `action_id`, plus `action_id` → handler. So “lever 05” always means “run checkout_optimization handler” in code. New lever = new row and new handler. No lever names or “suggestions” in code — only IDs and actions. Keeps marketing and product wording out of the codebase.

---

*Doc purpose: capture new ideas that are technical or product-only. No marketing language. Update this file when you add more such ideas.*
