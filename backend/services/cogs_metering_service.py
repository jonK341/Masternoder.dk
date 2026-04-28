"""
COGS metering — reference job, Runway / encode (CPU·GPU) / storage / LLM blend.

Scope: global (USD by default); tune via env. Used for pricing that covers API, GPU, storage.

Logs: logs/cogs/metering.jsonl (one JSON object per completed job).
"""
from __future__ import annotations

import json
import os
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Reference job (pricing anchor — global, not region-specific)
# ---------------------------------------------------------------------------

REFERENCE_JOB_ID = "ref_v1_global_doc_90s"

# Narrative: typical "full" documentary-style job used to compare real runs.
REFERENCE_JOB_SPEC: Dict[str, Any] = {
    "id": REFERENCE_JOB_ID,
    "label": "Reference: ~90s output, 1× Runway Gen-4 clip, multi-segment encode, LLM plan",
    "scope": "global",
    "currency": "USD",
    "assumptions": {
        "output_video_duration_sec": 90,
        "runway_output_seconds_billed": 5,
        "runway_clips": 1,
        "llm_estimated_total_tokens": 12000,
        "llm_estimated_calls": 4,
        "encode_cpu_wall_sec": 180,
        "output_file_bytes": 15 * 1024 * 1024,
        "storage_amortization_days": 30,
    },
}


def _fenv(name: str, default: float) -> float:
    try:
        v = os.environ.get(name, "").strip()
        if not v:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _ienv(name: str, default: int) -> int:
    try:
        v = os.environ.get(name, "").strip()
        if not v:
            return default
        return int(float(v))
    except (TypeError, ValueError):
        return default


def runway_cost_usd(output_seconds: float) -> float:
    """Runway (and similar API video): $ per second of API output length."""
    rate = _fenv("COGS_RUNWAY_USD_PER_OUTPUT_SECOND", 0.05)
    return max(0.0, float(output_seconds) * rate)


def encode_compute_cost_usd(wall_seconds: float, use_gpu: bool = False) -> float:
    """Local encode (MoviePy/FFmpeg): amortized host cost."""
    if use_gpu:
        rate = _fenv("COGS_GPU_USD_PER_HOUR", 0.45)
    else:
        rate = _fenv("COGS_ENCODE_CPU_USD_PER_HOUR", 0.02)
    return max(0.0, (wall_seconds / 3600.0) * rate)


def storage_cost_usd_one_month(file_bytes: int) -> float:
    """Object/disk storage for one month (set COGS_STORAGE_USD_PER_GB_MONTH to your bucket rate)."""
    gb = max(0.0, int(file_bytes) / (1024.0 ** 3))
    rate = _fenv("COGS_STORAGE_USD_PER_GB_MONTH", 0.015)
    return gb * rate


def llm_cost_usd_total_tokens(total_tokens: int) -> float:
    """Blended LLM $ / 1K tokens (paid path); use 0 for free-only internal estimates."""
    rate = _fenv("COGS_LLM_USD_PER_1K_TOKENS", 0.0004)
    return max(0.0, (max(0, int(total_tokens)) / 1000.0) * rate)


def estimate_reference_job_usd() -> Dict[str, Any]:
    """Full line-item estimate for REFERENCE_JOB_SPEC using current env rates."""
    a = REFERENCE_JOB_SPEC["assumptions"]
    rw = runway_cost_usd(float(a["runway_output_seconds_billed"]))
    enc = encode_compute_cost_usd(float(a["encode_cpu_wall_sec"]), use_gpu=False)
    st = storage_cost_usd_one_month(int(a["output_file_bytes"]))
    llm = llm_cost_usd_total_tokens(int(a["llm_estimated_total_tokens"]))
    total = rw + enc + st + llm
    return {
        "reference_job_id": REFERENCE_JOB_ID,
        "currency": "USD",
        "line_items": {
            "runway_video_api": round(rw, 6),
            "encode_cpu": round(enc, 6),
            "storage_1mo": round(st, 6),
            "llm_blend": round(llm, 6),
        },
        "total_usd": round(total, 6),
        "assumptions": dict(a),
        "rates_effective": {
            "COGS_RUNWAY_USD_PER_OUTPUT_SECOND": _fenv("COGS_RUNWAY_USD_PER_OUTPUT_SECOND", 0.05),
            "COGS_ENCODE_CPU_USD_PER_HOUR": _fenv("COGS_ENCODE_CPU_USD_PER_HOUR", 0.02),
            "COGS_GPU_USD_PER_HOUR": _fenv("COGS_GPU_USD_PER_HOUR", 0.45),
            "COGS_STORAGE_USD_PER_GB_MONTH": _fenv("COGS_STORAGE_USD_PER_GB_MONTH", 0.015),
            "COGS_LLM_USD_PER_1K_TOKENS": _fenv("COGS_LLM_USD_PER_1K_TOKENS", 0.0004),
        },
    }


def _cogs_log_path() -> str:
    base = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "logs",
    )
    return os.path.join(base, "cogs", "metering.jsonl")


def metering_jsonl_path() -> str:
    """Absolute path to COGS metering log (same file as summarize_metering_jsonl)."""
    return _cogs_log_path()


def append_cogs_log(record: Dict[str, Any]) -> None:
    path = _cogs_log_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def _file_size(path: Optional[str]) -> int:
    try:
        if path and os.path.isfile(path):
            return int(os.path.getsize(path))
    except Exception:
        pass
    return 0


def build_actual_job_cogs_usd(
    *,
    runway_output_seconds: float,
    encode_wall_seconds: float,
    output_bytes: int,
    llm_tokens_estimated: int,
    encode_use_gpu: bool = False,
) -> Dict[str, Any]:
    """Line items for one completed job (actuals + LLM estimate if tokens unknown)."""
    rw = runway_cost_usd(runway_output_seconds)
    enc = encode_compute_cost_usd(encode_wall_seconds, use_gpu=encode_use_gpu)
    st = storage_cost_usd_one_month(output_bytes)
    llm = llm_cost_usd_total_tokens(llm_tokens_estimated)
    total = rw + enc + st + llm
    return {
        "runway_video_api": round(rw, 6),
        "encode_compute": round(enc, 6),
        "storage_1mo": round(st, 6),
        "llm_blend": round(llm, 6),
        "total_usd": round(total, 6),
    }


def _ratio_vs_reference(actual_total: float, reference_total: float) -> Optional[float]:
    if reference_total <= 0:
        return None
    return round(actual_total / reference_total, 4)


def _percentile_sorted(sorted_vals: List[float], p: float) -> Optional[float]:
    """p in [0,100]. Linear interpolation between closest ranks."""
    if not sorted_vals:
        return None
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    if p <= 0:
        return float(sorted_vals[0])
    if p >= 100:
        return float(sorted_vals[-1])
    k = (n - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, n - 1)
    if f == c:
        return float(sorted_vals[f])
    return float(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


def summarize_metering_jsonl(
    path: Optional[str] = None,
    *,
    max_lines: int = 100_000,
) -> Dict[str, Any]:
    """
    Read metering.jsonl and compute p50/p90 totals, line-item splits, ratio_vs_reference_job.
    path defaults to logs/cogs/metering.jsonl (respects MASTERNODER_LOG_DIR).
    """
    log_path = path or _cogs_log_path()
    totals: List[float] = []
    ratios: List[float] = []
    runway: List[float] = []
    encode: List[float] = []
    storage: List[float] = []
    llm: List[float] = []
    n_read = 0
    try:
        if not os.path.isfile(log_path):
            return {
                "success": False,
                "error": "file_not_found",
                "path": log_path,
                "count": 0,
            }
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if n_read >= max_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                n_read += 1
                cogs = row.get("cogs_usd") or {}
                t = float(cogs.get("total_usd") or 0)
                totals.append(t)
                runway.append(float(cogs.get("runway_video_api") or 0))
                encode.append(float(cogs.get("encode_compute") or 0))
                storage.append(float(cogs.get("storage_1mo") or 0))
                llm.append(float(cogs.get("llm_blend") or 0))
                rj = row.get("ratio_vs_reference_job")
                if rj is not None:
                    try:
                        ratios.append(float(rj))
                    except (TypeError, ValueError):
                        pass
    except Exception as e:
        return {"success": False, "error": str(e), "path": log_path, "count": 0}

    if not totals:
        return {
            "success": True,
            "path": log_path,
            "count": 0,
            "message": "no_rows",
        }

    totals_s = sorted(totals)
    ratios_s = sorted(ratios) if ratios else []

    def _line_stats(name: str, xs: List[float]) -> Dict[str, Any]:
        s = sorted(xs)
        return {
            "name": name,
            "sum_usd": round(sum(xs), 6),
            "mean_usd": round(statistics.mean(xs), 6),
            "p50_usd": round(_percentile_sorted(s, 50) or 0.0, 6),
            "p90_usd": round(_percentile_sorted(s, 90) or 0.0, 6),
        }

    out: Dict[str, Any] = {
        "success": True,
        "path": log_path,
        "count": len(totals),
        "total_usd": {
            "mean": round(statistics.mean(totals), 6),
            "p50": round(_percentile_sorted(totals_s, 50) or 0.0, 6),
            "p90": round(_percentile_sorted(totals_s, 90) or 0.0, 6),
            "min": round(min(totals), 6),
            "max": round(max(totals), 6),
        },
        "ratio_vs_reference_job": {
            "mean": round(statistics.mean(ratios), 6) if ratios else None,
            "p50": round(_percentile_sorted(ratios_s, 50) or 0.0, 6) if ratios else None,
            "p90": round(_percentile_sorted(ratios_s, 90) or 0.0, 6) if ratios else None,
        },
        "line_items": [
            _line_stats("runway_video_api", runway),
            _line_stats("encode_compute", encode),
            _line_stats("storage_1mo", storage),
            _line_stats("llm_blend", llm),
        ],
    }
    return out


def record_completed_video_job(
    *,
    job_kind: str,
    job_id: str,
    user_id: str,
    config: Dict[str, Any],
    output_path: Optional[str],
    video_metrics: Optional[Dict[str, Any]] = None,
    duration_config_sec: int = 90,
    num_segments: int = 1,
    llm_tokens_estimated: Optional[int] = None,
    org_label: Optional[str] = None,
) -> None:
    """
    Called after a successful video job. Best-effort; never raises.

    video_metrics: from generate_rich_video_sync(metrics_out=...) — runway clips, encode duration, etc.
    """
    try:
        vm = video_metrics or {}
        runway_clips = int(vm.get("runway_clips") or 0)
        runway_sec_per = float(vm.get("runway_seconds_per_clip") or 5.0)
        runway_output_seconds = float(vm.get("runway_output_seconds_billed") or (runway_clips * runway_sec_per))
        encode_wall = float(vm.get("encode_wall_seconds_est") or vm.get("encode_wall_seconds") or 0.0)
        out_dur = float(vm.get("output_video_duration_sec") or 0.0)
        encode_use_gpu = bool(vm.get("encode_used_gpu"))

        obytes = _file_size(output_path)
        if obytes <= 0:
            obytes = int(vm.get("output_file_bytes") or 0)

        # If encode time missing, rough estimate from output duration + segment count
        if encode_wall <= 0 and out_dur > 0:
            encode_wall = max(30.0, out_dur * 1.8 + num_segments * 8.0)

        llm_actual: Optional[int] = None
        if video_metrics:
            llm_actual = video_metrics.get("llm_tokens_actual")
            if llm_actual is None and isinstance(video_metrics.get("llm_usage_tokens"), dict):
                u = video_metrics["llm_usage_tokens"]
                llm_actual = int(u.get("total_tokens") or 0) or (
                    int(u.get("prompt_tokens") or 0) + int(u.get("completion_tokens") or 0)
                )

        tok_source = "heuristic"
        tok = llm_tokens_estimated
        if llm_actual is not None and int(llm_actual) > 0:
            tok = int(llm_actual)
            tok_source = "actual"
        if tok is None:
            # Heuristic: planning + enhancement scale with segments and duration
            tok = _ienv("COGS_LLM_TOKENS_BASE", 2500) + num_segments * _ienv("COGS_LLM_TOKENS_PER_SEGMENT", 800)
            tok += int(duration_config_sec // 30) * 400
            tok_source = "heuristic"

        line = build_actual_job_cogs_usd(
            runway_output_seconds=runway_output_seconds,
            encode_wall_seconds=encode_wall,
            output_bytes=obytes,
            llm_tokens_estimated=tok,
            encode_use_gpu=encode_use_gpu,
        )

        ref = estimate_reference_job_usd()
        ref_total = float(ref["total_usd"])
        ratio = _ratio_vs_reference(float(line["total_usd"]), ref_total)

        _org = org_label
        if _org is None and config:
            try:
                from backend.services.monetization_org_pool_service import resolve_scr_org_label

                _org = resolve_scr_org_label(user_id, config)
            except Exception:
                _org = None
        if _org:
            _org = str(_org).strip()[:256]

        record: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "job_kind": job_kind,
            "job_id": job_id,
            "user_id": user_id,
            "duration_config_sec": duration_config_sec,
            "num_segments": num_segments,
            "output_path": output_path,
            "output_bytes": obytes,
            "video_metrics": vm,
            "cogs_usd": line,
            "reference_job_id": REFERENCE_JOB_ID,
            "reference_total_usd": ref_total,
            "ratio_vs_reference_job": ratio,
            "llm_tokens_source": tok_source,
            "llm_tokens_for_cogs": int(tok),
        }
        if _org:
            record["org_label"] = _org
        append_cogs_log(record)
    except Exception:
        pass


def summarize_effective_rates() -> Dict[str, Any]:
    """For GET /api — no secrets."""
    return {
        "currency": "USD",
        "reference_job": REFERENCE_JOB_SPEC,
        "estimate": estimate_reference_job_usd(),
    }
