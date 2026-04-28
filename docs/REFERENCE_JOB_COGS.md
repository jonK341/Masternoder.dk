# Reference job and COGS metering (global)

**Purpose:** One canonical **reference job** anchors pricing and margin math for **API (Runway, LLM), GPU/CPU encode, and storage** — scoped for **global** use (default **USD**), not Denmark-only.

**Code:** `backend/services/cogs_metering_service.py`  
**Per-job log:** `logs/cogs/metering.jsonl` (append-only; one JSON object per successful generation when the rich-video path runs; AI-clips bundle jobs also append a lighter row).

---

## 1. Reference job definition

| Field | Value (v1) |
|-------|------------|
| **ID** | `ref_v1_global_doc_90s` |
| **Intent** | Typical “full” pipeline: multi-segment documentary-style output |
| **Assumed output duration** | ~90 s |
| **Runway Gen-4** | 1 clip × **5 s** API-billed output (matches `runwayml_service.generate_segment_clips` default duration) |
| **LLM (blend)** | ~**12k** tokens, **4** calls (planning + enhancement — heuristic in code if not metered per call yet) |
| **Encode** | ~**180 s** wall CPU time (placeholder in reference; **actual** jobs use measured wall time around `write_videofile`) |
| **Output file** | ~**15 MB** (reference); **actual** jobs use real file size |
| **Storage** | **1 month** amortization at `COGS_STORAGE_USD_PER_GB_MONTH` |

Tune **reference assumptions** in `REFERENCE_JOB_SPEC` when your real production mix changes.

---

## 2. Environment variables (USD rates)

Set these from **your** provider invoices (Runway, cloud GPU, R2/S3, OpenAI/Groq paid usage). Defaults are **placeholders** — not financial advice.

| Variable | Meaning |
|----------|---------|
| `COGS_RUNWAY_USD_PER_OUTPUT_SECOND` | Runway (or equivalent) **$ per second** of **API video output** billed |
| `COGS_ENCODE_CPU_USD_PER_HOUR` | Amortized **server/CPU** cost for MoviePy/FFmpeg encode |
| `COGS_GPU_USD_PER_HOUR` | Optional **GPU** host cost if you encode on CUDA |
| `COGS_STORAGE_USD_PER_GB_MONTH` | Object storage **$ per GB-month** (e.g. R2, S3 IA) |
| `COGS_LLM_USD_PER_1K_TOKENS` | **Blended** $ / 1K tokens across routed providers (simplify v1) |
| `COGS_LLM_TOKENS_BASE` | Baseline token estimate when not instrumented |
| `COGS_LLM_TOKENS_PER_SEGMENT` | Extra tokens per segment in heuristic |
| `COGS_ENCODE_ASSUME_GPU` | `1` / `true` to use GPU rate for encode line item |
| `MASTERNODER_LOG_DIR` | Optional override for log root (default: project `logs/`) |

**API (read-only):**

- `GET /api/system/cogs/reference-job` — reference spec + **estimated** USD line items  
- `GET /api/system/cogs/summary` — effective rates + reference (no secrets)

---

## 3. What the pipeline records (actual jobs)

On **successful** `rich_video` completion, the service logs:

- **Runway:** `runway_clips`, `runway_output_seconds_billed` (from segments with `runway_video_path`)  
- **Encode:** `encode_wall_seconds` (monotonic timer around `final.write_videofile`)  
- **Output:** `output_file_bytes`, `output_video_duration_sec`  
- **Heuristic LLM tokens** if per-call usage is not yet aggregated (see `record_completed_video_job`)

Each row includes **`ratio_vs_reference_job`** = actual estimate ÷ reference total (handy for dashboards).

**AI clips** jobs (`ai_clips`) log a lighter row (no single output path; segment count drives LLM heuristic).

---

## 4. Pricing workflow (leverage)

1. Set env rates from **real COGS**.  
2. Call **`GET /api/system/cogs/reference-job`** — note **`total_usd`**.  
3. Pick **gross margin** (e.g. 70%) → minimum retail = `total_usd / (1 - margin)`.  
4. After a week of **`metering.jsonl`**, compare **median** `cogs_usd.total_usd` to the reference; adjust tiers and caps.

---

## 5. Related docs

- `docs/VIDEO_STORAGE_STRATEGY.md` — storage architecture and offload  
- `docs/RESEARCH_AI_SYSTEMS.md` — LLM providers and cron  
- `docs/MONETIZATION_PAYPAL.md` — PayPal-aligned revenue models (packs, tiers, subs, B2B, marketplace), rollout order, and code touchpoints; COGS here is **unit economics** — pair with that doc for **retail pricing**.

---

## 6. Runway pricing source

Update `COGS_RUNWAY_USD_PER_OUTPUT_SECOND` when Runway changes plans. Official API docs: [https://docs.dev.runwayml.com/](https://docs.dev.runwayml.com/)
