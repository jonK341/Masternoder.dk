"""Trophy chain anchor queue — L2 commitment layer (plan 003 BM-U6 Phase 1–2)."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_QUEUE_PATH = os.path.join(_BASE, "data", "trophy_anchor_queue.json")
_REGISTRY_PATH = os.path.join(_BASE, "data", "trophy_anchor_registry.json")
_CONFIG_PATH = os.path.join(_BASE, "data", "trophy_anchor_config.json")

ANCHOR_VERSION = "trophy-anchor-v1"
_OP_RETURN_MAGIC = b"TRO\x01"


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
            "broadcast_on_chain": False,
            "explorer_tx_base": "/explorer?tx=",
        },
    )


def anchor_commitment(edition_key: str, proof_hash: str) -> str:
    raw = f"{ANCHOR_VERSION}|{(edition_key or '').strip()}|{(proof_hash or '').strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def op_return_payload_hex(anchor_commitment_hex: str) -> str:
    """Build OP_RETURN data hex: magic + 32-byte commitment digest."""
    digest = (anchor_commitment_hex or "").strip().lower()
    if len(digest) != 64:
        raise ValueError("anchor_commitment must be 64 hex chars")
    payload = _OP_RETURN_MAGIC + bytes.fromhex(digest)
    if len(payload) > 80:
        raise ValueError("op_return_payload exceeds 80 bytes")
    return payload.hex()


def explorer_url_for_tx(txid: str) -> str:
    cfg = get_config()
    base = (cfg.get("explorer_tx_base") or "/explorer?tx=").strip()
    if not base.endswith("=") and "?" not in base:
        base = base.rstrip("/") + "/"
    if base.endswith("="):
        return f"{base}{txid}"
    return f"{base}{txid}"


def broadcast_anchor_op_return(anchor_commitment_hex: str) -> Dict[str, Any]:
    """Broadcast OP_RETURN tx with trophy anchor payload (plan 003 A-U5)."""
    try:
        payload_hex = op_return_payload_hex(anchor_commitment_hex)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    try:
        from backend.services import mn2_rpc_client as rpc
    except Exception as exc:
        return {"success": False, "error": f"rpc_import_failed: {exc}"}

    raw = rpc.createrawtransaction([], [{"data": payload_hex}])
    if raw.get("error"):
        return {"success": False, "error": raw["error"], "stage": "createrawtransaction"}

    hex_tx = raw.get("result")
    if not hex_tx:
        return {"success": False, "error": "empty_raw_tx", "stage": "createrawtransaction"}

    funded = rpc.fundrawtransaction(hex_tx)
    if funded.get("error"):
        return {"success": False, "error": funded["error"], "stage": "fundrawtransaction"}

    funded_hex = (funded.get("result") or {}).get("hex") if isinstance(funded.get("result"), dict) else funded.get("result")
    if not funded_hex:
        return {"success": False, "error": "empty_funded_tx", "stage": "fundrawtransaction"}

    signed = rpc.signrawtransactionwithwallet(funded_hex)
    if signed.get("error"):
        return {"success": False, "error": signed["error"], "stage": "signrawtransactionwithwallet"}

    signed_result = signed.get("result") or {}
    if isinstance(signed_result, dict) and not signed_result.get("complete"):
        return {"success": False, "error": "incomplete_signature", "stage": "signrawtransactionwithwallet"}

    signed_hex = signed_result.get("hex") if isinstance(signed_result, dict) else signed_result
    if not signed_hex:
        return {"success": False, "error": "empty_signed_tx", "stage": "signrawtransactionwithwallet"}

    sent = rpc.sendrawtransaction(signed_hex)
    if sent.get("error"):
        return {"success": False, "error": sent["error"], "stage": "sendrawtransaction"}

    txid = sent.get("result")
    if not txid:
        return {"success": False, "error": "empty_txid", "stage": "sendrawtransaction"}

    return {
        "success": True,
        "anchor_txid": str(txid),
        "anchor_explorer_url": explorer_url_for_tx(str(txid)),
        "op_return_hex": payload_hex,
    }


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
        from backend.services.trophy_fulfillment_service import _editions_file_path

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


def _apply_anchor_broadcast(
    entry: Dict[str, Any],
    *,
    commitment: str,
    broadcast_result: Dict[str, Any],
) -> Dict[str, Any]:
    txid = broadcast_result.get("anchor_txid")
    explorer = broadcast_result.get("anchor_explorer_url")
    entry.update(
        {
            "anchor_status": "anchored",
            "anchor_txid": txid,
            "anchor_explorer_url": explorer,
            "anchored_at": _iso(),
            "on_chain_mint": False,
        }
    )
    _patch_edition_anchor(
        str(entry.get("user_id") or ""),
        str(entry.get("item_id") or ""),
        int(entry.get("edition_no") or 0),
        {
            "anchor_status": "anchored",
            "anchor_commitment": commitment,
            "anchor_txid": txid,
            "anchor_explorer_url": explorer,
            "on_chain_mint": False,
        },
    )
    return entry


def _maybe_broadcast_entry(entry: Dict[str, Any], cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    if not cfg.get("broadcast_on_chain", False):
        return entry, None
    if entry.get("anchor_txid"):
        return entry, None
    commitment = entry.get("anchor_commitment") or ""
    if not commitment:
        return entry, None

    result = broadcast_anchor_op_return(commitment)
    if not result.get("success"):
        return entry, result

    updated = _apply_anchor_broadcast(entry, commitment=commitment, broadcast_result=result)
    return updated, result


def process_anchor_queue(*, limit: int = 20, job_id: Optional[str] = None) -> Dict[str, Any]:
    """Commit pending anchors to registry; optionally broadcast OP_RETURN when configured."""
    cfg = get_config()
    processed: List[Dict[str, Any]] = []
    broadcasted: List[Dict[str, Any]] = []

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
            entry, bcast = _maybe_broadcast_entry(entry, cfg)
            if bcast and bcast.get("success"):
                job["status"] = "anchored"
                job["anchored_at"] = _iso()
                broadcasted.append({"edition_key": ekey, "anchor_txid": entry.get("anchor_txid")})
            else:
                job["status"] = "committed"
                job["committed_at"] = _iso()

            anchors[ekey] = entry

            if entry.get("anchor_status") == "anchored":
                pass  # edition already patched in _apply_anchor_broadcast
            else:
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

            processed.append(
                {
                    "edition_key": ekey,
                    "anchor_commitment": commitment,
                    "anchor_status": entry.get("anchor_status"),
                    "anchor_txid": entry.get("anchor_txid"),
                    "broadcast_error": (bcast or {}).get("error") if bcast and not bcast.get("success") else None,
                }
            )

        qdoc["jobs"] = jobs
        qdoc["updated_at"] = _iso()
        rdoc["anchors"] = anchors
        rdoc["updated_at"] = _iso()
        _write_json(_QUEUE_PATH, qdoc)
        _write_json(_REGISTRY_PATH, rdoc)

    return {
        "success": True,
        "processed": len(processed),
        "broadcasted": len(broadcasted),
        "entries": processed,
    }


def broadcast_anchor_queue(*, limit: int = 10, edition_key: Optional[str] = None) -> Dict[str, Any]:
    """Ops: broadcast OP_RETURN for committed registry entries missing anchor_txid."""
    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "anchor_disabled"}

    broadcasted: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    with _LOCK:
        rdoc = _read_json(_REGISTRY_PATH, {"anchors": {}})
        anchors = rdoc.setdefault("anchors", {})
        qdoc = _read_json(_QUEUE_PATH, {"jobs": []})
        jobs = qdoc.get("jobs") or []

        for ekey, entry in list(anchors.items()):
            if not isinstance(entry, dict):
                continue
            if edition_key and ekey != edition_key:
                continue
            if entry.get("anchor_txid"):
                continue
            if entry.get("anchor_status") not in ("committed", "anchored", None):
                continue
            if len(broadcasted) + len(errors) >= max(1, int(limit or 10)):
                break

            commitment = entry.get("anchor_commitment") or ""
            result = broadcast_anchor_op_return(commitment)
            if not result.get("success"):
                errors.append({"edition_key": ekey, "error": result.get("error"), "stage": result.get("stage")})
                continue

            entry = _apply_anchor_broadcast(entry, commitment=commitment, broadcast_result=result)
            anchors[ekey] = entry

            for job in jobs:
                if isinstance(job, dict) and job.get("edition_key") == ekey:
                    job["status"] = "anchored"
                    job["anchored_at"] = _iso()
                    break

            broadcasted.append({"edition_key": ekey, "anchor_txid": entry.get("anchor_txid")})

        rdoc["anchors"] = anchors
        rdoc["updated_at"] = _iso()
        qdoc["jobs"] = jobs
        qdoc["updated_at"] = _iso()
        _write_json(_REGISTRY_PATH, rdoc)
        _write_json(_QUEUE_PATH, qdoc)

    return {
        "success": True,
        "broadcasted": len(broadcasted),
        "errors": errors,
        "entries": broadcasted,
    }


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

    status = entry.get("anchor_status") or ("anchored" if entry.get("anchor_txid") else "committed")
    return {
        "success": True,
        "edition_key": ekey,
        "anchor_status": status,
        "anchor_commitment": entry.get("anchor_commitment"),
        "anchor_txid": entry.get("anchor_txid"),
        "anchor_explorer_url": entry.get("anchor_explorer_url"),
        "on_chain_mint": False,
        "committed_at": entry.get("committed_at"),
        "anchored_at": entry.get("anchored_at"),
    }
