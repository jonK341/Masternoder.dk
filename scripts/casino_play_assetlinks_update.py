#!/usr/bin/env python3
"""Update static/.well-known/assetlinks.json with Play App Signing SHA-256."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETLINKS_PATH = ROOT / "static" / ".well-known" / "assetlinks.json"
PACKAGE_NAME = "dk.masternoder.casino"
PLACEHOLDER = "REPLACE_WITH_PLAY_APP_SIGNING_SHA256"
TRUNCATED_BAD = "305253597"

_HEX64 = re.compile(r"^[0-9A-Fa-f]{64}$")


def normalize_sha256(raw: str) -> str:
    """Strip colons/spaces and uppercase. Raises ValueError if not 64 hex chars."""
    cleaned = re.sub(r"[\s:]", "", (raw or "").strip())
    if not _HEX64.match(cleaned):
        raise ValueError(
            f"SHA-256 must be exactly 64 hex characters (got {len(cleaned)} after removing colons)"
        )
    if cleaned.upper() == TRUNCATED_BAD or len(cleaned) < 64:
        raise ValueError("Refusing truncated or known-bad fingerprint")
    return cleaned.upper()


def validate_fingerprint(raw: str, *, allow_placeholder: bool = False) -> str:
    """Validate fingerprint; return normalized 64-char hex (uppercase, no colons)."""
    value = (raw or "").strip()
    if value == PLACEHOLDER:
        if allow_placeholder:
            return value
        raise ValueError(f"Placeholder {PLACEHOLDER!r} is not a production fingerprint")
    if value == TRUNCATED_BAD or (re.sub(r"[\s:]", "", value).upper() == TRUNCATED_BAD):
        raise ValueError(f"Refusing known truncated production value {TRUNCATED_BAD!r}")
    return normalize_sha256(value)


def load_assetlinks(path: Path = ASSETLINKS_PATH) -> list:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}")
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list) or not data:
        raise ValueError("assetlinks.json must be a non-empty JSON array")
    entry = data[0]
    target = entry.get("target") or {}
    if entry.get("relation") != ["delegate_permission/common.handle_all_urls"]:
        raise ValueError("Unexpected relation in assetlinks.json")
    if target.get("namespace") != "android_app":
        raise ValueError("target.namespace must be android_app")
    if target.get("package_name") != PACKAGE_NAME:
        raise ValueError(f"target.package_name must be {PACKAGE_NAME}")
    fps = target.get("sha256_cert_fingerprints")
    if not isinstance(fps, list) or len(fps) != 1:
        raise ValueError("sha256_cert_fingerprints must be a single-element array")
    return data


def build_assetlinks(fingerprint: str) -> list:
    normalized = validate_fingerprint(fingerprint)
    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": PACKAGE_NAME,
                "sha256_cert_fingerprints": [normalized],
            },
        }
    ]


def write_assetlinks(fingerprint: str, path: Path = ASSETLINKS_PATH) -> str:
    payload = build_assetlinks(fingerprint)
    normalized = payload[0]["target"]["sha256_cert_fingerprints"][0]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    return normalized


def fingerprint_from_file(path: Path = ASSETLINKS_PATH) -> str:
    data = load_assetlinks(path)
    return data[0]["target"]["sha256_cert_fingerprints"][0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write Play App Signing SHA-256 into static/.well-known/assetlinks.json"
    )
    parser.add_argument(
        "sha256",
        help="SHA-256 certificate fingerprint (64 hex chars, with or without colons)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate fingerprint only; do not write file",
    )
    args = parser.parse_args()

    try:
        if args.check_only:
            normalized = validate_fingerprint(args.sha256)
            print(f"OK: valid SHA-256 ({normalized})")
            return 0
        normalized = write_assetlinks(args.sha256)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Updated {ASSETLINKS_PATH.relative_to(ROOT)}")
    print(f"  package: {PACKAGE_NAME}")
    print(f"  sha256:  {normalized}")
    print()
    print("Deploy to production:")
    print("  python scripts/deploy.py well_known --ask-pass")
    print()
    print("Verify:")
    print("  curl -sS https://masternoder.dk/.well-known/assetlinks.json | jq .")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
