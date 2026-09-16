"""Post-transfer hooks: provenance, L2 re-anchor, Discord fanout (plan 003 A-U3)."""
from __future__ import annotations

from typing import Any, Dict, Optional


def on_edition_transferred(
    edition: Dict[str, Any],
    *,
    from_user_id: str,
    to_user_id: str,
    transfer_type: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ekey = (edition.get("edition_key") or "").strip()
    iid = (edition.get("item_id") or "").strip()
    eno = int(edition.get("edition_no") or 0)
    phash = (edition.get("proof_hash") or "").strip()
    out: Dict[str, Any] = {"success": True, "edition_key": ekey}

    try:
        from backend.services.trophy_provenance_service import append_event

        out["provenance"] = append_event(
            ekey,
            transfer_type,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            user_id=to_user_id,
            metadata={**(extra or {}), "item_id": iid, "edition_no": eno},
        )
    except Exception as exc:
        out["provenance"] = {"success": False, "error": str(exc)}

    if ekey and phash and to_user_id and iid and eno:
        try:
            from backend.services.trophy_anchor_service import queue_transfer_reanchor

            out["anchor"] = queue_transfer_reanchor(
                user_id=to_user_id,
                item_id=iid,
                edition_no=eno,
                edition_key=ekey,
                proof_hash=phash,
                source=transfer_type,
                from_user_id=from_user_id,
            )
        except Exception as exc:
            out["anchor"] = {"success": False, "error": str(exc)}

    if transfer_type == "auction_sale":
        try:
            from backend.services.trophy_discord_fanout import post_trophy_sale

            sale_payload = {
                "edition_key": ekey,
                "item_id": iid,
                "seller_id": from_user_id,
                "buyer_id": to_user_id,
                "gif_url": edition.get("gif_url") or edition.get("edition_gif_url"),
                "license_number": edition.get("license_number"),
                "block_height": edition.get("block_height"),
                **(extra or {}),
            }
            out["discord"] = post_trophy_sale(sale_payload)
        except Exception:
            pass

    return out


def on_edition_granted(edition: Dict[str, Any], user_id: str, acquired_via: str) -> None:
    ekey = (edition.get("edition_key") or "").strip()
    if not ekey:
        return
    try:
        from backend.services.trophy_provenance_service import append_event

        append_event(
            ekey,
            "minted",
            user_id=user_id,
            metadata={
                "acquired_via": acquired_via,
                "item_id": edition.get("item_id"),
                "edition_no": edition.get("edition_no"),
                "license_number": edition.get("license_number"),
            },
        )
    except Exception:
        pass
