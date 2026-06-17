# MN2 integration — what's missing

Gap list vs the [archived integration plan](archive/plans/MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md) and [MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md). **Phases 1–7** and §8.3 items are implemented; Phase 7 closed the previously listed gaps.

---

## 1. Security / ops (Phase 7 — done)

| Gap | Status |
|-----|--------|
| **Scan-deposits** | If `MN2_SCAN_SECRET` is set, endpoint requires `X-Scanner-Token` or `?token=`. Set it in production (see MN2_OPS). |
| **Min/max withdrawal** | **Done:** `min_withdrawal`, `max_withdrawal` in `data/mn2_config.json`; enforced in withdraw route. |

---

## 2. Optional features (Phase 7 — done)

| Feature | Status |
|----------|--------|
| **Chainz health fallback** | **Done:** `/api/health/system` uses Chainz `getblockcount` when RPC is unreachable (`backend/services/mn2_chainz.py`). |
| **Chainz ticker.usd** | **Done:** Cached in `mn2_chainz.py`; `/api/mn2/balance` returns `mn2_usd_price` when available. |
| **Theme_premium / landing "Pay with MN2"** | **Done:** Badge/link on `theme_premium/index.html` and root `index.html` (nav) linking to `/shop`. |
| **Withdrawal duration in ledger** | **Done:** `withdrawal_duration_ms` in ledger metadata for each withdrawal. |
| **Admin ops/stats** | **Done:** `GET /api/mn2/ops/stats` (scanner runs + RPC summary); protected by `MN2_OPS_SECRET` or `MN2_SCAN_SECRET` when set. |

---

## 3. Documentation / naming (Phase 7 — done)

| Item | Status |
|------|--------|
| **Plan typo** | **Done:** `mastercoder2d` → `masternoder2d` (and conf/cli) in MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md. |
| **Reconciliation script** | **Done:** `scripts/mn2_reconcile.py` (ledger net vs optional RPC `getbalance`). |

---

## 4. Implemented (no gap)

- Phase 1–6: RPC, wallet, ledger, scanner, withdraw, shop, UI.
- **Phase 7:** Min/max withdrawal, Chainz fallback + ticker.usd, "Pay with MN2" badge (theme_premium + landing), withdrawal_duration_ms in ledger, GET /api/mn2/ops/stats, scripts/mn2_reconcile.py, scan/ops secrets, plan typo fix.
- Testnet, MN2_OPS.md, AGENTS_MN2.md.

---

## 5. Optional next steps (low priority)

- Set `MN2_SCAN_SECRET` and (optionally) `MN2_OPS_SECRET` in production; use token in cron for scan-deposits and when calling ops/stats.
- Tune `min_withdrawal` / `max_withdrawal` in `data/mn2_config.json` if needed.
