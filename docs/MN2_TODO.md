# MN2 TODO

Last updated: **2026-06-17** (camgirls Phase 1c production catalog onboarded).

See [MN2_UPGRADE_PLAN_v123.md](MN2_UPGRADE_PLAN_v123.md) · [GAME_HUB_UNIFIED_25.md](GAME_HUB_UNIFIED_25.md) · [CAMGIRLS_PHASE1C.md](CAMGIRLS_PHASE1C.md)

---

## Done — deployed / verified 2026-06-17

- [x] Explorer overview + 5-day network monitor + Chainz links
- [x] Deposit self-heal, daemon policy, Health Ops Hub on `/staking-monitor`
- [x] Treasury sign-off + 600k pool funded
- [x] **`mn2_staking` deploy** — health hub, trader-staking status fix
- [x] **Trader pool** — 6 agents, ~152k MN2 staked (live)
- [x] **Trader market** — `run-market` live, cross-agent fills, `/api/market/ticker` + `/trades` ✓
- [x] **MasterNoder2 v1.2.3.0** — merged to `main` ([PR #1](https://github.com/jonK341/MasterNoder2/pull/1))
- [x] **Game Hub Option C** — all 25 ideas + phase 2 polish
- [x] **Camgirls deploy** — catalog, unlock/tip, chat, agents, `/camgirls/` page ✓
- [x] **Camgirls Phase 1c** — `performer_nova` + `performer_luna` onboarded; demos deactivated (deploy data file)

**Live:** `/news` ✓ · `/staking-monitor` ✓ · `/api/market/*` ✓ · `/camgirls/` ✓ · explorer E1 ✓ · game hub ✓

---

## Verify after deploy

```powershell
python scripts/camgirls_post_deploy_verify.py
python scripts/camgirls_post_deploy_verify.py --remote-only --ask-pass
```

After **v1.2.3.0 release binaries** — [MN2_RELEASE_BUILD.md](MN2_RELEASE_BUILD.md):

```powershell
python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply
```

---

## Camgirls platform

- [x] **Phase 0–2** — spec, catalog, MN2 rails, AI chat
- [x] **Phase 1c — Production content** — `data/camgirls_performers_production.json` (replace payout addresses per performer when ops adds real ones)
- [ ] **Phase 3 — Optional voice** — LiveKit spike on separate VPS
- [x] **Phase 4 — Explorer coexistence** — [CAMGIRLS_PHASE4_NGINX.md](CAMGIRLS_PHASE4_NGINX.md)

**Add / update performers:**

```powershell
python scripts/camgirls_onboard_performers.py --file data/camgirls_performers_production.json --dry-run
python scripts/camgirls_onboard_performers.py --file data/camgirls_performers_production.json
python scripts/deploy.py camgirls --ask-pass
```

---

## Still manual / network ops

- [ ] **Build + tag MasterNoder2 v1.2.3.0 release assets** — [MN2_RELEASE_BUILD.md](MN2_RELEASE_BUILD.md)
- [ ] **Revive / register 1 masternode** — steadier `mnsync` + pool minting
- [ ] **Rotate `DEPLOY_PASS`** in `.env` so non-interactive deploy scripts work

---

## M8 Discord — all live (2026-06-16)

Streams 51–60 deployed (role gating, promos, alert funnel, digest, quest bot, etc.).
