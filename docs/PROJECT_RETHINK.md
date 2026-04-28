# Masternoder.dk — Project Rethink

**Using:** Cursor marketplace skills (**brainstorming** + **agent-native-architecture**) to rethink the whole project.

**Date:** 2025-02-24

---

## 1. What We're Rethinking

**Current state (one line):**  
AI video-generation platform with generator, gallery, stats, game layer (achievements, battles), profile, debugger, and many agent routes/services.

**Rethink goal:**  
Align the whole project around clearer product intent, simpler architecture, and—where it fits—**agent-native** design (agents as first-class citizens, not bolted on).

---

## 2. Brainstorming Lens: Clarify Intent First

Before changing code, nail down **WHAT** the product is for (brainstorming skill: understand the idea before HOW).

| Topic | Questions to resolve |
|-------|----------------------|
| **Purpose** | Is the core value “create videos,” “game/engagement around creation,” or “agent-powered workflows”? One primary, others secondary. |
| **Users** | Who uses it? Creators only, or creators + viewers + “players” (battle/achievements)? |
| **Success** | How do you know it’s working? (e.g. videos created, time in app, battles played, agent tasks completed.) |
| **Scope** | Keep generator + gallery + game + agents, or simplify to a smaller “v1” and expand later? |

**Recommendation:** Decide the **one sentence** that describes Masternoder.dk (e.g. “A place where you create short clips and level up by playing battles and earning points”). Use that to cut or defer features that don’t serve it.

---

## 3. Agent-Native Architecture Lens

The marketplace **agent-native-architecture** skill says: *features are outcomes achieved by agents with tools in a loop; parity between UI and agent capabilities; prefer atomic tools.*

### 3.1 Parity Check (UI ↔ Agent)

**Principle:** Whatever the user can do in the UI, the agent should be able to achieve with tools.

| User action (UI) | How an agent could achieve it today |
|------------------|--------------------------------------|
| Create video (generator) | Call generator API / unified generate-video (if exposed as tool). |
| View gallery, download | Needs tools: list videos, get video URL/file. |
| Play battle, view leaderboard | Battle APIs exist; agent needs tools that map to same outcomes. |
| View/edit profile | Profile APIs; agent needs read/update profile tools. |
| Earn points, achievements | Points are written by backend; agent could trigger same triggers (e.g. rewards). |

**Gap:** Many UI flows exist; the **agent controller** and individual agent routes are fragmented. There is no single “capability map” (UI action → agent tool). Rethink: **one capability map** and ensure every user action has a corresponding agent-achievable outcome (one or more tools).

### 3.2 Granularity (Primitives vs Workflows)

**Principle:** Prefer atomic primitives; features = outcomes from agent loops, not big “workflow” tools.

| Current style | More agent-native |
|---------------|-------------------|
| “Generate video” as one black box | Primitives: set config, start job, poll status, get video URL, award points. Agent composes them. |
| “Run battle” as one call | Primitives: create match, submit moves, get result, update points. Agent can retry, branch, explain. |
| Many specialized agent routes | Fewer, more generic tools (e.g. “run_generator_job”, “run_battle”) + rich context in prompts. |

**Rethink:** Expose **generator**, **battle**, **profile**, **points** as small, composable tools. Let the agent (or a single “orchestrator” agent) use them in a loop to satisfy user goals (“create a clip and then enter a battle”).

### 3.3 Composability (New Features = New Prompts)

**Principle:** With parity and atomic tools, new behaviors can be added by new prompts, not only new code.

- Example: “Weekly recap” = prompt that uses tools: list my videos, list my battles, get my points → summarize.
- Today: would require new endpoints and new UI. After rethink: one new prompt + existing tools.

**Rethink:** Document the **minimal set of tools** (generator, gallery, battle, profile, points, jobs). Then any “feature” that can be described in words should be implementable as a prompt over those tools.

### 3.4 Refactoring Toward Agent-Native

**From the skill’s refactoring angle:**

- **Identify orphan UI actions** — Anything the user can do that no agent can do. Add tools or compositions until parity.
- **Replace workflow-shaped APIs with primitives** — Where one big “do everything” endpoint exists, consider splitting into steps the agent can call (start → poll → get result).
- **Single “agent surface”** — Instead of 50+ agent route modules, consider one coherent **agent API** (e.g. MCP or single router) that exposes the capability map and lets one agent (or many) use the same tools.
- **Context injection** — Agent system prompts should receive **what exists**: list of videos, current user level, available battles, etc. So the agent can say “I see you have 3 videos; I can create another or start a battle.”

---

## 4. Structural Rethink (High Level)

### 4.1 Possible Directions

**A. Product-first simplify**  
- Pick the one core loop (e.g. “create clip → earn points → battle”).  
- Make that path excellent; put other areas in “lab” or “advanced.”  
- Reduces surface area for both users and agents.

**B. Agent-first**  
- Define the **minimal tool set** (generator, gallery, battle, profile, points).  
- Build one **orchestrator** agent that can do everything a user can do via those tools.  
- UI becomes one way to trigger the same capabilities (alternative: chat/CLI).

**C. Consolidate then expand**  
- Merge duplicate routes (e.g. many `agent_*` blueprints) into a few clear modules.  
- Single “agent gateway” that exposes the capability map.  
- Then add new features as prompts + existing tools.

**Recommendation:** Start with **C** (consolidate, one agent surface, capability map). Then decide between A (simplify product) or B (double down on agent as primary interface) based on your “one sentence” for the product.

### 4.2 Concrete Next Steps

1. **Write the one-sentence product definition** and the **capability map** (every user action → how an agent achieves it).
2. **List atomic tools** you want to support: e.g. `generator/create`, `generator/status`, `gallery/list`, `battle/start`, `battle/result`, `profile/get`, `profile/update`, `points/get`, `points/award` (or via existing triggers).
3. **Design one agent API** (e.g. under `/vidgenerator/api/agent/` or MCP) that exposes only these tools and injects context (user id, available videos, etc.).
4. **Gradually migrate** the most important user flows to use this agent API from the UI (e.g. “Create video” button could call the same tool an agent would use).
5. **Trim or archive** redundant agent blueprints and routes that don’t appear on the capability map.

---

## 5. Summary

| Lens | Outcome |
|------|---------|
| **Brainstorming** | Clarify product intent (one sentence, primary user, success metric). Use that to simplify scope and prioritize. |
| **Agent-native** | Parity (UI = agent), granularity (primitives), composability (new features = prompts). Refactor: capability map, one agent surface, context injection. |
| **Structural** | Prefer consolidate (C): one capability map, one agent API, then either simplify product (A) or go agent-first (B). |

---

## 6. Next Steps

- **Decide:** What is the one-sentence definition of Masternoder.dk?
- **Document:** Capability map (user actions → agent tools) in a single doc or table.
- **Implement:** One agent gateway + minimal tool set; then iterate from there.

If you want to go deeper on one area (e.g. generator-only, or battle-only, or full MCP design), say which and we can narrow the rethink to that slice.
