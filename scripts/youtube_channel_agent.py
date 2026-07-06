#!/usr/bin/env python3
"""YouTube content agent for trading reports: generate, package, and optionally upload."""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REPORT_JSON = ROOT / "reports" / "trading_content" / "trading_content_report_latest.json"
DEFAULT_OUTDIR = ROOT / "reports" / "youtube_agent"
DEFAULT_CREDS = ROOT / "config" / "youtube_client_secrets.json"
DEFAULT_TOKEN = ROOT / "config" / "youtube_token.json"
DEFAULT_CATEGORY_ID = "28"  # Science & Technology
SCOPES = ["https://www.googleapis.com/auth/youtube"]


@dataclass
class CredentialStatus:
    has_client_secrets: bool
    has_token_file: bool
    channel_id: Optional[str]
    channel_handle: Optional[str]
    upload_enabled: bool
    live_enabled: bool
    missing: List[str]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def _load_report(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _credential_status(client_secrets: Path, token_path: Path) -> CredentialStatus:
    channel_id = (os.environ.get("YOUTUBE_CHANNEL_ID") or "").strip() or None
    channel_handle = (os.environ.get("YOUTUBE_CHANNEL_HANDLE") or "").strip() or None
    upload_enabled = (os.environ.get("YOUTUBE_ENABLE_UPLOAD") or "0").strip() in ("1", "true", "yes", "on")
    live_enabled = (os.environ.get("YOUTUBE_ENABLE_LIVE") or "0").strip() in ("1", "true", "yes", "on")

    missing: List[str] = []
    if not client_secrets.is_file():
        missing.append(f"Missing client secrets file: {client_secrets}")
    if not channel_id and not channel_handle:
        missing.append("Set YOUTUBE_CHANNEL_ID or YOUTUBE_CHANNEL_HANDLE for channel targeting.")
    if upload_enabled and not token_path.is_file():
        missing.append(
            f"Upload is enabled but token file is missing: {token_path}. "
            "Run upload once interactively to generate token."
        )
    return CredentialStatus(
        has_client_secrets=client_secrets.is_file(),
        has_token_file=token_path.is_file(),
        channel_id=channel_id,
        channel_handle=channel_handle,
        upload_enabled=upload_enabled,
        live_enabled=live_enabled,
        missing=missing,
    )


def _select_content(report_payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if "report" in report_payload and "content_pack" in report_payload:
        return report_payload["report"], report_payload["content_pack"]
    # Compatibility fallback if plain report was passed.
    return report_payload, {}


def _build_assets(report: Dict[str, Any], content_pack: Dict[str, Any], channel_name: str) -> Dict[str, Any]:
    metrics = report.get("metrics_window") or {}
    top_symbols = report.get("top_symbols_window") or []
    top_events = report.get("top_events_window") or []
    top_symbol = top_symbols[0]["symbol"] if top_symbols else "N/A"
    top_event = top_events[0]["event_type"] if top_events else "N/A"
    window_hours = int(report.get("window_hours") or 24)
    trades = int(metrics.get("trade_count") or 0)
    notional = float(metrics.get("notional_usd") or 0)
    fees = float(metrics.get("fee_usd") or 0)
    timestamp = _now_utc().strftime("%Y-%m-%d")

    title = f"Trading Pulse: {trades:,} Trades in {window_hours}h | {channel_name}"
    short_title = f"{trades:,} trades in {window_hours}h"
    description = (
        f"Today's trading pulse from our automated exchange stack.\n\n"
        f"Window: last {window_hours}h\n"
        f"Trades: {trades:,}\n"
        f"Notional: {_fmt_money(notional)}\n"
        f"Estimated fees: {_fmt_money(fees)}\n"
        f"Top symbol: {top_symbol}\n"
        f"Top event: {top_event}\n\n"
        "This report is generated automatically from SQL-backed trading records and logs.\n"
        "If you want deeper breakdowns, comment below with the metrics you want next.\n\n"
        "#trading #crypto #analytics #automation"
    )
    tags = [
        "trading",
        "crypto",
        "algorithmic trading",
        "market analysis",
        "youtube automation",
        f"{top_symbol.lower()}",
    ]

    hook = content_pack.get("video_script_30s") or (
        f"Hook: We executed {trades:,} trades in the last {window_hours}h.\n"
        f"Body: That is {_fmt_money(notional)} notional and {_fmt_money(fees)} in estimated fees.\n"
        f"Close: {top_symbol} led activity, with {top_event} as the top operational event."
    )
    shorts_script = (
        f"{short_title}. "
        f"Volume: {_fmt_money(notional)}. "
        f"Fees: {_fmt_money(fees)}. "
        f"Top symbol: {top_symbol}. Follow for daily trading pulses."
    )
    livestream_outline = (
        "Live stream plan (45-60 min)\n"
        "1) Intro + disclaimer (5 min)\n"
        "2) Trading pulse recap from latest SQL report (10 min)\n"
        "3) Top symbols and event flow breakdown (15 min)\n"
        "4) Risk/ops and what changed vs previous window (10 min)\n"
        "5) Q&A and next-run commitments (10-20 min)\n"
    )
    monetization_notes = (
        "Monetization focus\n"
        "- Long-form: weekly trading recap + educational explainers for watch-time growth.\n"
        "- Shorts: daily pulse clips to grow top-of-funnel traffic.\n"
        "- Live streams: super chats, memberships, and sponsor slots once audience consistency improves.\n"
        "- Conversion: include CTA to your paid product, consulting, or premium analytics.\n"
        "- KPI targets: CTR > 5%, average view duration growth, returning viewers, and subscriber conversion."
    )

    return {
        "title": title,
        "short_title": short_title,
        "description": description,
        "tags": tags,
        "category_id": DEFAULT_CATEGORY_ID,
        "privacy_status": os.environ.get("YOUTUBE_PRIVACY_STATUS", "private"),
        "video_script_30s": hook,
        "shorts_script": shorts_script,
        "livestream_outline": livestream_outline,
        "monetization_notes": monetization_notes,
        "x_post": content_pack.get("x_post"),
        "linkedin_post": content_pack.get("linkedin_post"),
        "newsletter_blurb": content_pack.get("newsletter_blurb"),
        "generated_at": _now_utc().isoformat().replace("+00:00", "Z"),
        "report_window_end": report.get("window_end"),
        "date_stamp": timestamp,
    }


def _write_package(outdir: Path, assets: Dict[str, Any]) -> Dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = _now_utc().strftime("youtube_content_%Y%m%d_%H%M%S")
    run_dir = outdir / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = run_dir / "youtube_upload_metadata.json"
    script_path = run_dir / "video_script_30s.txt"
    shorts_path = run_dir / "shorts_script.txt"
    live_path = run_dir / "livestream_plan.txt"
    monetization_path = run_dir / "monetization_plan.txt"
    channel_fix_path = run_dir / "channel_fix_checklist.md"

    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "title": assets["title"],
                "description": assets["description"],
                "tags": assets["tags"],
                "category_id": assets["category_id"],
                "privacy_status": assets["privacy_status"],
            },
            f,
            indent=2,
            ensure_ascii=True,
        )
        f.write("\n")
    script_path.write_text(assets["video_script_30s"] + "\n", encoding="utf-8")
    shorts_path.write_text(assets["shorts_script"] + "\n", encoding="utf-8")
    live_path.write_text(assets["livestream_outline"] + "\n", encoding="utf-8")
    monetization_path.write_text(assets["monetization_notes"] + "\n", encoding="utf-8")
    channel_fix_path.write_text(
        "# YouTube channel setup fix checklist\n\n"
        "1. Verify channel ownership in YouTube Studio -> Settings -> Channel.\n"
        "2. Enable 2FA on the Google account used for API upload.\n"
        "3. In Google Cloud Console, enable YouTube Data API v3.\n"
        "4. Create OAuth client credentials (Desktop app), save to `config/youtube_client_secrets.json`.\n"
        "5. Set env vars: `YOUTUBE_CHANNEL_ID` (or handle), `YOUTUBE_ENABLE_UPLOAD=1`.\n"
        "6. Run upload once interactively to mint token at `config/youtube_token.json`.\n"
        "7. In YouTube Studio, verify upload defaults (language, visibility, category, audience).\n"
        "8. For livestreams, enable live streaming in channel eligibility settings (can take 24h).\n"
        "9. Add monetization hooks: channel memberships, super chats, sponsor contact info.\n"
        "10. Keep legal/compliance disclaimer in descriptions for trading-related content.\n",
        encoding="utf-8",
    )

    latest = outdir / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "youtube_upload_metadata.json").write_text(metadata_path.read_text(encoding="utf-8"), encoding="utf-8")
    (latest / "video_script_30s.txt").write_text(script_path.read_text(encoding="utf-8"), encoding="utf-8")
    (latest / "shorts_script.txt").write_text(shorts_path.read_text(encoding="utf-8"), encoding="utf-8")
    (latest / "livestream_plan.txt").write_text(live_path.read_text(encoding="utf-8"), encoding="utf-8")
    (latest / "monetization_plan.txt").write_text(monetization_path.read_text(encoding="utf-8"), encoding="utf-8")
    (latest / "channel_fix_checklist.md").write_text(channel_fix_path.read_text(encoding="utf-8"), encoding="utf-8")

    return {
        "run_dir": str(run_dir),
        "metadata_json": str(metadata_path),
        "script": str(script_path),
        "shorts_script": str(shorts_path),
        "livestream_plan": str(live_path),
        "monetization_plan": str(monetization_path),
        "channel_fix_checklist": str(channel_fix_path),
        "latest_dir": str(latest),
    }


def _youtube_client(client_secrets: Path, token_path: Path):
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except Exception as exc:
        raise RuntimeError(
            "YouTube upload dependencies missing. Install: pip install google-api-python-client google-auth-oauthlib"
        ) from exc

    creds = None
    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secrets.is_file():
                raise RuntimeError(f"Missing OAuth client secrets file: {client_secrets}")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def upload_video(
    *,
    client_secrets: Path,
    token_path: Path,
    video_file: Path,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    if not video_file.is_file():
        raise RuntimeError(f"Video file not found: {video_file}")
    youtube = _youtube_client(client_secrets, token_path)
    from googleapiclient.http import MediaFileUpload  # type: ignore

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata.get("tags") or [],
            "categoryId": metadata.get("category_id") or DEFAULT_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": metadata.get("privacy_status") or "private",
            "selfDeclaredMadeForKids": False,
        },
    }
    req = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_file), chunksize=-1, resumable=True),
    )
    resp = req.execute()
    vid = resp.get("id")
    return {"success": True, "video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}" if vid else None}


def create_livestream_event(
    *,
    client_secrets: Path,
    token_path: Path,
    title: str,
    description: str,
    start_in_hours: int,
    privacy_status: str,
) -> Dict[str, Any]:
    youtube = _youtube_client(client_secrets, token_path)
    start = (_now_utc() + timedelta(hours=start_in_hours)).isoformat().replace("+00:00", "Z")
    req = youtube.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "scheduledStartTime": start,
            },
            "status": {"privacyStatus": privacy_status},
            "contentDetails": {"enableAutoStart": False, "enableAutoStop": False},
        },
    )
    resp = req.execute()
    return {
        "success": True,
        "broadcast_id": resp.get("id"),
        "scheduled_start": start,
        "title": title,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="YouTube channel/content agent for trading content.")
    p.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON), help="Path to trading_content report JSON.")
    p.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="Output directory for generated YouTube assets.")
    p.add_argument("--channel-name", default=os.environ.get("YOUTUBE_CHANNEL_NAME", "MasterNoder"), help="Brand/channel name in titles.")
    p.add_argument("--client-secrets", default=str(DEFAULT_CREDS), help="OAuth client secrets JSON file.")
    p.add_argument("--token-file", default=str(DEFAULT_TOKEN), help="OAuth token JSON file.")
    p.add_argument("--video-file", default="", help="Video file path to upload when --upload is used.")
    p.add_argument("--upload", action="store_true", help="Upload generated metadata + video to YouTube.")
    p.add_argument("--create-live", action="store_true", help="Create a scheduled livestream event.")
    p.add_argument("--live-start-hours", type=int, default=24, help="Hours from now when scheduling live event.")
    p.add_argument("--dry-run", action="store_true", help="Generate/check everything except external API writes.")
    p.add_argument("--print-json", action="store_true", help="Print machine-readable result JSON.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report_json)
    outdir = Path(args.outdir)
    client_secrets = Path(args.client_secrets)
    token_path = Path(args.token_file)

    if not report_path.is_file():
        raise SystemExit(f"Trading report JSON not found: {report_path}")

    report_payload = _load_report(report_path)
    report, content_pack = _select_content(report_payload)
    creds = _credential_status(client_secrets, token_path)
    assets = _build_assets(report, content_pack, args.channel_name)
    paths = _write_package(outdir, assets)

    result: Dict[str, Any] = {
        "success": True,
        "generated_at": _now_utc().isoformat().replace("+00:00", "Z"),
        "report_source": str(report_path),
        "paths": paths,
        "credential_status": {
            "has_client_secrets": creds.has_client_secrets,
            "has_token_file": creds.has_token_file,
            "channel_id": creds.channel_id,
            "channel_handle": creds.channel_handle,
            "upload_enabled": creds.upload_enabled,
            "live_enabled": creds.live_enabled,
            "missing": creds.missing,
        },
        "actions": {},
    }

    metadata = {
        "title": assets["title"],
        "description": assets["description"],
        "tags": assets["tags"],
        "category_id": assets["category_id"],
        "privacy_status": assets["privacy_status"],
    }

    if args.upload:
        if args.dry_run:
            result["actions"]["upload"] = {
                "success": True,
                "dry_run": True,
                "message": "Upload skipped due to --dry-run.",
                "video_file": args.video_file,
            }
        else:
            try:
                upload_result = upload_video(
                    client_secrets=client_secrets,
                    token_path=token_path,
                    video_file=Path(args.video_file),
                    metadata=metadata,
                )
                result["actions"]["upload"] = upload_result
            except Exception as exc:
                result["actions"]["upload"] = {"success": False, "error": str(exc)}

    if args.create_live:
        if args.dry_run:
            result["actions"]["livestream"] = {
                "success": True,
                "dry_run": True,
                "title": f"LIVE Trading Pulse: {assets['short_title']}",
                "start_in_hours": args.live_start_hours,
            }
        else:
            try:
                live = create_livestream_event(
                    client_secrets=client_secrets,
                    token_path=token_path,
                    title=f"LIVE Trading Pulse: {assets['short_title']}",
                    description=assets["description"],
                    start_in_hours=args.live_start_hours,
                    privacy_status=assets["privacy_status"],
                )
                result["actions"]["livestream"] = live
            except Exception as exc:
                result["actions"]["livestream"] = {"success": False, "error": str(exc)}

    if args.print_json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print("YouTube channel agent complete.")
        print(f"Content package: {paths['run_dir']}")
        print(f"Latest package: {paths['latest_dir']}")
        if creds.missing:
            print("Credential/setup gaps:")
            for item in creds.missing:
                print(f"- {item}")
        else:
            print("Credential setup looks good for automated upload/live operations.")
        if result["actions"]:
            print("Actions:")
            for name, payload in result["actions"].items():
                print(f"- {name}: {payload}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
