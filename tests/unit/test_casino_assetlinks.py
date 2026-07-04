"""Digital Asset Links validation for dk.masternoder.casino."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ASSETLINKS_PATH = ROOT / "static" / ".well-known" / "assetlinks.json"

from scripts.casino_play_assetlinks_update import (  # noqa: E402
    PLACEHOLDER,
    TRUNCATED_BAD,
    build_assetlinks,
    fingerprint_from_file,
    load_assetlinks,
    normalize_sha256,
    validate_fingerprint,
)

VALID_SHA = "AA" * 32  # 64 hex chars


def test_assetlinks_json_structure():
    data = load_assetlinks()
    assert data[0]["target"]["package_name"] == "dk.masternoder.casino"
    assert data[0]["relation"] == ["delegate_permission/common.handle_all_urls"]


def test_normalize_sha256_accepts_colons_and_lowercase():
    assert normalize_sha256("aa:bb:" + "cc" * 30) == ("AABB" + "CC" * 30)


def test_validate_fingerprint_rejects_placeholder():
    with pytest.raises(ValueError, match="Placeholder"):
        validate_fingerprint(PLACEHOLDER)


def test_validate_fingerprint_rejects_truncated_bad():
    with pytest.raises(ValueError, match="truncated|64 hex"):
        validate_fingerprint(TRUNCATED_BAD)


def test_validate_fingerprint_rejects_short_hex():
    with pytest.raises(ValueError, match="64 hex"):
        validate_fingerprint("ABCD1234")


def test_validate_fingerprint_accepts_valid():
    assert validate_fingerprint(VALID_SHA) == VALID_SHA
    colon_form = ":".join(VALID_SHA[i : i + 2] for i in range(0, 64, 2))
    assert validate_fingerprint(colon_form) == VALID_SHA


def test_build_assetlinks_payload():
    payload = build_assetlinks(VALID_SHA)
    assert payload[0]["target"]["sha256_cert_fingerprints"] == [VALID_SHA]


@pytest.mark.skipif(
    os.environ.get("CASINO_ASSETLINKS_STRICT") != "1",
    reason="Set CASINO_ASSETLINKS_STRICT=1 after Play SHA is in repo",
)
def test_repo_fingerprint_is_production_ready():
    fp = fingerprint_from_file()
    assert fp != PLACEHOLDER
    assert fp != TRUNCATED_BAD
    assert validate_fingerprint(fp) == fp


def test_repo_fingerprint_not_truncated():
    """Always fail if committed fingerprint is truncated or the old bad value."""
    fp = fingerprint_from_file()
    if fp == PLACEHOLDER:
        pytest.skip("Placeholder expected until Play App Signing SHA is set")
    with open(ASSETLINKS_PATH, encoding="utf-8") as fh:
        raw = json.load(fh)
    committed = raw[0]["target"]["sha256_cert_fingerprints"][0]
    assert committed != TRUNCATED_BAD
    assert len(committed.replace(":", "")) >= 64
