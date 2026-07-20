## Summary

<!-- What changed and why -->

## Test plan

- [ ] Unit tests: `python3 -m pytest tests/unit/…`
- [ ] Explorer smoke (if MN2/explorer touched): `python scripts/smoke_explorer_deploy.py`

## Post-deploy checklist (explorer / MN2)

- [ ] `python scripts/deploy.py mn2_staking static_pages [--mn2_env] --ask-pass`
- [ ] `POST_DEPLOY_BASE_URL=https://<site> python scripts/smoke_explorer_deploy.py`
- [ ] `curl -sS …/api/mn2/services` — explorer service present
- [ ] `curl -sS …/api/mn2/explorer/status` — `healthy` or `degraded` (not unreachable)
- [ ] Browser: `/explorer/` hard refresh; tx/address/block detail pages load
- [ ] Purge CDN cache for `/static/js/mn2-*` if applicable
- [ ] Optional: `python scripts/mn2_explorer_probe_alert.py --force-alert` (Discord)

See [docs/EXPLORER_OPS_P4.md](docs/EXPLORER_OPS_P4.md) for full ops runbook.
