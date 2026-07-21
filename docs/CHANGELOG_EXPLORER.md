# MN2 Explorer — Changelog

Release notes for the Crypto Hub and explorer APIs. (#221)

## 2026-07-21 — P0–P6 implementation (PR #57)

### Added
- In-page tx / address / block detail routes and APIs
- Crypto Hub v2: network monitor, rich list, masternodes, search, SSE stream
- Explorer OpenAPI + `/api/docs/explorer` Swagger UI
- Post-deploy smoke (`scripts/smoke_explorer_deploy.py`) and CI workflow
- Hub deep links from profile wallet and shop revenue address

### Fixed
- `mn2_masternode` blueprint registration (`/api/mn2/services` 404)
- Chainz `$0` price filtered; ACTIVE masternodes treated as enabled
- Centralized URL builders in `mn2_explorer_urls.py`

### Ops
- Network history snapshots, probe alerts, nginx cache example
- Feature flags: `EXPLORER_HUB_V2`, `EXPLORER_HUB_V2_CANARY_PERCENT`

### Deferred
- i18n, PWA offline shell, address compare (P2)
- Webhook milestones, GraphQL, Redis cache (P1)
- Live uwsgi deploy (#168) — runbook in [EXPLORER_OPS_P4.md](EXPLORER_OPS_P4.md)

---

## Template (future releases)

```markdown
## YYYY-MM-DD — Short title

### Added
### Changed
### Fixed
### Ops
```
