"""
Centralized MN2 block-explorer URL builders.

Supports Chainz `.dws` query URLs and iquidus/eiquidus path URLs (`/tx/`, `/address/`).
Config lives in data/mn2_config.json (explorer_base_url, explorer_kind, fallback, local API).
Environment overrides (when set): MN2_EXPLORER_BASE_URL, MN2_EXPLORER_FALLBACK_BASE_URL,
MN2_EXPLORER_LOCAL_API_URL, MN2_EXPLORER_KIND.
"""
import json
import os
from typing import Any, Dict, Optional

_DEFAULT_CHAINZ = "https://chainz.cryptoid.info/mn2/"


def _config_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data", "mn2_config.json")


def _env_overlay(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Apply self-hosted explorer env vars over mn2_config.json when present."""
    out = dict(cfg)
    for key, env_key in (
        ("explorer_base_url", "MN2_EXPLORER_BASE_URL"),
        ("explorer_fallback_base_url", "MN2_EXPLORER_FALLBACK_BASE_URL"),
        ("explorer_local_api_url", "MN2_EXPLORER_LOCAL_API_URL"),
        ("explorer_kind", "MN2_EXPLORER_KIND"),
    ):
        val = (os.environ.get(env_key) or "").strip()
        if val:
            out[key] = val
    return out


def load_explorer_config() -> Dict[str, Any]:
    path = _config_path()
    cfg: Dict[str, Any] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    cfg = loaded
        except Exception:
            pass
    return _env_overlay(cfg)


def explorer_base_url(cfg: Optional[Dict[str, Any]] = None) -> str:
    cfg = cfg if cfg is not None else load_explorer_config()
    url = (cfg.get("explorer_base_url") or "").strip()
    return url or _DEFAULT_CHAINZ


def explorer_fallback_base_url(cfg: Optional[Dict[str, Any]] = None) -> str:
    cfg = cfg if cfg is not None else load_explorer_config()
    fb = (cfg.get("explorer_fallback_base_url") or "").strip()
    return fb or _DEFAULT_CHAINZ


def explorer_local_api_url(cfg: Optional[Dict[str, Any]] = None) -> str:
    cfg = cfg if cfg is not None else load_explorer_config()
    return (cfg.get("explorer_local_api_url") or "").strip().rstrip("/")


def explorer_kind(cfg: Optional[Dict[str, Any]] = None) -> str:
    """Return 'chainz' or 'iquidus' (eiquidus uses the same URL shape as iquidus)."""
    cfg = cfg if cfg is not None else load_explorer_config()
    kind = (cfg.get("explorer_kind") or "").strip().lower()
    if kind in ("iquidus", "eiquidus", "local"):
        return "iquidus"
    if kind == "chainz":
        return "chainz"
    base = explorer_base_url(cfg).lower()
    if "chainz.cryptoid" in base:
        return "chainz"
    return "iquidus"


def explorer_tx_url(txid: str, cfg: Optional[Dict[str, Any]] = None) -> str:
    if not (txid or "").strip():
        return ""
    base = explorer_base_url(cfg).rstrip("/")
    txid = txid.strip()
    if explorer_kind(cfg) == "chainz":
        return f"{base}/tx.dws?txid={txid}"
    return f"{base}/tx/{txid}"


def explorer_address_url(address: str, cfg: Optional[Dict[str, Any]] = None) -> str:
    if not (address or "").strip():
        return ""
    base = explorer_base_url(cfg).rstrip("/")
    address = address.strip()
    if explorer_kind(cfg) == "chainz":
        return f"{base}/address.dws?addr={address}"
    return f"{base}/address/{address}"


def explorer_block_url(block_hash_or_height: str, cfg: Optional[Dict[str, Any]] = None) -> str:
    if not (block_hash_or_height or "").strip():
        return ""
    base = explorer_base_url(cfg).rstrip("/")
    ref = str(block_hash_or_height).strip()
    if explorer_kind(cfg) == "chainz":
        return f"{base}/block.dws?id={ref}"
    return f"{base}/block/{ref}"
