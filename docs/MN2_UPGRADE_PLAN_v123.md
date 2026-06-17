# MN2 upgrade plan — wallet v1.2.3.0 + app deploy

Last updated: **2026-06-17** (full track execution)

Related: [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) · [MN2_OPS.md](MN2_OPS.md) · [MN2_TODO.md](MN2_TODO.md) · [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md) · [CAMGIRLS_PHASE0.md](CAMGIRLS_PHASE0.md)

---

## Phase 0 — audit ✓

| Check | Result |
|-------|--------|
| GitHub CLI | ✓ `jonK341` |
| Production verify | ✓ RPC height ~914k+, reconcile + conservation green |
| Trader staking status | ✓ 200, ~152k MN2 in trader pool (post-deploy) |
| SSH (non-interactive) | ✗ stale `DEPLOY_PASS` — use `--ask-pass` for deploy/ops scripts |

---

## Phase 1 — MasterNoder2 v1.2.3.0

| Step | Status |
|------|--------|
| Source patch (mnsync + `getstakinginfo`) | ✓ [PR #1](https://github.com/jonK341/MasterNoder2/pull/1) **merged** to `main` |
| Release binaries `masternoder2d.tar.gz` | ⏳ Build on Linux — `scripts/mn2_build_release.sh` + `mn2_publish_release.py` |
| Production binary swap | ⏳ After release: `python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply` |

---

## Phase 2 — Masternoder.dk app ✓

| Item | Status |
|------|--------|
| Trader-staking status fix | ✓ Deployed (`mn2_staking`) |
| Trader pool funded | ✓ ~152k MN2 staked across 6 agents |
| Join-pool rebalance | Optional — run with ops secret if retargeting ~25k±10k each |

---

## Phase 3 — deferred + new features (code shipped, deploy `camgirls`)

| Item | Status |
|------|--------|
| Multi-source MN2 USD median | ✓ `mn2_usd_price_median()` — Chainz + config + env |
| SSE explorer tiles | ✓ `GET /api/mn2/explorer/stream` + JS EventSource |
| `explorer_use_local_stats` | ✓ Config key in `mn2_config.json` (default `false`) |
| Camgirls Phase 1a/1b | ✓ API + `/camgirls/` page + age gate + unlock/tip |
| Revive 1 masternode | Manual ops (network-wide) |

**Deploy:**

```powershell
python scripts/deploy.py camgirls --ask-pass
python scripts/deploy.py static_pages --ask-pass   # explorer SSE JS if not in camgirls manifest
```

---

## Phase 4 — Camgirls roadmap

| Phase | Status |
|-------|--------|
| 0 Spec | ✓ [CAMGIRLS_PHASE0.md](CAMGIRLS_PHASE0.md) |
| 1a Directory + MN2 unlock/tip | ✓ Code ready — deploy + add real performers via ops API |
| 1c Age gate | ✓ `POST /api/camgirls/age-verify` |
| 2 Text AI chat | ✓ Deployed — verify with `camgirls_post_deploy_verify.py` |
| 3 Voice spike | Planned |
| 4 Explorer coexistence | ✓ [CAMGIRLS_PHASE4_NGINX.md](CAMGIRLS_PHASE4_NGINX.md) — apply nginx only if moving to subdomain |

**Ops — add performer:**

```bash
curl -s -X POST -H "X-Ops-Secret: $SECRET" -H "Content-Type: application/json" \
  -d '{"id":"performer_1","display_name":"…","unlock_price_mn2":50,"payout_address":"J…","active":true}' \
  http://127.0.0.1:5000/api/camgirls/ops/performers
```

---

## Phase 5 — Discord cross-roads (code shipped, deploy `mn2_staking`)

| Item | Status |
|------|--------|
| Market fan-out → `#market` | ✓ `market_discord_fanout.py` + cron |
| Alert funnel — market/camgirls/agent types | ✓ M8 #53 |
| Affiliate rotator — market, camgirls, compendium | ✓ M8 #57 |
| Support FAQ — market, camgirls | ✓ M8 #60 |
| Trader tick → activity bus | ✓ `run_all_traders()` emit |

**Deploy:**

```powershell
python scripts/deploy.py mn2_staking --ask-pass
```

**Post-deploy:** schedule `cron/discord_market_fanout.sh` — see [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md) · [MN2_OPS.md](MN2_OPS.md) §10.

---

## Decision log

- Daemon upgrade: merge first, build release, then `--apply` (no reindex).
- Camgirls MVP on main site path first; explorer stays on `camgirls.masternoder.dk`.
- SSH ops: always `--ask-pass` until `DEPLOY_PASS` in `.env` is rotated.
