"""Trophy chain anchor queue — L2 commitment layer (plan 003 BM-U6 Phase 1)."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_QUEUE_PATH = os.path.join(_BASE, "data", "trophy_anchor_queue.json")
_REGISTRY_PATH = os.path.join(_BASE, "data", "trophy_anchor_registry.json")
_CONFIG_PATH = os.path.join(_BASE, "data", "trophy_anchor_config.json")

ANCHOR_VERSION = "trophy-anchor-v1"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with _LOCK:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        return True
    except Exception:
        return False


def get_config() -> Dict[str, Any]:
    return _read_json(
        _CONFIG_PATH,
        {
            "enabled": True,
            "auto_process_on_queue": True,
            "explorer_tx_base": "/explorer?tx=",
        },
    )


def anchor_commitment(edition_key: str, proof_hash: str) -> str:
    raw = f"{ANCHOR_VERSION}|{(edition_key or '').strip()}|{(proof_hash or '').strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def queue_edition_anchor(
    *,
    user_id: str,
    item_id: str,
    edition_no: int,
    edition_key: str,
    proof_hash: str,
    source: str = "grant",
) -> Dict[str, Any]:
    """Enqueue a trophy edition for anchor commitment (best-effort)."""
    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "anchor_disabled"}

    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    ekey = (edition_key or "").strip()
    phash = (proof_hash or "").strip()
    if not uid or not iid or not ekey:
        return {"success": False, "error": "missing_edition_fields"}

    commitment = anchor_commitment(ekey, phash)
    job_id = f"{ekey}:{phash[:16]}"

    with _LOCK:
        doc = _read_json(_QUEUE_PATH, {"jobs": []})
        jobs = doc.setdefault("jobs", [])
        for job in jobs:
            if isinstance(job, dict) and job.get("job_id") == job_id:
                return {"success": True, "duplicate": True, "job_id": job_id, "anchor_commitment": commitment}

        jobs.append(
            {
                "job_id": job_id,
                "user_id": uid,
                "item_id": iid,
                "edition_no": int(edition_no),
                "edition_key": ekey,
                "proof_hash": phash,
                "anchor_commitment": commitment,
                "source": (source or "grant").strip(),
                "status": "pending",
                "queued_at": _iso(),
            }
        )
        doc["updated_at"] = _iso()
        _write_json(_QUEUE_PATH, doc)

    _patch_edition_anchor(uid, iid, int(edition_no), {"anchor_status": "pending", "anchor_commitment": commitment})

    if cfg.get("auto_process_on_queue", True):
        try:
            process_anchor_queue(limit=1, job_id=job_id)
        except Exception:
            pass

    return {"success": True, "job_id": job_id, "anchor_commitment": commitment, "anchor_status": "pending"}


def _patch_edition_anchor(user_id: str, item_id: str, edition_no: int, fields: Dict[str, Any]) -> None:
    try:
        from backend.services.trophy_fulfillment_service import get_edition, _editions_file_path

        path = _editions_file_path(user_id)
        doc = _read_json(path, {"editions": []})
        editions = doc.get("editions") or []
        for idx, row in enumerate(editions):
            if not isinstance(row, dict):
                continue
            if (row.get("item_id") or "") != item_id:
                continue
            try:
                if int(row.get("edition_no") or 0) != int(edition_no):
                    continue
            except (TypeError, ValueError):
                continue
            editions[idx] = {**row, **fields}
            doc["editions"] = editions
            doc["updated_at"] = _iso()
            _write_json(path, doc)
            return
    except Exception:
        pass


def process_anchor_queue(*, limit: int = 20, job_id: Optional[str] = None) -> Dict[str, Any]:
    """Commit pending anchors to registry (Phase 1: ledger registry, no chain tx yet)."""
    cfg = get_config()
    processed: List[Dict[str, Any]] = []

    with _LOCK:
        qdoc = _read_json(_QUEUE_PATH, {"jobs": []})
        jobs = [j for j in (qdoc.get("jobs") or []) if isinstance(j, dict)]
        rdoc = _read_json(_REGISTRY_PATH, {"anchors": {}})
        anchors = rdoc.setdefault("anchors", {})

        for job in jobs:
            if job.get("status") != "pending":
                continue
            if job_id and job.get("job_id") != job_id:
                continue
            if len(processed) >= max(1, int(limit or 20)):
                break

            ekey = job.get("edition_key") or ""
            commitment = job.get("anchor_commitment") or anchor_commitment(ekey, job.get("proof_hash") or "")
            entry = {
                "edition_key": ekey,
                "user_id": job.get("user_id"),
                "item_id": job.get("item_id"),
                "edition_no": job.get("edition_no"),
                "proof_hash": job.get("proof_hash"),
                "anchor_commitment": commitment,
                "anchor_status": "committed",
                "on_chain_mint": False,
                "anchor_txid": None,
                "anchor_explorer_url": None,
                "committed_at": _iso(),
                "source": job.get("source"),
            }
            anchors[ekey] = entry
            job["status"] = "committed"
            job["committed_at"] = _iso()

            _patch_edition_anchor(
                str(job.get("user_id") or ""),
                str(job.get("item_id") or ""),
                int(job.get("edition_no") or 0),
                {
                    "anchor_status": "committed",
                    "anchor_commitment": commitment,
                    "on_chain_mint": False,
                },
            )
            processed.append({"edition_key": ekey, "anchor_commitment": commitment})

        qdoc["jobs"] = jobs
        qdoc["updated_at"] = _iso()
        rdoc["anchors"] = anchors
        rdoc["updated_at"] = _iso()
        _write_json(_QUEUE_PATH, qdoc)
        _write_json(_REGISTRY_PATH, rdoc)

    return {"success": True, "processed": len(processed), "entries": processed}


def get_anchor_status(edition_key: str) -> Dict[str, Any]:
    ekey = (edition_key or "").strip()
    if not ekey:
        return {"success": False, "error": "edition_key_required"}

    rdoc = _read_json(_REGISTRY_PATH, {"anchors": {}})
    entry = (rdoc.get("anchors") or {}).get(ekey)
    if not entry:
        return {
            "success": True,
            "edition_key": ekey,
            "anchor_status": "none",
            "on_chain_mint": False,
            "message": "No anchor committed yet",
        }

    return {
        "success": True,
        "edition_key": ekey,
        "anchor_status": entry.get("anchor_status") or "committed",
        "anchor_commitment": entry.get("anchor_commitment"),
        "anchor_txid": entry.get("anchor_txid"),
        "anchor_explorer_url": entry.get("anchor_explorer_url"),
        "on_chain_mint": False,
        "committed_at": entry.get("committed_at"),
    }
