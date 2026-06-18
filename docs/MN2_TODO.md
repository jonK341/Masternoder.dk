# MN2 TODO

Last updated: **2026-06-17** (camgirls daemon payout addresses).

See [MN2_UPGRADE_PLAN_v123.md](MN2_UPGRADE_PLAN_v123.md) · [CAMGIRLS_PHASE1C.md](CAMGIRLS_PHASE1C.md)

---

## Done — deployed / verified 2026-06-17

- [x] Explorer, staking, trader pool/market, Game Hub, camgirls platform
- [x] **Camgirls Phase 1c** — production performers; demos deactivated
- [x] **Camgirls daemon payouts** — `getnewaddress` per performer → `data/camgirls_payout_addresses.json`

**Live:** `/camgirls/` ✓ · `/staking-monitor` ✓ · `/api/market/*` ✓ · explorer E1 ✓

---

## Deploy + provision (after code pull)

```powershell
python scripts/deploy.py camgirls --ask-pass
python scripts/camgirls_provision_payout_addresses.py --remote --ask-pass
python scripts/camgirls_post_deploy_verify.py --remote-only --ask-pass
```

---

## Camgirls platform

- [x] Phase 0–2 — spec, catalog, MN2 rails, AI chat
- [x] Phase 1c — production catalog (payout via daemon, not JSON)
- [ ] Phase 3 — Optional voice (LiveKit spike)
- [x] Phase 4 — nginx guide [CAMGIRLS_PHASE4_NGINX.md](CAMGIRLS_PHASE4_NGINX.md)

---

## Still manual / network ops

- [ ] **Build + tag MasterNoder2 v1.2.3.0** — [MN2_RELEASE_BUILD.md](MN2_RELEASE_BUILD.md)
- [ ] **Revive / register 1 masternode**
- [ ] **Rotate `DEPLOY_PASS`**

---

## M8 Discord — all live (2026-06-16)

Streams 51–60 deployed.
