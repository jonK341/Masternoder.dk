#!/usr/bin/env python3
"""Batch onboard camgirls performers from a wave file (250-scale roster ops).

Reads JSON or CSV wave stubs (15–50 rows per wave), upserts data/camgirls_performers.json,
registers brand media meta, optionally syncs DB, provisions MN2/PayPal payout rails, and
runs the media generator for new slugs.

Examples (local):
  python scripts/camgirls_batch_onboard.py --file data/camgirls_performers_wave.template.json --dry-run
  python scripts/camgirls_batch_onboard.py --file waves/wave2.json --batch 2 --wave-size 25

On production server (Python script — never run with bash):
  cd /var/www/html && bash scripts/camgirls_py.sh scripts/camgirls_batch_onboard.py --file waves/wave2.json --batch 2 --dry-run
  # or: bash scripts/camgirls_batch_onboard.sh --file waves/wave2.json --batch 2 --dry-run
  python scripts/camgirls_batch_onboard.py --file waves/wave2.csv --batch 2 \\
    --provision-addresses --generate-media

Payout rails (MN2 getnewaddress + PayPal checkout metadata):
  Use --provision-addresses after JSON upserts, or run
  python scripts/camgirls_provision_payout_addresses.py --performer <id>
  Requires MN2_RPC_* in .env on the host that mints addresses.

Wave JSON fields: see data/camgirls_performers_wave.template.json
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "scripts"))

from project_env import load_project_dotenv


def main() -> int:
    load_project_dotenv()
    parser = argparse.ArgumentParser(description="Batch onboard camgirls performers from a wave file")
    parser.add_argument("--file", required=True, help="Wave JSON or CSV (see data/camgirls_performers_wave.template.json)")
    parser.add_argument("--batch", type=int, help="Wave batch number (default id prefix performer_wave<N>_)")
    parser.add_argument("--id-prefix", help="Override performer id prefix (e.g. performer_wave2_)")
    parser.add_argument("--wave-size", type=int, help="Max rows to process from the wave file")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print plan only; no writes")
    parser.add_argument(
        "--provision-addresses",
        action="store_true",
        help="After upsert, call provision_payout_rails for onboarded ids (MN2 + PayPal)",
    )
    parser.add_argument(
        "--generate-media",
        action="store_true",
        help="Run scripts/camgirls_generate_performer_media.py after meta registration",
    )
    parser.add_argument(
        "--no-sync-db",
        action="store_true",
        help="Skip SQLite camgirls_performers sync (upsert_performer still syncs per row)",
    )
    parser.add_argument(
        "--full-catalog-sync",
        action="store_true",
        help="Run full JSON→DB catalog sync after batch",
    )
    args = parser.parse_args()

    from backend.services.camgirls_wave_ops import build_wave_batch

    try:
        performers, media_by_id, summary = build_wave_batch(
            args.file,
            wave_size=args.wave_size,
            batch=args.batch,
            id_prefix=args.id_prefix,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(
        f"Wave: prefix={summary['id_prefix']} · "
        f"normalized={summary['normalized']}/{summary['selected']} rows"
    )
    for err in summary.get("errors") or []:
        print(f"  WARN: {err}", file=sys.stderr)

    if not performers:
        print("No performers to onboard", file=sys.stderr)
        return 1

    for p in performers:
        mid = media_by_id.get(p["id"]) or {}
        print(
            f"  {'[dry-run]' if args.dry_run else 'onboard'} {p['id']} · {p['display_name']} "
            f"· media={mid.get('slug', '—')}"
        )

    if args.dry_run:
        print(f"[dry-run] would register media meta for {len(media_by_id)} performers")
        if args.provision_addresses:
            print("[dry-run] would provision payout rails for onboarded ids")
        if args.generate_media:
            print("[dry-run] would run camgirls_generate_performer_media.py")
        return 0 if not summary.get("errors") else 1

    from backend.services.camgirls_media_service import upsert_performer_media_meta
    from backend.services.camgirls_service import upsert_performer

    upsert_performer_media_meta(media_by_id, dry_run=False)
    ok = 0
    ids: list[str] = []
    for row in performers:
        pid = row["id"]
        result = upsert_performer(row)
        if result.get("success"):
            ok += 1
            ids.append(pid)
            extra = ""
            if result.get("payout_address"):
                extra = f" payout={result['payout_address']}"
            elif result.get("payout_warning"):
                extra = f" (payout pending: {result['payout_warning']})"
            print(f"Upserted {pid}{extra}")
        else:
            print(f"Failed {pid}: {result.get('error')}", file=sys.stderr)

    if args.full_catalog_sync and not args.no_sync_db:
        from backend.services.camgirls_catalog_sync_service import sync_json_catalog_to_db

        sync = sync_json_catalog_to_db()
        print(f"SQLite catalog sync: {sync.get('synced')}/{sync.get('json_rows')} rows")
        if not sync.get("success"):
            return 1

    if args.provision_addresses and ids:
        from backend.services.camgirls_payout_service import provision_payout_rails

        result = provision_payout_rails(performer_ids=ids)
        mn2 = result.get("mn2") or {}
        paypal = result.get("paypal") or {}
        print(
            f"Payout rails: MN2 {result.get('provisioned_mn2')}/{result.get('total')} · "
            f"PayPal {result.get('provisioned_paypal')}/{result.get('total')}"
        )
        for row in mn2.get("results") or []:
            if row.get("success"):
                flag = " (cached)" if not row.get("created") else " (new)"
                print(f"  MN2 {row.get('performer_id')}: {row.get('payout_address')}{flag}")
            else:
                print(f"  MN2 FAIL {row.get('performer_id')}: {row.get('error')}", file=sys.stderr)
        for row in paypal.get("results") or []:
            if row.get("success"):
                pe = row.get("paypal_email") or "—"
                pc = "on" if row.get("paypal_checkout_enabled") else "off"
                print(f"  PayPal {row.get('performer_id')}: checkout {pc} · {pe}")
        if not result.get("success"):
            return 1

    if args.generate_media:
        py = os.environ.get("PYTHON", sys.executable)
        cmd = [py, os.path.join(BASE, "scripts", "camgirls_generate_performer_media.py")]
        print("Running media generator…")
        proc = subprocess.run(cmd, cwd=BASE)
        if proc.returncode != 0:
            return proc.returncode

    print(f"Done: {ok}/{len(performers)} performers onboarded")
    return 0 if ok == len(performers) else 1


if __name__ == "__main__":
    raise SystemExit(main())
