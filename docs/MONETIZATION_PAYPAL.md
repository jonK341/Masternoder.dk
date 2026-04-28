# PayPal-aligned monetization (MasterNoder)

**Purpose:** Map **revenue models** to MasterNoder’s stack: PayPal capture → grant credits/points, **COGS**-aware pricing, and phased rollout.

**Contents:** [§0 Single metric](#0-single-metric-north-star) · [§1–5 Revenue models](#1-coin--credit-packs-one-time) · [§6 Cross-cutting](#6-cross-cutting-all-models) · [§7 Checklist](#7-checklist-product--engineering) · [§8 Playbook](#8-execution-playbook-step-by-step) · [§9 Deploy](#9-deploy-checklist) · [§10 Status](#10-implementation-status--next-steps)

**Related:** [REFERENCE_JOB_COGS.md](./REFERENCE_JOB_COGS.md) (unit economics), [PAYPAL_INTEGRATION_GUIDE.md](./PAYPAL_INTEGRATION_GUIDE.md) (credentials and routes), [VIDEO_STORAGE_STRATEGY.md](./VIDEO_STORAGE_STRATEGY.md) (storage path and margin), [MONETIZATION_INVESTIGATION_CLOSEOUT.md](./MONETIZATION_INVESTIGATION_CLOSEOUT.md) (closeout + deploy).

---

## 0. Single metric (north star)

*(Same block as [MONETIZATION_INVESTIGATION_CLOSEOUT.md §0](./MONETIZATION_INVESTIGATION_CLOSEOUT.md#0-single-metric-north-star) — edit both when changing.)*

Review **one** headline number each week so the rest of this doc does not sprawl into dozens of KPIs.

### Headline KPI (pick one phase — then stick to it)

| Phase | Primary metric | How to get it |
|-------|----------------|---------------|
| **A — COGS honest** (now) | **Median `ratio_vs_reference_job`** over the last **7 days** in `metering.jsonl` | `python scripts/cogs_metering_report.py` or inspect rows; compare to [REFERENCE_JOB_COGS.md](./REFERENCE_JOB_COGS.md). Typical healthy band **~0.7–1.5** while the product mix stabilises — **investigate** sustained drift outside that band. |
| **B — Growth** | **Activation rate:** % of new accounts with **≥1** completed **`rich_video`** within **7 days** of signup | Join signup time → first successful job (`job_kind` / job store). Pairs with [§8.5](#85-growth-global-not-dk-only). |
| **C — Paid** (packs/subs live) | **Blended gross margin on paid usage:** revenue attributed to billable jobs **minus** Σ `cogs_usd.total_usd` for those jobs, divided by revenue | **Beyond raw metering:** `metering.jsonl` gives **COGS per `job_id`**, not **which dollars** paid for which jobs. Phase **C** needs **revenue ↔ `job_id`** (or defensible user-period rollups) via **ledger + grants + subscription cycles** — see §10 **Attribution**. |

**Rule:** use **phase A** until real **`COGS_*`** from invoices and stable jobs exist; add **B** when acquisition matters; switch headline to **C** once PayPal/Stripe revenue is tied to usage.

### Two-line progress lens

| Track | Typical state (early 2026) |
|-------|----------------------------|
| **Measurement & COGS rails** | **Advanced** — LLM usage into metering, p50/p90 report, optional admin stats API. |
| **Monetised product surface** | **Early → mid** — packs, tiers (flagged), subs + shop, **SCR** ledger are **in repo**; **§8.2–8.5** roadmap: **habit loops** (no **automated** usage-vs-allowance nudges), **paid queue** (no **separate** subsystem; optional **`priority_tier`** future), **metered B2B API**. |

---

**Code touchpoints (non-exhaustive):**

| Area | Location |
|------|----------|
| PayPal OAuth, create/capture | `backend/services/paypal_service.py` |
| HTTP routes | `backend/routes/paypal_routes.py` |
| Shop / coins / PayPal items | `backend/routes/shop_routes.py` |
| Unified points | `backend/services/unified_points_database.py` |
| COGS reference + metering | `backend/services/cogs_metering_service.py`, `logs/cogs/metering.jsonl`, `scripts/cogs_metering_report.py` |
| LLM usage aggregation (per job) | `backend/services/llm_service.py`, `backend/services/video_ai_bridge.py` |
| Metering stats API (admin key) | `GET /api/system/cogs/metering-stats` — env `COGS_ADMIN_REPORT_KEY` |
| SCR (B2B SKUs + ledger + manual cash line) | `data/monetization_config.json` (`b2b_studio_skus`), `monetization_ledger_service.append_payment_event`, `POST /api/monetization/b2b/record-payment` — env `B2B_LEDGER_SECRET`; optional org pool `monetization_org_pool_service` + env `MONETIZATION_ORG_POOL_ENFORCEMENT`; CSV export `python scripts/scr_usage_export.py` |
| Purchase notifications | `backend/services/purchase_notification_service.py` |

---

## 1. Coin / credit packs (one-time)

### What it is

Users pay a fixed **USD** amount once; you grant **credits** that map to generations (or internal currency the shop/generator already uses). This is a **prepaid wallet**: cash upfront, consumption later.

### Why it’s high leverage

- **Fast to ship:** Create → approve → **capture** and post-capture granting already exist (`paypal_routes` + unified points).
- **Easy to experiment:** Adjust pack sizes and prices without re-architecting the video pipeline.
- **Cash upfront:** Improves cash flow versus pure post-usage billing.

### Tie-in to economics

Use the **reference job** (`GET /api/system/cogs/reference-job`) and **`metering.jsonl`** as anchors: decide how many reference-equivalent generations a pack should cover, then add **margin** on top (see [REFERENCE_JOB_COGS.md §4](./REFERENCE_JOB_COGS.md) — gross margin target, minimum retail).

Packs can be labeled in friendly units (“**N standard generations**”) while internally you deduct **credits** proportional to **actual** COGS per job (longer video, more Runway seconds, heavier encode → more credits).

### Product decisions

- **Expiry:** none vs 12 months (affects liability and perceived value).
- **Refunds:** partial vs none after some usage (support load).
- **Bonuses:** e.g. “$20 pack = $22 credit” to lift average order value.

### A/B testing

Test **price points** (e.g. entry tier vs mid tier), **bonus percentages**, and **default highlighted pack** in the UI. Measure **conversion**, **repeat purchase**, and **credit burn rate** (granted vs used).

### Risks

Aggressive discounts attract **one-time bargain hunters**. Mitigate with **soft caps** on cheap first-time packs and clear **receipts** / notifications (see `purchase_notification_service`).

---

## 2. Premium generation tiers

### What it is

Different **classes of output** carry different **prices or credit costs**: resolution, length, watermark, model tier, segment count, **priority** queue, etc. Each premium bump can be:

- **Credits only** (deduct more credits for HD), or  
- **PayPal per action** (small order per job or per unlock), or  
- **Hybrid:** credits for standard; PayPal for overage.

### Why it’s high leverage

Margin is not flat: **COGS varies** with Runway seconds, encode time, LLM tokens, storage (`cogs_metering_service`). Tiers let you **charge where cost spikes** instead of subsidizing heavy users with light ones.

### How it maps to the stack

- **Metering** exposes **`ratio_vs_reference_job`** — use it to define tier boundaries (e.g. “Pro” = jobs above X× reference).
- **PayPal:** one order per premium unlock, or one checkout for a bundle of options before render. [PAYPAL_INTEGRATION_GUIDE.md](./PAYPAL_INTEGRATION_GUIDE.md) sketches **agent-triggered** orders for premium actions (confirm price → pay → run pipeline).

### Design pattern

Prefer **3–4 clear tiers** in the UI (e.g. Standard / HD / Long / Studio) with **predictable** credit or dollar prices. Avoid many micro-options that confuse checkout.

### Risks

**Surprise bills** if PayPal is charged mid-flow — show **final price before** redirect. For credits-only tiers, avoid opaque “dynamic pricing” without a clear **estimate** before render.

---

## 3. Subscriptions (recurring)

### What it is

A **recurring PayPal plan** (Subscriptions API) for a **monthly allowance:** credits, features, or both — e.g. “Pro: 20 generations/month + priority + no watermark.”

### Why LTV can beat one-off packs

Predictable **MRR**, faster **payback** on acquisition if users stay, and habit formation. One-off packs fit **spiky** or **trial** users better.

### Product decisions (before building)

- **Allowance:** fixed credits/month vs “up to N reference jobs” vs feature flags only.
- **Rollover:** unused credits roll or expire (rollover increases perceived value; adds accounting complexity).
- **Downgrade / cancel:** grace until period end is a common pattern.

### PayPal-specific

Plans, billing cycles, failed payment retries, and **webhooks** for subscription lifecycle events — **server-side** state is required, not only client redirect success.

### Implementation (this repo)

1. **Config:** `data/monetization_config.json` → **`subscriptions.plans`**: keys are PayPal **billing plan ids** (`P-…`), values include **`monthly_generation_credits`**, optional **`monthly_coins_granted`**, optional **`price_usd_monthly`** (display), optional **`tier`** (`creator` \| `pro`).
2. **Start checkout:** `POST /api/monetization/subscription/create` with JSON `{ "plan_id": "P-…", "user_id": "…" }` (omit **`plan_id`** if exactly one plan exists). Returns **`approve_url`** — same PayPal OAuth app as coin packs. **Shop → PayPal & coins** lists plans from **`GET /api/monetization/config`**.
3. **Bind after return:** PayPal redirects to **`/shop?paypal_subscription=success&subscription_id=…&plan_id=…&user_id=…`**; the page calls **`POST /api/monetization/subscription/bind`**. Writes **`logs/monetization/subscription_bindings.json`** ( **`custom_id`** on the subscription is also **`user_id`** for webhook auto-bind).
4. **Webhook URL (PayPal dashboard):** `POST /api/monetization/webhooks/paypal-subscription`. Set **`PAYPAL_WEBHOOK_ID`** from the same app as **`PAYPAL_CLIENT_ID`** / **`PAYPAL_CLIENT_SECRET`**. Optional **`PAYPAL_WEBHOOK_BYPASS=1`** for local testing only (never in production).
5. **Events:** **`PAYMENT.SALE.COMPLETED`** grants monthly coins + ledger row + optional **profile `monetization_tier`** when **`tier`** is set. **`BILLING.SUBSCRIPTION.ACTIVATED`** can auto-bind if **`custom_id`** on the subscription equals **`user_id`**. **`BILLING.SUBSCRIPTION.CANCELLED`** sets tier back to **creator** (best effort).
6. **Idempotency:** webhook event ids in **`logs/monetization/paypal_webhook_processed_ids.jsonl`**.

### Fit for MasterNoder

Strong if **core users** generate **weekly**; weaker if traffic is mostly **one-off** — then packs + tiers ship faster.

### Risks

**Churn** and disputes on “didn’t use it this month.” Mitigate with clear **terms**, easy **cancel**, and **reminders** before renewal.

---

## 4. Lion’s share: the studio cash dream (B2B / teams)

### The dream (why this section exists)

Retail packs are **oxygen** — they keep the lights on and teach you pricing. The **lion’s share** of durable software money, for a generator like MasterNoder, usually lives **above** the $4.99 impulse line: **teams** that need **volume**, **predictability**, and **someone to invoice**. The dream is not “we also do B2B.” The dream is **lining the business with chunks of cash** that are large enough to **fund roadmap and infra** while **metering proves margin** on every job — same physics as §1–3, different **ticket size** and **contract shape**.

### What it is (still plain English)

Selling to **agencies, comms, education, studios, internal creative teams**: **prepaid generation blocks**, **monthly minimums**, **annual commits**, **invoice + bank + PayPal deposit**, optional **shared org workspace**. You are selling **outcomes and runway** (batch workflows, brand-safe outputs, priority, reporting) — not only “a video.”

### Why this can beat microtransactions on *dollars per hour of founder time*

- **Fewer, larger payers** → less relative overhead (support per dollar, payment friction).
- **Contractual caps** align with **COGS** planning ([REFERENCE_JOB_COGS.md](./REFERENCE_JOB_COGS.md)) instead of hoping usage stays flat.
- **Same engine** as retail: **PayPal** or **invoice** still ends up as **attributed revenue** you can join to **`metering.jsonl`** for phase **C** margin ([§0](#0-single-metric-north-star)).

---

### Fresh engineering solution: **Studio Cash Rail (SCR)**

SCR is a **single pattern** — not a second product — so B2B does not fork the pipeline.

| Layer | Job | How it maps to the repo (today → next) |
|-------|-----|----------------------------------------|
| **1 — Quote** | Turn **reference job cost × expected usage × term × seats** into **named SKUs** so nobody invents prices in DMs. | **Shipped:** **`data/monetization_config.json`** → **`b2b_studio_skus.skus`**; exposed read-only on **`GET /api/monetization/config`** as **`b2b_studio_skus`**. |
| **2 — Cash** | Every inbound **USD/EUR** event gets **one append-only row** with **deal metadata** — **`logs/monetization/payment_ledger.jsonl`**, with **`deal_kind`**, **`invoice_ref`**, **`org_label`**, **`studio_sku_id`** (plus existing PayPal / subscription ids). | **Shipped:** ledger columns + **`POST /api/monetization/b2b/record-payment`** (env **`B2B_LEDGER_SECRET`**, header **`X-B2B-Ledger-Key`**) for wire / invoice / manual settlement lines (`provider`: **`b2b_scr`**). |
| **3 — Burn** | **Same jobs, same `metering.jsonl`** as consumer traffic. Entitlement is **balance + period** (credits or tier) keyed by **`user_id`** or **`org_label`** on jobs (config / profile) — generation **measures** COGS per job; optional **org pool** enforcement blocks starts when **ledger credits in − metering burn out** falls below a per-job reserve. | **Do not** build a second video stack. Enforce **tier/credits** the same way as §2; **SCR** answers “**who prepaid** and **which deal** funded this quarter’s burn.” **`org_label`** is written to **`metering.jsonl`** when `scr_org_label` / profile prefs are set. |

**PayPal’s role in SCR:** **Deposit + top-up** and **business subscription** where it fits; **wire / invoice** for renewals once trust exists — all layer-2 **cash events** with a **reference** that lands in the ledger.

**Operations (lightweight):** a **CRM row** per prospect, **order/invoice references** on every payment, **usage export** — run **`python scripts/scr_usage_export.py`** (writes `metering_jobs.csv`, `ledger_scr.csv`, `org_pool_summary.csv` under `exports/` by default; phase **C** margin joins). Legal: **MSA/DPA** when EU processing applies.

### Risks (unchanged in nature)

Long **sales cycles** — keep **consumer packs + subs** live while the **lion lane** matures. The dream fails if B2B becomes **custom consulting** without **SKU discipline**; SCR exists to prevent that.

---

## 5. Marketplace-style (later)

### What it is

**Two-sided:** creators supply templates/assets; buyers pay; platform takes a **fee**; **payouts** to creators (PayPal **Payouts** or other rails).

### Why defer

- Need **supply** and **quality** before liquidity.  
- **Tax / compliance** (e.g. reporting obligations depending on jurisdiction), **KYC**, buyer–seller **disputes**.  
- **Support** scales with bad listings or IP issues.

### When it becomes core

If the differentiator is a **creator library** or **economy around the generator** — not while proving **single-player** demand.

### PayPal Payouts

Use when **volume**, **payout rules**, and **compliance** are in place — not as the first monetization experiment.

---

## 6. Cross-cutting (all models)

1. **Anchor retail to COGS** using the reference job + median actuals in `metering.jsonl` ([REFERENCE_JOB_COGS.md §4](./REFERENCE_JOB_COGS.md)).  
2. **PayPal** collects cash; **margin** = price − COGS − fees − support − failed payments.  
3. **Recommended rollout:** **packs + tiers** first (fast iteration) → **subscriptions** when repeat use is proven → **B2B** in parallel if you have leads → **marketplace** only as a deliberate phase-2 business model.  
4. **Weekly review:** one headline KPI from [§0](#0-single-metric-north-star) — do not dilute with too many parallel metrics.

---

## 7. Checklist (product + engineering)

**Detailed steps:** [§8 Execution playbook](#8-execution-playbook-step-by-step).

| Priority | Action |
|----------|--------|
| P0 | Live PayPal credentials, return URLs, test capture → grant path ([PAYPAL_INTEGRATION_GUIDE.md](./PAYPAL_INTEGRATION_GUIDE.md)). |
| P0 | Define credit ↔ reference job (or COGS multiple) so packs are defensible. |
| P1 | Shop/UI: clear packs, receipts, support contact. |
| P1 | Tier table: credit or USD price per tier; gate pipeline by tier. |
| P2 | Subscriptions API + webhooks + allowance accounting. |
| P2 | **SCR:** ~~config + ledger + `record-payment`~~ **done**; ~~usage export (`scripts/scr_usage_export.py`)~~ **done**; ~~optional org pool enforcement~~ **done** (`MONETIZATION_ORG_POOL_ENFORCEMENT`, `scr_org_label` on API + profile). |
| P3 | Marketplace: payouts, policies, supply onboarding. |

---

## 8. Execution playbook (step-by-step)

Concrete steps that sit **on top of** the revenue models above: instrumentation, caps, retention, infra, B2B, growth, and a **this-week** slice.

### 8.1 Unit economics and pricing

| Step | Action |
|------|--------|
| 1 | **Wire real LLM usage.** ✅ *Shipped:* `video_ai_bridge` accumulates `LLMResponse.usage` into `config["_llm_usage_totals"]`; rich-video completion merges **`llm_tokens_actual`** into `_video_cogs_metrics`; `record_completed_video_job` writes **`llm_tokens_source`** (`actual` \| `heuristic`) and **`llm_tokens_for_cogs`** to `metering.jsonl`. Code: `llm_service.accumulate_llm_usage_from_response`, `video_generator_service._run_video_generation_impl`. |
| 2 | **Dashboard from `metering.jsonl`.** ✅ *Shipped:* `python scripts/cogs_metering_report.py` and `summarize_metering_jsonl()`; optional **`GET /api/system/cogs/metering-stats`** with **`COGS_ADMIN_REPORT_KEY`** + header **`X-Cogs-Admin-Key`**. Reports **p50 / p90** totals, line items, **`ratio_vs_reference_job`**. Use **p90** for subscription caps. See [MONETIZATION_INVESTIGATION_CLOSEOUT.md](./MONETIZATION_INVESTIGATION_CLOSEOUT.md). |
| 3 | **Tiered limits.** Map product names (e.g. **Creator / Pro**) to **hard caps**: max **Runway** output seconds per job or per month, max **output MB/month**, max **LLM tokens** per job or per billing period. **Enforce before starting jobs** (reject or upsell). Same mental model as [REFERENCE_JOB_COGS.md](./REFERENCE_JOB_COGS.md); caps are the retail side of COGS. |

### 8.2 Product and retention

Keep users **paying and generating** without surprise churn. Three layers: **what they buy**, **how honestly you describe usage**, **how you remind them before renewal**.

| Step | Action | Status |
|------|--------|--------|
| 1 | **Subscription SKUs.** Recurring billing aligned to **included generations** (or reference-equivalent credits) per month; **overage** priced **above** blended COGS from metering (never below). | **Partial — shipped:** PayPal **Subscriptions** end-to-end: **`POST /api/monetization/subscription/create`**, bind, webhooks, monthly grant from **`subscriptions.plans`**; shop **Pro** block. **Remaining:** real **plan ids**, copy, optional **Stripe** if you need EU card mix; define **overage** policy in product + pricing. |
| 2 | **Credit packs + reference honesty.** Sell **generation credits** tied to **reference fractions** (`credit_definition.reference_fraction_per_credit` in **`data/monetization_config.json`**) so prices stay defensible when **job mix** shifts. | **Partial — shipped:** packs + **`generation_credits_granted`** on packs; **`GET /api/monetization/config`**. **Remaining:** surface “**≈ N ref-eq generations**” in shop copy; revisit fraction when the **canonical reference job** changes ([REFERENCE_JOB_COGS.md](./REFERENCE_JOB_COGS.md)). |
| 3 | **Habit loops.** Before renewal: **in-app** or **email** — e.g. “You used **~X%** of your monthly allowance (metered vs cap).” Reduces **surprise churn** and supports **fair upsell**. | **Not shipped** as **automated** nudges (no scheduler + **usage vs allowance** messaging pipeline). **Roadmap:** scheduled messaging + aggregation. **Input data exists:** tier caps ([§2](#2-premium-generation-tiers)), metering rows. |

**Design rule:** retention nudges should cite **measured** usage where possible (metering / caps), not vanity counts — aligns with trust and §0 phase **B/C**.

---

### 8.3 Technical reliability and margin

Protect **margin under failure and load**: storage truth, **fair** prioritisation, and **observable** provider paths.

| Step | Action | Status |
|------|--------|--------|
| 1 | **Storage path.** **Upload then delete local** where applicable so **storage COGS** and disk reality match; avoid silent **free** local retention that poisons margin math. | **Process + doc:** follow [VIDEO_STORAGE_STRATEGY.md](./VIDEO_STORAGE_STRATEGY.md). Treat as **operational** checklist on every deploy that touches paths or CDN. |
| 2 | **Queue + priority.** **Paid / subscribed** users should not lose to **free** traffic when the system is busy — **encode / job ordering** favours revenue. | **Not** a **separate** subsystem in this repo (no dedicated paid queue service). **Partial mitigation:** tier **enforcement** ([§2](#2-premium-generation-tiers)) rejects **oversized** jobs before expensive work. **Future:** optional **`priority_tier`** (or similar) on the job runner + `MONETIZATION_*` / subscription flag — **not** shipped. |
| 3 | **Provider fallbacks.** When a **provider** fails or rate-limits, fall back to the next acceptable path; **log** which path ran so **COGS** and **pricing by path** stay honest. | **Partial — LLM:** `llm_service` routes by **task_type** and **circuit breakers**; usage lands in metering via **`llm_tokens_source`**. **Video / Runway / external APIs:** ensure **provider** (or path id) is **consistent on `metering.jsonl` rows** when you add alternates — **pricing by path** in §6 depends on it. |

---

### 8.4 B2B and API

Same **COGS** and **same jobs** as retail; difference is **ticket size**, **invoice discipline**, and **contract language**.

| Step | Action | Status |
|------|--------|--------|
| 1 | **Studio Cash Rail (cash + SKU).** Named **B2B SKUs** in config; **manual cash** lines via **`POST /api/monetization/b2b/record-payment`** ( **`B2B_LEDGER_SECRET`** ); ledger fields **`deal_kind`**, **`invoice_ref`**, **`org_label`**, **`studio_sku_id`**. | **Shipped:** [§4](#4-lions-share-the-studio-cash-dream-b2b--teams), **`b2b_studio_skus`**, **`payment_ledger.jsonl`**, **`python scripts/scr_usage_export.py`** (ledger + metering CSVs), optional **`MONETIZATION_ORG_POOL_ENFORCEMENT`** + **`scr_org_label`** / profile **`scr_org_label`** (metering rows tagged with **`org_label`**). |
| 2 | **Metered API keys (future).** Per-org **API keys** with `job_id` in every request; **invoice** and **disputes** use **metering** + ledger as **source of truth** (same fields as internal UI). | **Roadmap:** auth + rate limits + **key → org → user** mapping; **no** duplicate COGS pipeline — reuse **`cogs_metering_service`** outputs. |
| 3 | **SLA tier (pricing).** **Annual** contracts should **explicitly** fund a **higher** assumed **`COGS_ENCODE_CPU`** / host footprint — **prepay + price**, not “hope we stay under.” | **Process:** model in spreadsheet from **reference job** + **p90** from [§8.1](#81-unit-economics-and-pricing); encode **floor** in **`b2b_studio_skus`** list prices or side letter. |

---

### 8.5 Growth (global, not DK-only)

**DK** is one market; **payment rails** (PayPal, bank, later cards) and **language** should not trap you in a single geography.

| Step | Action | Status |
|------|--------|--------|
| 1 | **One landing + one funnel metric.** Single **primary CTA** (e.g. signup → **first video**). Track **cost per activation** vs **LTV** from packs + subs + tiers. | **Process:** align the **headline KPI** with [§0 phase B or C](#0-single-metric-north-star). **Product:** English-first landing is fine; **pricing** in USD on PayPal already supports **global** buyers. |
| 2 | **Partner experiments (discipline).** **Ads credits**, **cloud credits**, **influencer** codes — run as **time-boxed** experiments with a **stop rule** (e.g. CAC vs LTV after **N** weeks). | **Rule:** **core margin** from **priced usage** (credits, subscriptions, SCR deals), **not** from perpetual **free** inference — **LLM_PREFER_FREE**-style modes are for **dev/test**, not the default paid story. |
| 3 | **Support and expectations.** Global users = **async** support, clear **SLA** (e.g. “best effort 48h”), **refund** policy in line with **PayPal** and local **consumer** rules. | **Process:** link from checkout and profile; reduces chargebacks and disputes that **erase** margin. |

---

### 8.6 Quick wins this week

1. Set **real `COGS_*`** in `.env` from **last month’s invoices** (see [REFERENCE_JOB_COGS.md](./REFERENCE_JOB_COGS.md) §2).  
2. Run **10 real jobs**, inspect `logs/cogs/metering.jsonl`, and **adjust reference assumptions** in `REFERENCE_JOB_SPEC` if the **median** job materially differs from the reference.  
3. Pick **one subscription price** using a **reference-sized** allowance: shorthand **`reference_total_usd × jobs_per_month × (1 + markup)`** if you think in **markup on COGS** (e.g. 1.5× cost). For **gross margin** targets, match [REFERENCE_JOB_COGS.md §4](./REFERENCE_JOB_COGS.md): **minimum retail per job** = `reference_total_usd / (1 - gross_margin)` → **monthly floor** ≈ `jobs_per_month × reference_total_usd / (1 - gross_margin)` (then add PayPal fees and ops).

---

## 9. Deploy checklist

*(Duplicated from [MONETIZATION_INVESTIGATION_CLOSEOUT.md](./MONETIZATION_INVESTIGATION_CLOSEOUT.md) — keep both sections in sync when editing.)*

### Minimum (required for COGS + LLM metering + monetization commits)

Deploy these paths to the app root (e.g. `/var/www/html/` on the server):

| # | Path |
|---|------|
| 1 | `backend/services/cogs_metering_service.py` |
| 2 | `backend/services/video_ai_bridge.py` |
| 3 | `backend/services/llm_service.py` |
| 4 | `backend/services/video_generator_service.py` |
| 5 | `backend/routes/cogs_routes.py` |
| 6 | `backend/services/monetization_config_service.py`, `monetization_ledger_service.py`, `monetization_tier_service.py`, `paypal_service.py`, `paypal_webhook_service.py`, `monetization_subscription_service.py` |
| 7 | `backend/routes/shop_routes.py`, `paypal_routes.py`, `missing_endpoints_routes.py`, `cogs_routes.py` (monetization + webhook) |
| 8 | `data/monetization_config.json` |

Then **restart** the Python/uWSGI stack so routes and services reload.

**Automation:** the repo root **`deploy.py`** already lists the above (plus optional files below) in `FILES_TO_DEPLOY` — run `python deploy.py` from the project root after a pull to upload and restart.

### Optional

| Path | When |
|------|------|
| `scripts/cogs_metering_report.py` | Run **p50/p90** reports on the server via SSH (`python scripts/cogs_metering_report.py`). Not required for the web app to serve traffic. |
| `scripts/scr_usage_export.py` | **SCR (§4):** CSV export joining **`payment_ledger.jsonl`** and **`metering.jsonl`** (`exports/` by default). Not required at runtime. |
| `scripts/monetization_scr_export.py` | **Phase C sanity check:** JSON blended revenue vs metering COGS (`--since-days`, `--scr-only`); logic in **`backend/services/monetization_scr_blend_service.py`**. |
| `docs/SHOP_MONETIZATION_AUTOMATION_CLOSEOUT.md` | **Conclusion:** Shop v4 automation (`DEPLOY_POST_VERIFY`, `post_deploy_verify.py`), migration plan status, cheat sheet. |
| `docs/MONETIZATION_PAYPAL.md`, `docs/MONETIZATION_INVESTIGATION_CLOSEOUT.md`, `docs/REFERENCE_JOB_COGS.md`, other `docs/*.md` | Documentation only; no runtime dependency. |

### Metering stats API (optional)

If you call **`GET /api/system/cogs/metering-stats`**:

1. On the server, set in `.env` (or the environment uWSGI reads):

   `COGS_ADMIN_REPORT_KEY=<long random secret>`

2. Request with the same value:

   - Header: **`X-Cogs-Admin-Key: <secret>`**, or  
   - Query: **`?key=<secret>`**

If **`COGS_ADMIN_REPORT_KEY`** is unset, the endpoint returns **503** (`metering_stats_disabled`). See `.env.example` for the variable name.

### Verify

- `GET /api/system/cogs/summary` — should return reference + rates (no auth).  
- After a completed rich video, **`logs/cogs/metering.jsonl`** should gain rows with **`llm_tokens_source`** when providers return usage.  
- `python scripts/cogs_metering_report.py` — prints aggregates when the log file exists.

---

## 10. Implementation status & next steps

High-level **where the doc vs code is** (see also [§0 two-line lens](#two-line-progress-lens)).

### Status by area

| § | Topic | Code / product |
|---|--------|----------------|
| §1 | Coin / credit packs | **Partial** — **`data/monetization_config.json`** is the single source for pack SKUs + **`credit_definition.reference_fraction_per_credit`** + optional **`generation_credits_granted`** per pack; `GET /api/monetization/config` exposes it. Live PayPal + shop UX remains ops. |
| §2 | Premium tiers | **Shipped (opt-in)** — caps from JSON; enforcement when **`MONETIZATION_TIER_ENFORCEMENT=1`**. Checks run in **`video_generator_service`** before planning and in **`/api/unified/generate-video`** (HTTP 402/403 + `upsell`). User tier: profile **`preferences.monetization_tier`** or **`MONETIZATION_FORCE_TIER`**. |
| §3 | Subscriptions | **Shipped (ops + product):** **`POST /api/monetization/subscription/create`** → PayPal approve URL; return → **`POST /api/monetization/subscription/bind`**; webhook **`POST /api/monetization/webhooks/paypal-subscription`**; shop **Pro subscription** block on **PayPal & coins**. Replace **`P-PLACEHOLDER-PRO`**, set **`PAYPAL_WEBHOOK_ID`**, live plans. |
| §4 | Lion’s share / B2B (**Studio Cash Rail**) | **Shipped (ops + flags)** — SKUs + ledger + **`record-payment`**; **export** + **org pool** enforcement + **`org_label`** on metering when org is set (see §4 table and `.env.example`). |
| §5 | Marketplace | **Deferred** — explicit in doc. |
| **Shop V.9** | Single shop surface + regression checks | **`SHOP_UI_VERSION`** = **`9.0.0`** in **`backend/routes/shop_routes.py`** (exposed as **`shop_ui_version`** on **`GET /api/shop/config`**); **`shop/index.html`** maps sections 1–5 to PayPal packs, tiers, subscriptions, SCR/B2B, and catalog/MN2 purchases. **API line test** (`ShopV9.runProductLineChecks`; **`ShopV4`** alias) mirrors **`scripts/shop_v4_production_smoke.py`** GET coverage. |
| §8.1 | LLM + metering dashboard | **Shipped** — see §8.1 table; tier caps are §2. |
| §8.2–8.5 | Retention, infra, B2B API, growth | **Playbook (expanded):** §8.2–8.5 tables; **habit loops** = no **automated** nudges; **paid queue** = no **separate** subsystem (**`priority_tier`** future); **metered API keys** roadmap; **SCR** + **growth** mix of shipped and process. |
| **Attribution** | Revenue ↔ jobs (phase **C** margin) | **Partial** — **`payment_ledger.jsonl`** + **`metering.jsonl`** ship (**COGS** per **`job_id`**, payments/grants on ledger). **Gap:** **revenue ↔ `job_id`** (or billing-period allocation) **beyond** raw metering — i.e. which **capture/subscription/SCR line** funded **which** billable jobs — for **blended gross margin**; no single shipped end-to-end report. |

### Suggested next engineering commits (ordered)

1. ~~**P0 retail:**~~ **Done in repo:** `data/monetization_config.json` + `monetization_config_service` + shop/paypal use **`get_coin_pack_map()`**. Remaining: **live** PayPal credentials and product copy.  
2. ~~**P1 tiers:**~~ **Done (flagged):** `monetization_tier_service` + checks before planning; enable with **`MONETIZATION_TIER_ENFORCEMENT=1`**.  
3. ~~**P1 attribution:**~~ **Done:** append-only **`payment_ledger.jsonl`** on capture and on subscription billing (**`subscription_id`** populated for recurring grants).  
4. ~~**P2 subscriptions:**~~ **Done in repo:** webhook **verify**, **`POST /api/monetization/subscription/create`** (PayPal **`/v1/billing/subscriptions`** + **`approve_url`**), **`POST /api/monetization/subscription/bind`**, shop **PayPal & coins** tab (subscribe + return handler), **`PAYMENT.SALE.COMPLETED`** grants, idempotent webhooks. Remaining: replace **`P-PLACEHOLDER-PRO`** with a **real** PayPal billing plan id, optional **DB** mirror of **`subscription_bindings`**, polish copy and pricing.  
5. ~~**SCR (§4):**~~ **Done in repo:** **`b2b_studio_skus`**, ledger, **`record-payment`**, **`scripts/scr_usage_export.py`**, **`monetization_org_pool_service`** ( **`MONETIZATION_ORG_POOL_ENFORCEMENT`**, **`scr_org_label`** on **`POST /api/unified/generate-video`** and profile prefs).

### When to edit this file

Update **§0 phase table**, **§10 status rows**, and **§8.1 shipped** lines when you ship or descope a capability — keep **one** weekly headline metric honest. When retention, infra, B2B, or growth **ship** materially, refresh **§8.2–8.5** status columns.

---

**Disclaimer:** COGS env defaults are placeholders until set from your invoices. This doc is **product/engineering alignment**, not tax or legal advice.
