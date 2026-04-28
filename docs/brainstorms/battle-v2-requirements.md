---
date: 2026-04-28
topic: battle-v2
---

# Battle V2.0 Requirements

## Problem Frame

The Battle page currently has working functions, but progress is spread across quick battle stats, battle history, tournaments, clans, trophies, lab tech, and profile data. V2.0 should make the page feel like one competitive system where every meaningful action belongs to the current `user_id` and can be summarized from one progress contract.

---

## Actors

- A1. Player: uses the Battle page to fight, join social competition, create lab tech, and track profile progress.
- A2. Profile system: owns stable `user_id` identity, points, inventory, lab logbook, and profile display.
- A3. Battle services: record matches, points, trophies, social memberships, and competitive status.
- A4. Agents: act as selected battle/lab partners and should be attached to a player-owned action, not replace the player identity.

---

## Key Flows

- F1. Quick battle progress
  - **Trigger:** Player starts or queues a quick battle.
  - **Actors:** A1, A2, A3
  - **Steps:** Resolve `user_id`, execute battle, write points/win-loss/draw/streak, record history when storage is available, return updated progress.
  - **Outcome:** Profile, Battle stats, leaderboard, trophies, and history agree for the same player.
  - **Covered by:** R1, R2, R3, R4

- F2. Social battle progress
  - **Trigger:** Player joins a tournament or clan.
  - **Actors:** A1, A3, A4
  - **Steps:** Resolve `user_id`, store tournament participation by user, store clan membership as user plus selected agent, expose membership in Battle progress.
  - **Outcome:** Agents can be part of a battle team without losing the player ownership trail.
  - **Covered by:** R1, R5, R6

- F3. V2.0 readiness review
  - **Trigger:** Player opens the System tab.
  - **Actors:** A1, A2, A3
  - **Steps:** Load the Battle progress contract, show completion lanes, and show missing V2.0 gaps.
  - **Outcome:** The page itself explains what progress exists and what still needs to be built.
  - **Covered by:** R7, R8

---

## Requirements

**User-Owned Progress**
- R1. Every Battle action that changes progress must resolve a `user_id` and include that `user_id` in the response.
- R2. Quick battle outcomes must update `battle_points`, wins, losses, draws, and streaks for the resolved user.
- R3. Battle history must be readable by `user_id`, with empty history treated as a storage/configuration gap rather than a UI failure.
- R4. Trophies must be derived from the user’s actual battle stats until a dedicated trophy ledger exists.
- R5. Tournament participation must remain user-owned.
- R6. Clan membership must include the player `user_id` and the selected agent identity.

**V2.0 Interface**
- R7. The Battle page must expose a single progress summary that covers stats, history, resources, trophies, social progress, leaderboard rank, and lab progress.
- R8. The System tab must show both current progress and the explicit V2.0 missing list.
- R9. Lab tech created from Battle must use the same profile identity as Battle and Profile.

**V2.0 Backlog**
- R10. Replace template fantasy resources with an earned/spent per-user ledger. **Status:** first slice implemented for Quick Battle rewards.
- R11. Add dedicated season progress instead of using global leaderboard aliases. **Status:** first slice implemented for per-user season score.
- R12. Add per-match telemetry for battle intelligence beyond summary stats. **Status:** first slice implemented for Quick Battle events.
- R13. Add Battle crypto earning options that award internal `mn2_balance` with requirements, cooldowns, and claim history. **Status:** first slice implemented.
- R14. Add durable progress for agent-vs-agent battles if they return as a primary Battle page action.
- R15. Add richer reward previews for tournaments, clans, and streaks.

---

## Acceptance Examples

- AE1. **Covers R1, R2, R7.** Given `game_user_id = jane`, when Jane starts Quick Battle, the Battle progress summary for `jane` shows updated battle stats and points.
- AE2. **Covers R5, R6.** Given Jane selects `agent_alpha` and joins a clan, the membership is visible under Jane’s Battle progress and still records `agent_alpha` as the agent partner.
- AE3. **Covers R8.** Given no season ledger exists, when Jane opens the System tab, the missing list names season progress as a V2.0 gap.

---

## Success Criteria

- A player can answer “what have I progressed in Battle?” from one Battle page area.
- Profile, Battle, Lab, and points data agree on the same current `user_id`.
- A downstream implementer can use this document to plan V2.0 without inventing scope.

---

## Scope Boundaries

- Do not rebuild Profile, Lab, or Shop inside Battle; Battle should summarize and deep-link to those systems.
- Do not make agents the owner of player progress; agents are attached context under the player identity.
- Do not treat cosmetic shop themes as Battle progression unless backend rules explicitly connect them.
- Full multiplayer matchmaking is not required for the V2.0 progress contract.
- Battle crypto earnings are internal MN2 balance claims, not direct on-chain transfers.

---

## Key Decisions

- Battle V2.0 should extend existing unified points/profile patterns rather than introduce a separate identity layer.
- The first V2.0 slice should be a user-scoped progress contract, because it gives the UI and future agents one source of truth.
- The page should surface missing work directly, so future upgrades are visible from the product surface.
- Crypto earning should mirror the Star Map 25 model: user-scoped claim options, cooldowns, claim history, and internal MN2 balance awards.

---

## Dependencies / Assumptions

- `battle_matches` may not exist or may be empty in some environments, so history must remain optional.
- Unified points remain the source of truth for Battle points and simple leaderboard fallback.
- Lab technology drafts require the hunters profile database.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R10][Technical] Should battle resources live in unified points, a Battle ledger, or the existing profile JSON?
- [Affects R11][Technical] Should seasons snapshot scores or partition all battle events by season id?
- [Affects R12][Technical] Which telemetry fields are worth storing per match without creating noisy analytics?

---

## Next Steps

-> Plan and implement the V2.0 backlog in slices: progress contract first, then resource ledger, season ledger, and telemetry.
