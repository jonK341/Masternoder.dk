# Lab V2.0 - First Slice Requirements

## Goal

Make Lab V2.0 visible, rulebook-grounded, and agent-ready without changing existing write flows. The first slice is read-only and safe to deploy: it exposes the Lab V2 rulebook, current user progression, next milestones, and Lab-specific agent knowledge readiness.

## User Outcome

Users and agents can answer: "What is Lab V2.0, where am I in it, and what should happen next?"

## First Slice

- Add dedicated Lab V2 rulebook data in `data/rulebook_lab_v2.json`.
- Add `GET /api/lab/v2/status` for V2 status, milestones, rulebook summary, agent knowledge summary, and supporting tech state.
- Keep all existing Lab V1 flows working: research, deep scan, projects, roundtable, co-tech lifecycle, profile logbook.
- Include the new rulebook and docs in `deploy.py`.

## Lab V2 Pillars

- **Rulebook rule:** Dedicated Lab V2 rulebook with agent prompt, tech spec, user guide, manual, and rules.
- **Agent knowledge:** Surface Lab-specific knowledge from existing agent knowledge storage and define what agents are allowed to do.
- **User progression:** Summarize current tier, research count, deep scans, projects, co-tech drafts, and next milestones.
- **Supporting tech:** Health/readiness for catalog, profile storage, rulebook file, agent knowledge, tools, and cross-system bridges.

## Non-Goals For First Slice

- No schema migration.
- No new mutating agent tools.
- No automatic purchases, wallet actions, or invisible point awards.
- No replacement of existing Lab UI. V2 status can be added to the UI after the endpoint is stable.

## Acceptance Checks

- `GET /api/lab/v2/status` returns `success: true` for a new/default user.
- Response includes `version`, `rulebook`, `progression`, `milestones`, `agent_knowledge`, and `tech`.
- The endpoint works when the profile database has no row for the user.
- `data/rulebook_lab_v2.json` is deployed with the app.
- Existing shop smoke and platform checks continue to pass.

## Next Slices

- Add Lab V2 panel to `/lab` using `/api/lab/v2/status`.
- Add Lab-specific agent knowledge filters to `/api/rulebooks/agent-knowledge`.
- Add Chapter V catalog nodes for Star Map bridge, shop boosters, agent-safe tools, and rulebook mastery.
- Add analytics events for research, project, roundtable, co-tech, and V2 milestone completion.
