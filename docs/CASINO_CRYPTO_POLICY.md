# Casino Crypto Policy (MN2)

**Status:** Live policy for Phase 7 casino crypto rails (2026-07-25).

## Rails

| Rail | Ledger key | Notes |
|------|------------|-------|
| Virtual coins | `coins` | Cosmetic / social play — not redeemable for cash |
| MN2 | `mn2_balance` | On-platform MN2; Gate S auth + idempotent references |
| Fiat play | `casino_fiat_balance` | Funded via PayPal / MN2 buy-in packs |

## Allowed MN2 uses

- Wagering on casino games when real-money MN2 mode is enabled
- Progressive jackpots and tournaments denominated in MN2
- Playthrough **cashback** (`/api/casino/mn2/cashback`) — accrues on MN2 wagers, claim once per UTC day
- Internal **MN2 ↔ coins swap** via `/api/mn2/swap/quote|execute` (same AMM as wallet / Phase 2)

## Not allowed

- Discord / chat identity alone authorizing withdrawals or cashback claims
- Auto-withdrawal of casino MN2 winnings off-platform without Gate S withdrawal path
- Cashback farming via anonymous / `default_user` accounts
- Arming agent-treasury live distribute from casino flows

## Responsible gaming

- Existing deposit/loss limits and geo rules apply to MN2 and USD rails
- Security password verification required before MN2 / USD stakes when configured
- Big-win social posts are opt-in and RG-safe

## Ops

- Cashback state: `data/casino_mn2_cashback.json`
- Jackpot reconcile: `GET /api/casino/jackpots/reconcile`
- Policy owners: see `docs/MN2_TODO.md` (U3) and `docs/MN2_ECOSYSTEM_REPORT.md`
