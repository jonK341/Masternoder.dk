# Archive

This folder holds historical, point-in-time documentation that has been superseded by later work: dated status reports, "X is now complete" task logs, one-off audits, and old plans that have already shipped or been replaced. Nothing here was deleted — it's kept for historical/forensic reference (e.g. "why did we choose this approach back in January"), but **none of it should be treated as describing the current state of the platform.**

**For current state, see:**
- [`../../PROJECT_OVERVIEW.md`](../../PROJECT_OVERVIEW.md) — single up-to-date summary of the whole platform
- [`../../docs/ROADMAP_Q3_2026.md`](../ROADMAP_Q3_2026.md) — active 3-month plan
- [`../MN2_TODO.md`](../MN2_TODO.md), [`../CASINO_TODO.md`](../CASINO_TODO.md), [`../PLATFORM_TODO.md`](../PLATFORM_TODO.md) — live, dated ops backlogs
- [`../README.md`](../README.md) — index of all current, non-archived docs

## Why these were archived (2026-07-06 cleanup)

`docs/` had grown to 282 markdown files and the repo root had 27 more, most written as one-off "TASK_X_COMPLETE.md" / "STATUS_REPORT.md" / "CLEANUP_SUMMARY.md" logs at the moment a specific fix or feature shipped — sometimes several for the same subsystem, several months apart, often contradicting the platform's actual current state (e.g. multiple root `LAUNCH_READY.md`-style files claiming the site was fully live and launch-ready with 0% errors, from January 2026, while dated ops docs from June/July 2026 tell a very different, much more current story). That volume made it effectively impossible to answer "what's actually true right now" without reading hundreds of files and manually reconciling dates.

Files were moved here (not deleted) if they matched one of:
- A filename/status marker indicating a finished, point-in-time task (`_COMPLETE`, `_FIXED`, `_RESOLVED`, `_CLOSEOUT`, `FINAL_*`, `SPRINT*`, `PHASE*_COMPLETE`, `*_TEST_RESULTS`)
- A dated status/summary/report/analysis/recap snapshot from before **2026-05-01**, once cross-checked to confirm it isn't still linked from a current doc

Evergreen reference material (API docs, OpenAPI specs, `*_GUIDE.md`, design docs, active `*_TODO.md` backlogs, and anything still linked from a current doc) was deliberately **not** archived, even if old — those stay in `docs/` alongside the still-open backlogs.

If you're looking for something that used to be at `docs/SOMETHING.md` or root `SOMETHING.md` and it's not in `docs/` anymore, it's almost certainly in this folder under the same filename.
