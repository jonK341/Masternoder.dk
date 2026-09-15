"""Minimal PDF writer for checked shop orders. No secrets, no extra deps."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence


A4_WIDTH = 595.28
A4_HEIGHT = 841.89
MARGIN = 40.0


def _pdf_escape(text: str) -> str:
    return (
        str(text or "")
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _latin(text: str) -> str:
    return str(text or "").encode("latin-1", "replace").decode("latin-1")


def format_price_label(row: Dict[str, Any]) -> str:
    row = row or {}
    if row.get("amount_label"):
        return str(row["amount_label"])
    source = str(row.get("source") or "")
    if source == "listing" or row.get("listing_id"):
        coins = row.get("price_paid_coins")
        if coins is None:
            coins = row.get("price_coins")
        try:
            return f"{int(coins or 0)} coins"
        except (TypeError, ValueError):
            return f"{coins} coins"
    if source in ("masternode_hosting", "hosting"):
        method = str(row.get("payment_method") or row.get("price_type") or "").lower()
        if method in ("coins", "credits") and row.get("coins_total"):
            return f"{int(row.get('coins_total') or 0)} coins"
        if method in ("mn2", "mn2_onchain") and row.get("mn2_total"):
            suffix = " (on-chain)" if method == "mn2_onchain" else ""
            try:
                return f"{float(row.get('mn2_total') or 0):.4f} MN2{suffix}"
            except (TypeError, ValueError):
                return f"{row.get('mn2_total')} MN2{suffix}"
        usd = row.get("usd_total")
        try:
            if usd is not None:
                return f"${float(usd):.2f} PayPal"
        except (TypeError, ValueError):
            pass
        return "PayPal"
    price_type = str(row.get("price_type") or "").lower()
    points = row.get("price_paid_points")
    if price_type == "coins":
        return f"{row.get('price_paid_coins') or 0} coins"
    if price_type in ("paypal", "paypal_mn2_hosting"):
        usd = None
        if isinstance(points, dict) and points.get("usd") is not None:
            try:
                usd = float(points["usd"])
            except (TypeError, ValueError):
                usd = None
        if usd is not None:
            return f"${usd:.2f} PayPal"
        return "PayPal"
    if price_type in ("mn2", "mn2_onchain"):
        mn2_paid = points.get("mn2") if isinstance(points, dict) else points
        try:
            mn2_text = f"{float(mn2_paid):.4f}"
        except (TypeError, ValueError):
            mn2_text = str(mn2_paid or "")
        suffix = " (on-chain)" if price_type == "mn2_onchain" else ""
        return f"{mn2_text} MN2{suffix}"
    if price_type in ("points", "unified_points"):
        if isinstance(points, dict) and points:
            keys = list(points.keys())
            if len(keys) == 1:
                return f"{points[keys[0]]} {keys[0]}"
        return "points"
    if row.get("price_paid_coins"):
        return f"{row.get('price_paid_coins')} coins"
    return "—"


def format_status_label(row: Dict[str, Any]) -> str:
    raw = str(row.get("purchase_status") or row.get("status") or "completed").strip()
    if not raw:
        return "Completed"
    return raw.replace("_", " ").title()


def format_date_label(row: Dict[str, Any]) -> str:
    raw = row.get("sold_at") or row.get("paid_at") or row.get("created_at") or ""
    text = str(raw).strip()
    if not text:
        return "—"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return text[:32]


def _wrap(text: str, width: int) -> List[str]:
    words = re.split(r"\s+", str(text or "").strip()) or [""]
    lines: List[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) <= width or not current:
            current = trial
            continue
        lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines or [""]


def _page_stream(title: str, meta_lines: Sequence[str], headers: Sequence[str], rows: Sequence[Sequence[str]], page_no: int, page_count: int) -> str:
    commands = [
        "BT",
        "/F2 16 Tf",
        "0.05 0.75 0.53 rg",
        f"1 0 0 1 {MARGIN:.2f} {A4_HEIGHT - 56:.2f} Tm",
        f"({_pdf_escape(_latin(title))}) Tj",
        "0 g",
        "/F1 9 Tf",
    ]
    y = A4_HEIGHT - 78
    for line in meta_lines:
        commands.append(f"1 0 0 1 {MARGIN:.2f} {y:.2f} Tm")
        commands.append(f"({_pdf_escape(_latin(line))}) Tj")
        y -= 13
    y -= 8
    col_x = [MARGIN, 58, 250, 290, 390, 470]
    commands.append("/F2 8 Tf")
    for i, header in enumerate(headers):
        commands.append(f"1 0 0 1 {col_x[i]:.2f} {y:.2f} Tm")
        commands.append(f"({_pdf_escape(_latin(header))}) Tj")
    y -= 6
    commands.append("ET")
    commands.append("0.70 0.70 0.70 RG")
    commands.append("0.4 w")
    commands.append(f"{MARGIN:.2f} {y:.2f} m {A4_WIDTH - MARGIN:.2f} {y:.2f} l S")
    commands.append("BT")
    commands.append("/F1 8 Tf")
    y -= 14
    for row in rows:
        name_lines = _wrap(row[1], 34)
        block_h = max(12, 11 * len(name_lines))
        if y - block_h < 50:
            break
        cells = [row[0], name_lines[0], row[2], row[3], row[4], row[5]]
        for i, cell in enumerate(cells):
            commands.append(f"1 0 0 1 {col_x[i]:.2f} {y:.2f} Tm")
            commands.append(f"({_pdf_escape(_latin(cell))}) Tj")
        extra_y = y
        for extra in name_lines[1:]:
            extra_y -= 11
            commands.append(f"1 0 0 1 {col_x[1]:.2f} {extra_y:.2f} Tm")
            commands.append(f"({_pdf_escape(_latin(extra))}) Tj")
        y -= block_h + 4
    commands.append("ET")
    commands.append("BT")
    commands.append("/F1 8 Tf")
    commands.append("0.45 g")
    commands.append(f"1 0 0 1 {MARGIN:.2f} 28.00 Tm")
    commands.append(f"({_pdf_escape(_latin(f'Page {page_no} of {page_count}'))}) Tj")
    commands.append("ET")
    return "\n".join(commands) + "\n"


def _pack_objects(objects: List[bytes]) -> bytes:
    out = [b"%PDF-1.4\n"]
    offsets = [0]
    pos = len(out[0])
    for i, body in enumerate(objects, start=1):
        header = f"{i} 0 obj\n".encode("ascii")
        chunk = header + body + b"\nendobj\n"
        offsets.append(pos)
        out.append(chunk)
        pos += len(chunk)
    xref_pos = pos
    xref = [f"xref\n0 {len(objects) + 1}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode("ascii")
    return b"".join(out + xref) + trailer


def build_orders_pdf(
    *,
    user_id: str,
    rows: Iterable[Dict[str, Any]],
    generated_at: str | None = None,
) -> bytes:
    """Build a printable PDF of checked purchase + stall rows."""
    generated = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = "Shop orders"
    headers = ["#", "Item", "Qty", "Price", "Status", "Date"]
    table_rows: List[List[str]] = []
    for idx, row in enumerate(rows or [], start=1):
        name = str(row.get("item_name") or row.get("item_id") or "Item")
        source = str(row.get("source") or "purchase")
        if source == "listing":
            name = f"{name} (stall)"
        elif source in ("masternode_hosting", "hosting"):
            name = f"{name} (hosting)"
        pay = str(row.get("payment_method_label") or row.get("payment_method") or "").strip()
        if pay and pay.lower() not in name.lower():
            name = f"{name} [{pay}]"
        qty = str(row.get("quantity") or 1)
        table_rows.append(
            [
                str(idx),
                name,
                qty,
                format_price_label(row),
                format_status_label(row),
                format_date_label(row),
            ]
        )

    per_page = 28
    chunks: List[List[List[str]]] = []
    if not table_rows:
        chunks = [[[]]]
    else:
        for i in range(0, len(table_rows), per_page):
            chunks.append(table_rows[i : i + per_page])
    page_count = max(1, len(chunks))
    meta = [
        f"Generated: {generated}",
        f"User: {user_id}",
        f"Orders: {len(table_rows)}",
    ]

    page_streams = [
        _page_stream(title, meta, headers, chunk if chunk != [[]] else [], page_no, page_count)
        for page_no, chunk in enumerate(chunks, start=1)
    ]
    objects: List[bytes] = []
    # 1 Catalog, 2 Pages, 3 Helvetica, 4 Helvetica-Bold, then pairs of Page + Contents
    font_regular = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    font_bold = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
    page_ids = []
    content_bodies = []
    # object numbers: 1 catalog, 2 pages, 3 F1, 4 F2, then page/content pairs starting at 5
    next_id = 5
    for stream in page_streams:
        stream_bytes = stream.encode("latin-1", "replace")
        page_ids.append(next_id)
        content_bodies.append((next_id + 1, stream_bytes))
        next_id += 2

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    catalog = b"<< /Type /Catalog /Pages 2 0 R >>"
    pages = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    objects.extend([catalog, pages, font_regular, font_bold])

    content_by_id = {cid: body for cid, body in content_bodies}
    # Append page then content in id order
    for pid in page_ids:
        cid = pid + 1
        page_obj = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {A4_WIDTH:.2f} {A4_HEIGHT:.2f}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {cid} 0 R >>"
        ).encode("ascii")
        objects.append(page_obj)
        body = content_by_id[cid]
        objects.append(f"<< /Length {len(body)} >>\nstream\n".encode("ascii") + body + b"endstream")

    return _pack_objects(objects)
