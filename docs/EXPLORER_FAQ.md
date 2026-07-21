# MN2 Explorer — FAQ

## Why does MN2 price show "—" (em dash)? (#219)

The hub hides invalid or zero USD prices. Chainz and the median oracle return `null` when:

- The ticker API is down or rate-limited
- The reported price is **$0** or negative (filtered in `chainz_ticker_usd`)
- No median/config price is configured

The tile label stays visible; only the value shows `—`. Check `source.mn2_usd_price` under the tile (`src: chainz`, `median`, etc.) when data returns.

---

## Why is the rich list empty? (#220)

Common causes:

1. **eiquidus index still syncing** — rich-list ext returns `[]` until address index is built. `GET /api/mn2/explorer/status` includes `checks.rich_list.index_synced`.
2. **RPC unreachable** — overview may still show height from Chainz while rich list depends on eiquidus.
3. **Fresh deploy** — wait for sync + first successful `/ext/richlist` probe.

The hub shows an explicit empty message when the API succeeds but returns no rows. See [EXPLORER_RUNBOOKS.md](EXPLORER_RUNBOOKS.md#eiquidus-index-stuck-217).

---

## Security & privacy

- Explorer APIs are **read-only** — no signing or spends (#226).
- Pool staked figures are **custodial platform totals**, not on-chain wallet balances (#227).
- Not financial advice (#228) — disclaimer on hub and wallet panels.
