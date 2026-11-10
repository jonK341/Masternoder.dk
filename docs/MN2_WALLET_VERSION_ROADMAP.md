# MN2 wallet & platform version roadmap (9.2.6.5)

Platform UI line **9.2.6.5** (shop + wallet chrome + `/api/version`). Daemon binaries stay on the MasterNoder2 release line from `scripts/mn2_release_config.py` (currently **v1.3.1.0**).

## Technology choices (lag-free wallet)

| Concern | Choice | Why |
| --- | --- | --- |
| Chrome balance | `GET /api/mn2/balance/onchain` (+ `/fast` alias) + 90s poll | **On-chain only:** ensures deposit address then sums UTXOs. No custodial ledger for chrome. |
| Dollar rate | Separate `GET /api/mn2/price` | Price never blocks the balance paint. |
| Live updates | Timed poll, not WebSocket/SSE for balance | Activity stream already holds a worker thread; a second held stream risks pool exhaustion. |
| On-chain detail | Existing `GET /api/mn2/balance` still available for shop/ledger reconciliation | Chrome no longer waits on Chainz or ledger. |
| Deposit address | Created on chrome paint + profile wallet load | `getnewaddress` when missing — more receive paths for network activity. |
| Spork intelligence | `GET /api/mn2/sporks` (all catalog sporks) | Read-only; defaults of SPORK_112 / 114 stay OFF. |
| Downloads | `GET /api/mn2/releases` + release config | One place for version + sha256; no stale hardcoded URLs. |

## Version schemes (keep separate)

1. **Platform UI** — four-part `9.x.y.z` (this line). Bump when wallet/shop chrome behavior ships.
2. **Daemon product** — `vMAJOR.MINOR.REVISION.BUILD` in `scripts/mn2_release_config.py`.
3. **P2P protocol** — daemon `protocolversion` / SPORK_14 / SPORK_15.
4. **Site cache-bust** — `/api/version` (aligned to platform UI for 9.2.6.5).

## Next 100 platform UI versions (9.2.6.5 → 9.2.106.5)

Use the patch digit as the wallet/chrome iteration counter. Suggested themes (not commitments):

| Range | Focus |
| --- | --- |
| 9.2.6.5 – 9.2.15.5 | Fast ledger chrome, downloads, full spork intelligence, deep links |
| 9.2.16.5 – 9.2.25.5 | Deposit scanner UX, trusted-address first-run, withdraw clarity |
| 9.2.26.5 – 9.2.35.5 | Session-only balance reads; drop query `user_id` on chrome |
| 9.2.36.5 – 9.2.45.5 | Shop/lab callers migrate off detail balance where safe |
| 9.2.46.5 – 9.2.55.5 | Optional shared EventSource only if worker pool grows |
| 9.2.56.5 – 9.2.65.5 | Mobile wallet shell parity |
| 9.2.66.5 – 9.2.75.5 | Hardware-wallet / watch-only education surfaces |
| 9.2.76.5 – 9.2.85.5 | Daemon upgrade assistant driven by release manifests |
| 9.2.86.5 – 9.2.95.5 | Spork operator console (read + signed update scripts) |
| 9.2.96.5 – 9.2.106.5 | Protocol bump prep (SPORK_14/15) + peer upgrade messaging |

## Next daemon versions (upgrade the wallet binaries)

Bump `TARGET_VERSION` in `scripts/mn2_release_config.py` and publish manifests. Candidate sequence after **v1.3.1.0**:

- **v1.3.2.0** — packaging / Qt checksum reliability
- **v1.3.3.0** — RPC timeout / unlock ergonomics for website deposits
- **v1.4.0.0** — optional SPORK_116+ only when product needs a new gate (do not invent ids casually)
- **v1.5.x / v2.x** — protocol bumps behind SPORK_14 / SPORK_15

## What upgrades the website wallet (without flipping live sporks)

1. Healthy `MN2_RPC_*` + optional `MN2_WALLET_PASSPHRASE` for address creation.
2. Deposit scanner / backfill so ledger reflects chain credits.
3. Fast chrome path (shipped in 9.2.6.5) so UI never waits on chain.
4. Keep `wallet_mode: ledger` for shop settlement unless shop must settle on-chain.
5. Keep `SPORK_112` and `SPORK_114` at OFF until an operator intentionally signs them.
