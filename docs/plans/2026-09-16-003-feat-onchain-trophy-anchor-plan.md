---
title: On-Chain Trophy Anchor — NFT Rethink
type: feat
date: 2026-09-16
artifact_contract: ce-unified-plan/v1
companion_plan: docs/plans/2026-09-16-001-feat-trophy-shop-wallet-plan.md
---

# On-Chain Trophy Anchor — Rethinking the NFT Project

## Executive summary

The original **PayPal NFT purchase** plan was renamed to **Trophy** because MasterNoder2 has **no NFT opcode or unique-asset RPC today**. That decision stands for checkout and UX honesty.

This plan adds a **second layer** without reversing the Trophy rebrand:

| Layer | Name | Status | User-facing |
|-------|------|--------|-------------|
| **L1** | Platform Trophy | Shipped (plan 001) | Edition numbers, PayPal/MN2, auction, transfer |
| **L2** | Chain Anchor | **Starting now** (BM-U6 Phase 1) | Optional proof commitment; explorer link when tx exists |
| **L3** | Full on-chain NFT | **Deferred** | Requires daemon + wallet consensus |

**Product language remains Trophy.** Do not resurrect "NFT" in shop/checkout copy until L3 is real. Internal code may use `trophy_anchor` / `anchor_commitment`.

## Why not call them NFTs yet?

- MN2 is UTXO/PIVX-style — no ERC-721 equivalent.
- `mintzerocoin` is fungible privacy, not collectibles.
- PayPal fulfillment must not send irreversible chain value as settlement.

## L2 — Anchor model (Phase 1, starting)

Each edition already has `proof_hash` and `edition_key`. L2 adds:

1. **Queue** — on grant (PayPal, block mint, auction transfer), enqueue anchor job.
2. **Commitment** — `anchor_commitment = SHA256("trophy-anchor-v1|{edition_key}|{proof_hash}")`.
3. **Registry** — `data/trophy_anchor_registry.json` records status: `pending` → `committed` (ledger) → `anchored` (when txid known).
4. **Edition metadata** — `anchor_status`, `anchor_commitment`, optional `anchor_txid`, `anchor_explorer_url`.
5. **API** — `GET /api/shop/trophies/anchor/status`, `POST /api/shop/trophies/anchor/process` (ops).

Phase 1 does **not** require a successful OP_RETURN tx. It prepares verifiable commitments and ops tooling.

## L2 — Phase 2 (next)

- `createrawtransaction` + OP_RETURN payload (80 bytes) with truncated commitment.
- Hot-wallet `sendrawtransaction` from ops wallet; store `anchor_txid`.
- Link from wallet/profile edition row to explorer tx.

## L3 — Full on-chain NFT (deferred)

Requires MN2 daemon work: unique asset index, transfer RPC, wallet UI. Out of scope for this repo until daemon RFC lands.

## Units

| Unit | Goal | Depends |
|------|------|---------|
| **A-U1** | `trophy_anchor_service` queue + registry + edition patch | U2 |
| **A-U2** | API status + ops process endpoint | A-U1 |
| **A-U3** | Hook grants (PayPal, block, auction, peer transfer) | A-U1 |
| **A-U4** | Wallet/profile show anchor badge + explorer when txid | A-U2, U4 |
| **A-U5** | OP_RETURN broadcast (daemon RPC) | A-U2, MN2 ops |

## Verification

```bash
pytest tests/unit/test_trophy_anchor_service.py -q
```

- New PayPal edition → `anchor_status: pending` then `committed` after process.
- `GET /api/shop/trophies/anchor/status?edition_key=TRO-top25-01-1` returns commitment.
- UI still shows `on_chain_mint: false` until L3.

## Relationship to plan 001

- Plan 001 **BM-U6** = this document's L2/L3 track.
- All plan 001 Trophy units remain source of truth for commerce; anchor is additive audit trail.
