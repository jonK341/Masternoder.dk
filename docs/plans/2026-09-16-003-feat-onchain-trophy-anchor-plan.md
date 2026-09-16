---
title: On-Chain Trophy Anchor — NFT Rethink (updated)
type: feat
date: 2026-09-16
status: L2 shipped · L3 deferred
artifact_contract: ce-unified-plan/v1
companion_plan: docs/plans/2026-09-16-001-feat-trophy-shop-wallet-plan.md
---

# On-Chain Trophy Anchor — Plan 003 (complete L2 track)

## Executive summary

| Layer | Name | Status | User-facing |
|-------|------|--------|-------------|
| **L1** | Platform Trophy | **Shipped** | Editions, PayPal/MN2, auction, transfer, proof page |
| **L2** | Chain Anchor | **Shipped** | Commitment queue, transfer re-anchor, optional OP_RETURN |
| **L3** | Full on-chain NFT | **Deferred** | Requires MN2 daemon unique-asset RPC |

**Product language remains Trophy** in shop/checkout. Proof pages and metadata JSON use neutral “collectible” wording.

## L2 — Shipped capabilities

### Anchor pipeline (`trophy_anchor_service.py`)

- `queue_edition_anchor` on mint (PayPal, block mint, staking, platform grant)
- `queue_transfer_reanchor` on **peer transfer** and **auction sale** (plan A-U3 ✅)
- Priority queue: staking_winner (100) > transfer (75) > block_mint (50) > default
- Registry: `pending` → `committed` → `anchored` (when txid exists)
- OP_RETURN broadcast via `broadcast_anchor_queue` (A-U5 ✅, `broadcast_on_chain` env/config)

### Proof & metadata (marketplace polish)

| API | Purpose |
|-----|---------|
| `GET /api/shop/trophies/metadata/{edition_key}` | Open-style JSON metadata |
| `GET /api/shop/trophies/proof/{edition_key}` | Public proof payload |
| `GET /api/shop/trophies/provenance/{edition_key}` | Ownership event chain |
| `/trophy/proof?edition_key=…` | Human-readable proof page |

### Provenance (`trophy_provenance_service.py`)

Global `data/trophy_provenance.jsonl` events: `minted`, `peer_transfer`, `auction_sale`, `revoked`, `burned`.

### Commerce polish

- **Resale royalty** — `royalty_bps` from `trading_profile` deducted on auction `buy_listing`
- **PayPal clawback** — `POST /api/shop/trophies/paypal-clawback` revokes edition on dispute
- **Burn** — `POST /api/shop/trophies/burn` for MN2 credit
- **Discord** — share + auction sale fanout (`trophy_discord_fanout.py`)
- **Genesis backfill** — lazy media + `scripts/backfill_block_trophy_media.py` + status API

### Wallet (A-U4 ✅)

- Anchor badges on trophy cards (pending / committed / anchored + explorer link)
- Proof + Share buttons on Trophies tab
- Set badges: Genesis Set, Million Club, Interval Champion

## Units — status

| Unit | Goal | Status |
|------|------|--------|
| **A-U1** | Queue + registry + edition patch | ✅ |
| **A-U2** | API status + ops process/broadcast | ✅ |
| **A-U3** | Hook grants **and transfers** | ✅ |
| **A-U4** | Wallet/profile anchor badge + proof | ✅ |
| **A-U5** | OP_RETURN broadcast | ✅ (ops-enabled) |

## Wallet upgrades (253–257)

| ID | Name |
|----|------|
| WR-UPG-253 | Trophy proof page |
| WR-UPG-254 | Resale royalty rail |
| WR-UPG-255 | Provenance timeline |
| WR-UPG-256 | Genesis set badge |
| WR-UPG-257 | Anchor badge glow |
| WR-UPG-258 | Featured profile trophy equip |
| WR-UPG-259 | Permanent IPFS metadata pin |

### Permanent storage (L2.5)

- `trophy_ipfs_service.py` — SHA-256 content-addressed JSON at `/static/trophy-ipfs/cid/{digest}.json`
- `ipfs://{digest}` URI on metadata + proof page; optional remote pin via `IPFS_PIN_API_URL`
- Auto-pin on grant enrichment and proof/metadata view

### Profile equip

- `POST /api/shop/trophies/equip-profile` — feature owned edition on `/profile` header
- Wallet Trophies tab **Feature** button (WR-UPG-258)

### Genesis auto-backfill (WR-UPG-260)

- Prewarm within 5,000 blocks of milestone (`genesis_prewarm_within_blocks`)
- `run_genesis_backfill_batches()` + `POST /api/shop/block-mint/backfill/genesis`
- Cron: `scripts/backfill_block_genesis.py`

### PayPal dispute clawback webhook (WR-UPG-261)

- `POST /api/paypal/trophy-webhook` — dispute/refund events revoke editions
- `trophy_paypal_webhook_service.py` with idempotent event log
- Cancels auction listings + releases block manifest claims on clawback

## L3 — Deferred

Requires MN2 daemon: unique asset index, transfer RPC, wallet consensus. No user-facing “NFT” label until L3.

## Verification

```bash
pytest tests/unit/test_trophy_anchor_service.py \
       tests/unit/test_trophy_provenance_service.py \
       tests/unit/test_trophy_metadata_service.py -q
```

- Peer transfer → provenance event + transfer re-anchor job
- Auction sale → royalty coins + Discord sale embed
- `GET /api/shop/trophies/proof/TRO-block-1000-1` returns GIF + license + chain
- UI: `on_chain_mint: false` until L3
