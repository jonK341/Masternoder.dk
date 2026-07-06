#!/usr/bin/env python3
"""AI content factory: creates fresh video/clip ideas and optionally dispatches generator jobs."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_JSON = ROOT / "reports" / "trading_content" / "trading_content_report_latest.json"
DEFAULT_OUTDIR = ROOT / "reports" / "ai_content_factory"
DEFAULT_API_BASE = os.environ.get("CONTENT_FACTORY_API_BASE", "http://127.0.0.1:5000")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _money(v: float) -> str:
    return f"${v:,.2f}"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract(payload: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    if "report" in payload and "content_pack" in payload:
        return payload["report"], payload["content_pack"]
    return payload, {}


def _safe_topic(s: str) -> str:
    return "".join(ch for ch in s if ch.isalnum() or ch in (" ", "-", "_")).strip()


def build_plan(report: Dict[str, Any], content_pack: Dict[str, Any], long_count: int, short_count: int) -> Dict[str, Any]:
    mw = report.get("metrics_window") or {}
    top_symbols = report.get("top_symbols_window") or []
    top_events = report.get("top_events_window") or []
    top_symbol = top_symbols[0]["symbol"] if top_symbols else "BTC"
    top_event = top_events[0]["event_type"] if top_events else "swap"
    window_hours = int(report.get("window_hours") or 24)
    trades = int(mw.get("trade_count") or 0)
    notional = float(mw.get("notional_usd") or 0.0)
    fees = float(mw.get("fee_usd") or 0.0)

    long_form: List[Dict[str, Any]] = []
    for i in range(long_count):
        title = (
            f"AI Trading Pulse #{i+1}: {trades:,} Trades in {window_hours}h "
            f"({_safe_topic(top_symbol)})"
        )
        desc = (
            f"Fresh AI-generated market recap from live trading telemetry. "
            f"Window={window_hours}h, volume={_money(notional)}, fees={_money(fees)}, "
            f"top symbol={top_symbol}, top event={top_event}."
        )
        long_form.append(
            {
                "title": title,
                "description": desc,
                "theme": "documentary",
                "duration": 120 if i == 0 else 90,
                "short_clip": False,
            }
        )

    shorts: List[Dict[str, Any]] = []
    base_prompt = content_pack.get("video_script_30s") or (
        f"{trades:,} trades in {window_hours}h. Top symbol {top_symbol}. "
        f"Estimated fees {_money(fees)}."
    )
    for i in range(short_count):
        prompt = (
            f"Create a vertical short (9:16), energetic pacing, clear captions. "
            f"Hook in first 2 seconds. Topic: {top_symbol} + {top_event}. "
            f"Core script: {base_prompt} Variant {i+1}."
        )
        shorts.append(
            {
                "prompt": prompt,
                "meta": {"aspect_ratio": "9:16", "variant": i + 1, "topic": top_symbol},
            }
        )

    stream_gate = {
        "requires_min_long_jobs": 1,
        "requires_min_short_jobs": 2,
        "stream_title": f"LIVE: AI Trading Pulse + Content Build ({top_symbol})",
        "stream_reason": "Go live when enough fresh generated assets are available for review + commentary.",
    }

    return {
        "generated_at": _now_utc().isoformat().replace("+00:00", "Z"),
        "report_window_end": report.get("window_end"),
        "summary": {
            "window_hours": window_hours,
            "trades": trades,
            "notional_usd": notional,
            "fees_usd": fees,
            "top_symbol": top_symbol,
            "top_event": top_event,
        },
        "long_form_jobs": long_form,
        "short_clip_jobs": shorts,
        "livestream_gate": stream_gate,
    }


def _post_json(url: str, payload: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    try:
        r = requests.post(url, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        return {"success": False, "error": f"request_failed:{exc}", "_http_status": 0}
    try:
        data = r.json()
    except Exception:
        data = {"success": False, "error": f"non_json_response:{r.text[:300]}"}
    data["_http_status"] = r.status_code
    return data


def _get_json(url: str, timeout: int = 60) -> Dict[str, Any]:
    try:
        r = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:
        return {"success": False, "error": f"request_failed:{exc}", "_http_status": 0}
    try:
        data = r.json()
    except Exception:
        data = {"success": False, "error": f"non_json_response:{r.text[:300]}"}
    data["_http_status"] = r.status_code
    return data


def dispatch_jobs(
    plan: Dict[str, Any],
    api_base: str,
    user_id: str,
    generate_live_event: bool,
    live_start_hours: int,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {"long_jobs": [], "short_jobs": [], "livestream": None}

    for row in plan.get("long_form_jobs", []):
        payload = dict(row)
        payload["user_id"] = user_id
        res = _post_json(f"{api_base}/api/generator/create", payload)
        out["long_jobs"].append({"request": payload, "response": res})

    for row in plan.get("short_clip_jobs", []):
        payload = {"prompt": row["prompt"], "meta": row["meta"]}
        res = _post_json(f"{api_base}/api/generator/ai-clips", payload)
        out["short_jobs"].append({"request": payload, "response": res})

    long_ok = sum(1 for j in out["long_jobs"] if (j["response"].get("success") is True))
    short_ok = sum(1 for j in out["short_jobs"] if (j["response"].get("success") is True))
    gate = plan.get("livestream_gate") or {}
    can_stream = long_ok >= int(gate.get("requires_min_long_jobs") or 1) and short_ok >= int(
        gate.get("requires_min_short_jobs") or 1
    )

    if generate_live_event and can_stream:
        cmd = [
            "python3",
            str(ROOT / "scripts" / "youtube_channel_agent.py"),
            "--create-live",
            "--live-start-hours",
            str(live_start_hours),
            "--print-json",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        live_payload: Dict[str, Any] = {"success": False, "stdout": proc.stdout, "stderr": proc.stderr}
        if proc.stdout.strip():
            try:
                live_payload = json.loads(proc.stdout)
            except Exception:
                pass
        out["livestream"] = {
            "triggered": True,
            "can_stream": True,
            "command": " ".join(cmd),
            "result": live_payload,
        }
    else:
        out["livestream"] = {
            "triggered": False,
            "can_stream": can_stream,
            "reason": "Gate not met or stream generation disabled.",
        }
    return out


def save_outputs(outdir: Path, payload: Dict[str, Any]) -> Dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = _now_utc().strftime("ai_content_factory_%Y%m%d_%H%M%S")
    run_dir = outdir / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    json_path = run_dir / "factory_output.json"
    md_path = run_dir / "factory_output.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    plan = payload.get("plan") or {}
    summary = plan.get("summary") or {}
    md = [
        "# AI Content Factory Output",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Dry run: `{payload.get('dry_run')}`",
        f"- API base: `{payload.get('api_base')}`",
        "",
        "## Summary",
        f"- Trades: `{summary.get('trades')}`",
        f"- Notional: `{summary.get('notional_usd')}`",
        f"- Fees: `{summary.get('fees_usd')}`",
        f"- Top symbol: `{summary.get('top_symbol')}`",
        f"- Top event: `{summary.get('top_event')}`",
        "",
        "## Long-form jobs",
    ]
    for row in plan.get("long_form_jobs", []):
        md.append(f"- `{row.get('title')}` ({row.get('duration')}s)")
    md.append("")
    md.append("## Short clip jobs")
    for row in plan.get("short_clip_jobs", []):
        md.append(f"- `{row.get('meta', {}).get('topic')}` variant `{row.get('meta', {}).get('variant')}`")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    latest = outdir / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "factory_output.json").write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    (latest / "factory_output.md").write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    return {"run_dir": str(run_dir), "json": str(json_path), "markdown": str(md_path), "latest": str(latest)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AI content factory for generator + YouTube pipeline.")
    p.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON), help="Trading content report JSON input.")
    p.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="Output folder for factory plans/results.")
    p.add_argument("--api-base", default=DEFAULT_API_BASE, help="Backend API base URL.")
    p.add_argument("--user-id", default=os.environ.get("CONTENT_FACTORY_USER_ID", "youtube_agent"), help="User id for generator jobs.")
    p.add_argument("--long-count", type=int, default=1, help="How many long-form jobs to plan/create.")
    p.add_argument("--short-count", type=int, default=3, help="How many short-clip jobs to plan/create.")
    p.add_argument("--create-live-on-gate", action="store_true", help="Create YouTube live event when output gate is met.")
    p.add_argument("--live-start-hours", type=int, default=24, help="Live event start offset (hours).")
    p.add_argument("--dry-run", action="store_true", help="Plan only; do not call generator or YouTube APIs.")
    p.add_argument("--print-json", action="store_true", help="Print result JSON.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report_json)
    if not report_path.is_file():
        raise SystemExit(f"Missing report JSON: {report_path}")
    report_payload = _read_json(report_path)
    report, content_pack = _extract(report_payload)
    plan = build_plan(report, content_pack, args.long_count, args.short_count)

    payload: Dict[str, Any] = {
        "success": True,
        "generated_at": _now_utc().isoformat().replace("+00:00", "Z"),
        "dry_run": bool(args.dry_run),
        "api_base": args.api_base,
        "report_json": str(report_path),
        "plan": plan,
        "dispatch": None,
    }

    if not args.dry_run:
        health = _get_json(f"{args.api_base}/api/health", timeout=20)
        if int(health.get("_http_status") or 0) >= 400:
            payload["success"] = False
            payload["dispatch"] = {"error": "api_unavailable", "health": health}
        else:
            payload["dispatch"] = dispatch_jobs(
                plan=plan,
                api_base=args.api_base.rstrip("/"),
                user_id=args.user_id,
                generate_live_event=bool(args.create_live_on_gate),
                live_start_hours=args.live_start_hours,
            )

    paths = save_outputs(Path(args.outdir), payload)
    payload["paths"] = paths

    if args.print_json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        print(f"AI content factory complete. Output: {paths['run_dir']}")
        print(f"Latest output: {paths['latest']}")
        print(f"Dry run: {payload['dry_run']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
