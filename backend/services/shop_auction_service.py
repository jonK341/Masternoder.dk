"""
Shop v5 auction house service.

MVP scope: fixed-price listings backed by reserved user inventory. Bidding can
layer on later once transfers and profile ownership are reliable.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_FILENAME = "auction_listings.json"
MARKETPLACE_FEE_RATE = 0.05


class AuctionError(RuntimeError):
    """Raised for expected auction-house validation or fulfillment failures."""


def _log_root() -> str:
    base = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "logs",
    )
    root = os.path.join(base, "shop_marketplace")
    os.makedirs(root, exist_ok=True)
    return root


def _path() -> str:
    return os.path.join(_log_root(), _FILENAME)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> List[Dict[str, Any]]:
    path = _path()
    with _LOCK:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("listings"), list):
                    return data["listings"]
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return []


def _save(listings: List[Dict[str, Any]]) -> None:
    path = _path()
    with _LOCK:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"listings": listings}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)


def _public_listing(row: Dict[str, Any]) -> Dict[str, Any]:
    bids = row.get("bids") if isinstance(row.get("bids"), list) else []
    highest_bid = max((int(b.get("bid_coins") or 0) for b in bids if isinstance(b, dict) and b.get("status") == "active"), default=0)
    return {
        "listing_id": row.get("listing_id"),
        "seller_id": row.get("seller_id"),
        "buyer_id": row.get("buyer_id"),
        "item_id": row.get("item_id"),
        "item_name": row.get("item_name"),
        "quantity": int(row.get("quantity") or 0),
        "price_coins": int(row.get("price_coins") or 0),
        "fee_rate": float(row.get("fee_rate") or MARKETPLACE_FEE_RATE),
        "status": row.get("status") or "active",
        "created_at": row.get("created_at"),
        "sold_at": row.get("sold_at"),
        "cancelled_at": row.get("cancelled_at"),
        "bid_count": len([b for b in bids if isinstance(b, dict) and b.get("status") == "active"]),
        "highest_bid_coins": highest_bid,
        "bids": bids[-10:] if bids else [],
    }


def list_active_listings(*, seller_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    seller = (seller_id or "").strip()
    rows = []
    for row in _load():
        if (row.get("status") or "") != "active":
            continue
        if seller and (row.get("seller_id") or "") != seller:
            continue
        rows.append(_public_listing(row))
    rows.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return rows[: max(1, min(int(limit or 100), 200))]


def list_user_listings(user_id: str, limit: int = 100) -> Dict[str, List[Dict[str, Any]]]:
    uid = (user_id or "").strip()
    selling: List[Dict[str, Any]] = []
    bought: List[Dict[str, Any]] = []
    sold: List[Dict[str, Any]] = []
    for row in _load():
        public = _public_listing(row)
        if (row.get("seller_id") or "") == uid:
            if row.get("status") == "sold":
                sold.append(public)
            else:
                selling.append(public)
        if (row.get("buyer_id") or "") == uid:
            bought.append(public)
    for bucket in (selling, bought, sold):
        bucket.sort(key=lambda x: (x.get("sold_at") or x.get("created_at") or ""), reverse=True)
    cap = max(1, min(int(limit or 100), 200))
    return {"selling": selling[:cap], "bought": bought[:cap], "sold": sold[:cap]}


def create_listing(user_id: str, item_id: str, quantity: int, price_coins: int) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    qty = int(quantity or 0)
    price = int(price_coins or 0)
    if not uid or uid == "default_user":
        raise AuctionError("Create or log in to a profile before selling items")
    if not iid:
        raise AuctionError("item_id is required")
    if qty <= 0:
        raise AuctionError("quantity must be greater than zero")
    if price <= 0:
        raise AuctionError("price_coins must be greater than zero")

    from backend.services.shop_db_service import add_to_inventory, reserve_inventory

    reserved = reserve_inventory(uid, iid, qty)
    if not reserved:
        raise AuctionError("You do not have enough of this item to list it")

    listing = {
        "listing_id": str(uuid.uuid4())[:12],
        "seller_id": uid,
        "buyer_id": None,
        "item_id": iid,
        "item_name": reserved.get("item_name") or iid,
        "quantity": qty,
        "price_coins": price,
        "fee_rate": MARKETPLACE_FEE_RATE,
        "status": "active",
        "created_at": _now(),
        "sold_at": None,
        "cancelled_at": None,
        "bids": [],
    }

    try:
        with _LOCK:
            listings = _load()
            listings.append(listing)
            _save(listings)
    except Exception as ex:
        add_to_inventory(uid, iid, listing["item_name"], qty)
        raise AuctionError(f"Could not create listing: {ex}") from ex
    return _public_listing(listing)


def cancel_listing(user_id: str, listing_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    lid = (listing_id or "").strip()
    if not uid or not lid:
        raise AuctionError("user_id and listing_id are required")

    from backend.services.shop_db_service import add_to_inventory

    with _LOCK:
        listings = _load()
        for idx, row in enumerate(listings):
            if (row.get("listing_id") or "") != lid:
                continue
            if (row.get("seller_id") or "") != uid:
                raise AuctionError("Only the seller can cancel this listing")
            if row.get("status") != "active":
                raise AuctionError("Listing is not active")
            _release_all_bid_escrows(row)
            if not add_to_inventory(uid, row.get("item_id") or "", row.get("item_name") or "", int(row.get("quantity") or 1)):
                raise AuctionError("Could not restore item to inventory")
            row["status"] = "cancelled"
            row["cancelled_at"] = _now()
            listings[idx] = row
            _save(listings)
            return _public_listing(row)
    raise AuctionError("Listing not found")


def buy_listing(
    buyer_id: str,
    listing_id: str,
    *,
    payment_method: str = "coins",
    escrow_bid_id: Optional[str] = None,
) -> Dict[str, Any]:
    buyer = (buyer_id or "").strip()
    lid = (listing_id or "").strip()
    if not buyer or buyer == "default_user":
        raise AuctionError("Create or log in to a profile before buying from auction")
    if not lid:
        raise AuctionError("listing_id is required")

    from backend.services.shop_db_service import add_to_inventory, reserve_inventory
    from backend.services.unified_points_database import unified_points_db

    with _LOCK:
        listings = _load()
        idx = None
        row = None
        for i, candidate in enumerate(listings):
            if (candidate.get("listing_id") or "") == lid:
                idx = i
                row = candidate
                break
        if idx is None or row is None:
            raise AuctionError("Listing not found")
        if row.get("status") != "active":
            raise AuctionError("Listing is not active")
        seller = (row.get("seller_id") or "").strip()
        if seller == buyer:
            raise AuctionError("You cannot buy your own listing")

        method = (payment_method or "coins").strip().lower()
        if escrow_bid_id and method != "coins":
            raise AuctionError("escrow bids settle in coins only")
        if method not in ("coins", "mn2"):
            raise AuctionError("payment_method must be coins or mn2")
        price = int(row.get("price_coins") or 0)
        qty = int(row.get("quantity") or 1)
        item_id = row.get("item_id") or ""
        item_name = row.get("item_name") or item_id
        fee_rate = float(row.get("fee_rate") or MARKETPLACE_FEE_RATE)
        fee = int(round(price * fee_rate))
        seller_payout = max(0, price - fee)

        escrow_bid: Optional[Dict[str, Any]] = None
        if escrow_bid_id:
            bids = row.get("bids") if isinstance(row.get("bids"), list) else []
            escrow_bid = next(
                (
                    b for b in bids
                    if isinstance(b, dict)
                    and (b.get("bid_id") or "") == escrow_bid_id
                    and b.get("status") == "active"
                    and b.get("escrowed")
                ),
                None,
            )
            if not escrow_bid:
                raise AuctionError("Escrowed bid not found or already settled")
            if (escrow_bid.get("bidder_id") or "") != buyer:
                raise AuctionError("Bid does not belong to buyer")
            if int(escrow_bid.get("bid_coins") or 0) != price:
                raise AuctionError("Bid amount does not match listing price")

        points = unified_points_db.get_all_points(buyer)
        if not points.get("success"):
            raise AuctionError("Could not read buyer balance")
        buyer_points = points.get("points") or {}
        price_mn2 = 0.0
        fee_mn2 = 0.0
        seller_payout_mn2 = 0.0
        if escrow_bid:
            debit = {"success": True}
        elif method == "mn2":
            coins_per_mn2 = _coins_per_mn2()
            if coins_per_mn2 <= 0:
                raise AuctionError("MN2 price is not configured")
            price_mn2 = price / coins_per_mn2
            fee_mn2 = fee / coins_per_mn2
            seller_payout_mn2 = max(0.0, seller_payout / coins_per_mn2)
            buyer_mn2 = float(buyer_points.get("mn2_balance", 0) or 0)
            if buyer_mn2 == 0 and isinstance(buyer_points.get("systems"), dict):
                buyer_mn2 = float(buyer_points["systems"].get("mn2_balance", 0) or 0)
            if buyer_mn2 < price_mn2:
                raise AuctionError(f"Insufficient MN2. Need {price_mn2:.8f}, have {buyer_mn2:.8f}")
            debit = unified_points_db.add_points(
                user_id=buyer,
                point_type="mn2_balance",
                amount=-price_mn2,
                source="auction_purchase_mn2",
                metadata={"listing_id": lid, "item_id": item_id, "seller_id": seller, "fee_mn2": fee_mn2, "price_coins": price},
            )
        else:
            buyer_coins = int(buyer_points.get("coins") or 0)
            if buyer_coins < price:
                raise AuctionError(f"Insufficient coins. Need {price}, have {buyer_coins}")
            debit = unified_points_db.add_points(
                user_id=buyer,
                point_type="coins",
                amount=-price,
                source="auction_purchase",
                metadata={"listing_id": lid, "item_id": item_id, "seller_id": seller, "fee": fee},
            )
        if not debit.get("success", True):
            raise AuctionError("Could not debit buyer balance")

        if not add_to_inventory(buyer, item_id, item_name, qty):
            if escrow_bid:
                _release_bid_escrow(unified_points_db, escrow_bid, lid, reason="buyer_inventory_failed")
            else:
                _refund_buyer(unified_points_db, buyer, method, price, price_mn2, lid, item_id, "buyer_inventory_failed")
            raise AuctionError("Could not attach item to buyer inventory; payment refunded")

        if method == "mn2":
            payout = unified_points_db.add_points(
                user_id=seller,
                point_type="mn2_balance",
                amount=seller_payout_mn2,
                source="auction_sale_mn2",
                metadata={"listing_id": lid, "item_id": item_id, "buyer_id": buyer, "gross_mn2": price_mn2, "fee_mn2": fee_mn2, "price_coins": price},
            )
        else:
            payout = unified_points_db.add_points(
                user_id=seller,
                point_type="coins",
                amount=seller_payout,
                source="auction_sale",
                metadata={"listing_id": lid, "item_id": item_id, "buyer_id": buyer, "gross": price, "fee": fee},
            )
        if not payout.get("success", True):
            reserve_inventory(buyer, item_id, qty)
            if escrow_bid:
                _release_bid_escrow(unified_points_db, escrow_bid, lid, reason="seller_payout_failed")
            else:
                _refund_buyer(unified_points_db, buyer, method, price, price_mn2, lid, item_id, "seller_payout_failed")
            raise AuctionError("Could not pay seller; purchase was rolled back")

        if escrow_bid:
            escrow_bid["status"] = "settled"
            escrow_bid["escrowed"] = False
            escrow_bid["settled_at"] = _now()

        row["status"] = "sold"
        row["buyer_id"] = buyer
        row["sold_at"] = _now()
        row["payment_method"] = method
        row["fee_coins"] = fee
        row["seller_payout_coins"] = seller_payout
        row["price_mn2"] = price_mn2 if method == "mn2" else None
        row["fee_mn2"] = fee_mn2 if method == "mn2" else None
        row["seller_payout_mn2"] = seller_payout_mn2 if method == "mn2" else None
        listings[idx] = row
        _save(listings)

        return {
            "listing": _public_listing(row),
            "buyer_id": buyer,
            "seller_id": seller,
            "price_coins": price,
            "fee_coins": fee,
            "seller_payout_coins": seller_payout,
            "payment_method": method,
            "price_mn2": price_mn2 if method == "mn2" else None,
            "fee_mn2": fee_mn2 if method == "mn2" else None,
            "seller_payout_mn2": seller_payout_mn2 if method == "mn2" else None,
        }


def _highest_active_bid(bids: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    active = [b for b in bids if isinstance(b, dict) and b.get("status") == "active"]
    if not active:
        return None
    return max(active, key=lambda b: int(b.get("bid_coins") or 0))


def _release_bid_escrow(unified_points_db: Any, bid: Dict[str, Any], listing_id: str, *, reason: str) -> None:
    if not bid.get("escrowed"):
        return
    amount = int(bid.get("bid_coins") or 0)
    if amount <= 0:
        bid["escrowed"] = False
        return
    unified_points_db.add_points(
        user_id=str(bid.get("bidder_id") or ""),
        point_type="coins",
        amount=amount,
        source="marketplace_bid_escrow_release",
        metadata={"listing_id": listing_id, "bid_id": bid.get("bid_id"), "reason": reason},
    )
    bid["escrowed"] = False
    if bid.get("status") == "active":
        bid["status"] = "outbid" if reason == "outbid" else "released"


def _release_all_bid_escrows(row: Dict[str, Any]) -> None:
    from backend.services.unified_points_database import unified_points_db

    bids = row.get("bids") if isinstance(row.get("bids"), list) else []
    lid = row.get("listing_id") or ""
    for bid in bids:
        if isinstance(bid, dict) and bid.get("escrowed"):
            _release_bid_escrow(unified_points_db, bid, lid, reason="listing_cancelled")


def get_user_bid_escrow_summary(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    total = 0
    rows = []
    for listing in _load():
        if (listing.get("status") or "") != "active":
            continue
        bids = listing.get("bids") if isinstance(listing.get("bids"), list) else []
        for bid in bids:
            if not isinstance(bid, dict) or not bid.get("escrowed"):
                continue
            if (bid.get("bidder_id") or "") != uid:
                continue
            amt = int(bid.get("bid_coins") or 0)
            total += amt
            rows.append({
                "listing_id": listing.get("listing_id"),
                "item_id": listing.get("item_id"),
                "item_name": listing.get("item_name"),
                "bid_id": bid.get("bid_id"),
                "bid_coins": amt,
                "created_at": bid.get("created_at"),
            })
    return {"success": True, "user_id": uid, "escrow_coins_total": total, "escrows": rows}


def place_bid(user_id: str, listing_id: str, bid_coins: int) -> Dict[str, Any]:
    bidder = (user_id or "").strip()
    lid = (listing_id or "").strip()
    bid = int(bid_coins or 0)
    if not bidder or bidder == "default_user":
        raise AuctionError("Create or log in to a profile before bidding")
    if bid <= 0:
        raise AuctionError("bid_coins must be greater than zero")

    from backend.services.unified_points_database import unified_points_db

    with _LOCK:
        listings = _load()
        for idx, row in enumerate(listings):
            if (row.get("listing_id") or "") != lid:
                continue
            if row.get("status") != "active":
                raise AuctionError("Listing is not active")
            if (row.get("seller_id") or "") == bidder:
                raise AuctionError("You cannot bid on your own listing")
            bids = row.get("bids") if isinstance(row.get("bids"), list) else []
            highest = _highest_active_bid(bids)
            highest_amt = int(highest.get("bid_coins") or 0) if highest else 0
            if bid <= highest_amt:
                raise AuctionError(f"Bid must be higher than current highest bid ({highest_amt})")

            points = unified_points_db.get_all_points(bidder)
            if not points.get("success"):
                raise AuctionError("Could not read bidder balance")
            buyer_coins = int((points.get("points") or {}).get("coins") or 0)
            if buyer_coins < bid:
                raise AuctionError(f"Insufficient coins. Need {bid}, have {buyer_coins}")

            if highest and highest.get("escrowed"):
                _release_bid_escrow(unified_points_db, highest, lid, reason="outbid")

            debit = unified_points_db.add_points(
                user_id=bidder,
                point_type="coins",
                amount=-bid,
                source="marketplace_bid_escrow",
                metadata={"listing_id": lid, "bid_coins": bid},
            )
            if not debit.get("success", True):
                raise AuctionError("Could not escrow bid coins")

            bid_row = {
                "bid_id": str(uuid.uuid4())[:12],
                "bidder_id": bidder,
                "bid_coins": bid,
                "status": "active",
                "escrowed": True,
                "created_at": _now(),
            }
            bids.append(bid_row)
            row["bids"] = bids[-50:]
            listings[idx] = row
            _save(listings)
            return {"listing": _public_listing(row), "bid": bid_row, "escrow_coins": bid}
    raise AuctionError("Listing not found")


def accept_bid(user_id: str, listing_id: str, bid_id: str) -> Dict[str, Any]:
    seller = (user_id or "").strip()
    lid = (listing_id or "").strip()
    bid_ref = (bid_id or "").strip()
    with _LOCK:
        listings = _load()
        for idx, row in enumerate(listings):
            if (row.get("listing_id") or "") != lid:
                continue
            if row.get("status") != "active":
                raise AuctionError("Listing is not active")
            if (row.get("seller_id") or "") != seller:
                raise AuctionError("Only the seller can accept bids")
            bids = row.get("bids") if isinstance(row.get("bids"), list) else []
            bid = next((b for b in bids if isinstance(b, dict) and b.get("bid_id") == bid_ref and b.get("status") == "active"), None)
            if not bid:
                raise AuctionError("Active bid not found")
            if not bid.get("escrowed"):
                raise AuctionError("Bid has no escrowed funds")
            original_price = int(row.get("price_coins") or 0)
            row["price_coins"] = int(bid.get("bid_coins") or 0)
            row["accepted_bid_id"] = bid_ref
            listings[idx] = row
            _save(listings)
            try:
                result = buy_listing(
                    str(bid.get("bidder_id") or ""),
                    lid,
                    payment_method="coins",
                    escrow_bid_id=bid_ref,
                )
            except Exception:
                restored = _load()
                for r_idx, restored_row in enumerate(restored):
                    if restored_row.get("listing_id") == lid:
                        restored_row["price_coins"] = original_price
                        restored_row.pop("accepted_bid_id", None)
                        restored[r_idx] = restored_row
                        _save(restored)
                        break
                raise
            return result
    raise AuctionError("Listing not found")


def price_history(item_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    iid = (item_id or "").strip()
    rows: List[Dict[str, Any]] = []
    for row in _load():
        if row.get("status") != "sold":
            continue
        if iid and row.get("item_id") != iid:
            continue
        rows.append({
            "item_id": row.get("item_id"),
            "item_name": row.get("item_name"),
            "price_coins": int(row.get("price_coins") or 0),
            "payment_method": row.get("payment_method") or "coins",
            "sold_at": row.get("sold_at"),
        })
    rows.sort(key=lambda x: x.get("sold_at") or "", reverse=True)
    return rows[: max(1, min(int(limit or 20), 100))]


def _coins_per_mn2() -> float:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "data", "mn2_config.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return float(data.get("coins_per_mn2") or 100)
    except Exception:
        return 100.0


def _refund_buyer(unified_points_db: Any, buyer: str, method: str, price: int, price_mn2: float, listing_id: str, item_id: str, reason: str) -> None:
    if method == "mn2":
        unified_points_db.add_points(
            user_id=buyer,
            point_type="mn2_balance",
            amount=price_mn2,
            source="auction_purchase_mn2_refund",
            metadata={"listing_id": listing_id, "item_id": item_id, "reason": reason, "price_coins": price},
        )
        return
    unified_points_db.add_points(
        user_id=buyer,
        point_type="coins",
        amount=price,
        source="auction_purchase_refund",
        metadata={"listing_id": listing_id, "item_id": item_id, "reason": reason},
    )
