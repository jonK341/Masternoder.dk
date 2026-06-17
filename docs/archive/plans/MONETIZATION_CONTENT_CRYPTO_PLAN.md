<!-- ARCHIVED MONETIZATION_CONTENT_CRYPTO_PLAN.md — finished plan removed from active docs. -->

> **Archived:** 2026-06-17. Phases 1–4 implemented in repo.

# Monetized content + crypto — implementation plan (MasterNoder)

**Purpose:** Alternatives to restricted verticals: **lawful** monetized content that fits **MN2** on-chain payments and/or **PayPal → credits** already described in [MONETIZATION_PAYPAL.md](./MONETIZATION_PAYPAL.md).

**Status:** Phases **1-4 are implemented in repo**. This document is now the closeout + deploy checklist.

**Principle:** Keep **two rails** explicit — **fiat (PayPal)** for users who want cards; **MN2** for crypto-native checkout, deposits, and treasury. Attribution and margin follow the same COGS discipline as generator jobs where applicable.

---

## 1. Content & product lines (examples)


| Line                              | What you sell                                      | Crypto (MN2)                                                                                                            | Fiat (PayPal / credits)                                     | Notes                                                                      |
| --------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------- |
| **A — Generator packs**           | Credits for video/AI generation                    | Shop items priced in MN2 where implemented; deposits                                                                    | Packs in [MONETIZATION_PAYPAL §1](./MONETIZATION_PAYPAL.md) | Core product; tune `coins_per_mn2` / shop in `data/mn2_config.json`.       |
| **B — Themes & templates**        | UI themes, presets, prompt packs, export templates | One-time MN2 invoice or cart; on-chain payment + ledger                                                                 | Same catalog in points/shop                                 | Digital delivery; low marginal COGS if static files.                       |
| **C — Subscriptions**             | Monthly premium tier (higher limits, features)     | MN2 recurring is **hard** without smart contracts — use **manual renew** or **fiat subscription** + optional MN2 top-up | PayPal subscription or prepaid credits                      | Prefer one system for “subscription truth” to avoid double grants.         |
| **D — B2B / API**                 | Metered API, studio SKUs                           | SCR ledger + MN2 settlement optional ([MONETIZATION_PAYPAL](./MONETIZATION_PAYPAL.md) SCR touchpoints)                  | Invoice / PayPal                                            | Already partially in repo (`b2b_studio_skus`, ledger).                     |
| **E — Digital goods marketplace** | Asset packs, music/SFX with license, icons         | MN2 checkout per item                                                                                                   | Credits / PayPal                                            | Clear **license terms** per asset; store hashes optional for authenticity. |
| **F — Games / meta**              | Cosmetics, battle passes, Starmap boosts           | MN2 micropayments via wallet                                                                                            | Credits                                                     | Fits existing engagement JSON (`user_engagement`, etc.) if tied to SKU.    |
| **G — Education / docs**          | Courses, tutorials (PDF/video hosted by you)       | MN2 unlock                                                                                                              | PayPal unlock                                               | Gate routes or pages after payment confirmation in ledger.                 |


**Avoid mixing unclear copyright:** Only sell content you own or license.

---

## 2. Payment architecture (same stack)

```
User ──► PayPal ──► capture ──► unified credits/points ──► consumption (COGS metering)
User ──► MN2 deposit ──► ledger ──► balance ──► shop / unlock / metered job
```

- **Margin:** Use **REFERENCE_JOB_COGS** + `metering.jsonl` for anything that burns LLM/video COGS ([MONETIZATION_PAYPAL §0](./MONETIZATION_PAYPAL.md)).
- **Pure digital SKUs** (themes): price − negligible hosting = margin; track separately from generator COGS.

---

## 3. Implementation status


| Phase                    | Status   | Deliverable                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1 — Catalog + rails**  | **Done** | `payment_rails_catalog`, `digital_goods`, and rail-aware coin packs live in `[data/monetization_config.json](../data/monetization_config.json)`. Public surfaces: `GET /api/shop/config` (`monetization_shop`), `GET /api/monetization/config`, and `get_public_config()`.                                                                                    |
| **2 — Digital delivery** | **Done** | Downloadable artifacts live under `[content/digital_goods/](../content/digital_goods/)`. Public surfaces: `GET /api/shop/digital-goods` and `GET /api/shop/digital-goods/<item_id>/download`. Paid downloads are gated by shop inventory; free-info SKUs are public.                                                                                          |
| **3 — Bundles**          | **Done** | `content_bundles` combine coin/generation-credit grants with digital goods. Public surfaces: `GET /api/shop/content-bundles`, `GET /api/shop/config`, `GET /api/monetization/config`, and `GET /api/shop-v3/items` (`bundles`). Bundle purchases use the same shop checkout path and grant child digital goods into inventory.                                |
| **4 — Reporting**        | **Done** | `[backend/services/monetization_scr_blend_service.py](../backend/services/monetization_scr_blend_service.py)` reports PayPal/B2B revenue by provider, SKU line, item, user/org, rough COGS, and MN2 shop payments. CLI: `python scripts/monetization_scr_export.py --since-days 30 --json`. API: `GET /api/monetization/report` with `COGS_ADMIN_REPORT_KEY`. |


---

## 4. Ship checklist

1. **Config:** set `COGS_ADMIN_REPORT_KEY`; optionally set `MN2_USD_PRICE` for estimated crypto revenue in reports.
2. **Payments:** verify PayPal credentials, MN2 daemon RPC, and shop inventory persistence with `GET /api/shop/payment-health?probe=1`.
3. **Catalog:** call `GET /api/shop/config`, `GET /api/shop/digital-goods`, and `GET /api/shop/content-bundles`; confirm SKUs render.
4. **Purchase path:** buy one `digital_good` and one `bundle` in sandbox / local points flow; confirm inventory receives the purchased SKU and the child bundle goods.
5. **Download path:** confirm paid goods return **403** before purchase and file download after purchase.
6. **Reporting:** run `python scripts/monetization_scr_export.py --since-days 30 --json`; call `GET /api/monetization/report?since_days=30&mn2_usd_price=<price>` with the admin key.
7. **Legal/ops:** publish digital goods terms, refund policy, and crypto price disclaimer before taking real payment.

---

## 5. API summary


| Endpoint                                         | Purpose                                                                                              |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `GET /api/monetization/config`                   | Public monetization catalog: rail-aware coin packs, digital goods, bundles, subscriptions, B2B SKUs. |
| `GET /api/shop/config`                           | Shop config plus `monetization_shop` block.                                                          |
| `GET /api/shop/digital-goods`                    | Digital goods catalog with `owned`, `artifact_available`, and `download_url`.                        |
| `GET /api/shop/digital-goods/<item_id>/download` | Gated download for purchased goods; free-info goods are public.                                      |
| `GET /api/shop/content-bundles`                  | Bundle catalog with child item summaries.                                                            |
| `GET /api/shop-v3/items`                         | Normal shop catalog including `category=digital_goods` and `category=bundles`.                       |
| `GET /api/monetization/report`                   | Admin-only revenue + COGS + MN2 report.                                                              |


---

## 6. Verification

```bash
python -m pytest tests/unit/test_monetization_commits.py -q --basetemp .pytest-tmp
python -m py_compile backend/routes/shop_routes.py backend/routes/cogs_routes.py backend/services/monetization_config_service.py backend/services/monetization_scr_blend_service.py scripts/monetization_scr_export.py
```

---

## 7. Compliance & ops (high level)

- **Terms / refund:** Digital goods policy; crypto volatility disclaimer for MN2 pricing.
- **Tax / accounting:** Fiat vs crypto recognition differs by jurisdiction — accountant for DK/EU rules.
- **PayPal:** Must match **acceptable use** for each SKU category ([PAYPAL_INTEGRATION_GUIDE.md](./PAYPAL_INTEGRATION_GUIDE.md)); crypto rails bypass PayPal but not consumer law.

---

## 8. What this doc does *not* cover

Restricted industries (e.g. adult), third-party affiliate scraping, or grey-area aggregation — use lawful owned/licensed SKUs only.

---

## 9. References

- [MONETIZATION_PAYPAL.md](./MONETIZATION_PAYPAL.md) — packs, COGS, SCR/B2B.
- [MN2_OPS.md](./MN2_OPS.md) — daemon, deposits, withdrawals.
- [MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](./MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md) — explorer links, phases.

