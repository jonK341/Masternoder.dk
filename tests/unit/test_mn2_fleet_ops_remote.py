"""Unit tests for mn2_masternode_fleet_ops_remote watch target helpers."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "mn2_masternode_fleet_ops_remote.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("mn2_masternode_fleet_ops_remote", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_resolve_watch_target_default():
    mod = _load_module()
    target, mode = mod.resolve_watch_target(target=None, target_all=False)
    assert target == 1
    assert mode == "fixed"


def test_resolve_watch_target_all():
    mod = _load_module()
    target, mode = mod.resolve_watch_target(target=None, target_all=True)
    assert target == 1
    assert mode == "hosted"


def test_resolve_watch_target_explicit():
    mod = _load_module()
    target, mode = mod.resolve_watch_target(target=5, target_all=False)
    assert target == 5
    assert mode == "fixed"


def test_build_remote_injects_watch_target_placeholders():
    mod = _load_module()
    remote = mod.build_remote(
        install=False,
        start=True,
        watch=True,
        interval=30,
        max_loops=10,
        fix_privkey=False,
        watch_target=3,
        watch_target_mode="fixed",
    )
    assert 'WATCH_TARGET="3"' in remote or "WATCH_TARGET=3" in remote or '__WATCH_TARGET__' not in remote
    assert "WATCH_TARGET_MODE" in remote or '__WATCH_TARGET_MODE__' not in remote
    assert "sync_ping_targets" in remote
    assert "enabled_with_activetime" in remote
    assert "sync-ping-targets" in remote
