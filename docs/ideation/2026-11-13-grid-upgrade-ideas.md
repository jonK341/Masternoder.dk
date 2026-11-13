# Grid upgrade ideas — 2026-11-13

## What we checked

- Live daemon: `EXCHANGE_GRID_LIVE=1` + `EXCHANGE_ARBITRAGE_LIVE=1`, heartbeat `grid live=True ticks=57 open_orders=0 realized=$-6.57`
- State: 55 assets, **all venues paused** (`thin_quote`) since ~05:22 CET; last real asset updates ~60–70h earlier
- Guard on PPP (`apply_quote_and_loss_guards`): pause venue when free quote &lt; `2 × order_size_usd` (~$12), then `reset_open_orders`
- Binance realized dominated by **XRP ≈ −$6.61**; NonKYC slightly green but still paused for empty USDT
- Maker-quote service already yields **buys only** on thin quote and keeps sells — grid pause is blunter

## Survivors (ranked)

### 1. Thin-quote → sell-only (not venue pause)
When quote is thin, suppress **buys** but keep **sell-from-existing / inventory sells** working. Matches maker-quote behavior; unsticks the current all-paused grid without needing a USDC/USDT top-up first.

### 2. Honest heartbeat / skip taxonomy
Surface `paused_venues`, `thin_quote` / `aggregate_hard_loss`, free quote, and `open_orders_read_failed` in the daemon summary instead of `open_orders=0` which looks like “idle but fine.”

### 3. Per-asset quarantine, not venue-wide death
XRP’s −$6.61 should halt **BINANCE:XRP**, not every Binance pair. Venue pause only for true venue failures (401, no quote asset at all).

### 4. Auto-resume + reseed when quote recovers
Clear `thin_quote` pauses when free quote ≥ threshold; call `reset_open_orders` once so ladders reseed. Today pauses stick until cooldown/manual while ticks noop.

### 5. Funded-inventory universe
When quote is thin, tick only symbols with free base above min notional. Stop spraying 57 empty ladders.

### 6. Cost-basis take-profit step (0.5–1.5%, not 5–10%)
Keep paired replacement, but size the sell step from **avg cost + fees + min edge** (or a small TP ladder). Logs show arb edges ≪ 5%; grid should aim for fee-positive maker steps, not swing targets.

### 7. API health gate
Binance “API-key format invalid” / NonKYC 401 must show as blockers in preflight/heartbeat; never look “live” while reconcile cannot see the book.

## Rejected / deferred

- **5–10% resting TP as default** — log scan: pbook median ~0.3% net; 0 hits ≥5%. Wrong scale for this book.
- **More levels / denser BN grid while paused** — adds surface area without fixing quote starvation.
- **Delete circuit breaker** — loss protection is useful; fix scope (asset vs venue) instead.

## Next step menu

1. Brainstorm **#1 sell-only under thin_quote** into a requirements plan  
2. Brainstorm **#2+#4 heartbeat + auto-resume** (ops visibility first)  
3. Brainstorm **#3+#5 quarantine + inventory universe**  
4. Surprise mix of top three  
5. Cancel / park ideation  
