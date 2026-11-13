# Profit trading profiles & strategy categories

Look-through catalog for the profit body.

- Categories: `backend/config/profit_strategy_categories.py`
- Profiles: `backend/config/profit_trading_profiles.py`
- Enrichment: `backend.services.exchange_strategy_enrichment_service`

## Four strategy categories

| Category | What it does | Limbs |
|----------|--------------|-------|
| **Arbitrage** | Buy cheap on one venue, sell rich on another — fast exec + split capital | hunter, dual_farm, latch, executor, datamaxi, courier, pbook, closer |
| **Momentum** | Short-term rise + volume (news/sentiment); **tight stop-loss** | momentum, swing |
| **VWAP** | Volume-weighted average as intraday support/resistance | vwap, grid, latch |
| **Grid** | Automated buy/sell ladder; harvests sideways noise | grid, closer, courier |

Pbook hitlist rows carry a `strategy` block (categories + momentum/VWAP/grid hints). Head state includes `strategies` from `limb_enrichment_snapshot()`.

## Cutting edge (arbitrage filter)

One score, three bands — `cutting_edge()` in the technique executor:

| Band | Meaning | Action |
|------|---------|--------|
| **fire** | `cut_bps` clears floor after skew−noise | Hunter / executor taker path |
| **latch** | Fat net, thin cut | Latch maker wait |
| **skip** | Phantom / dust | Drop |

`cut_bps = net − max(0, |mid_skew| − local_noise)` where local_noise is average half micro-spread. Hunter keeps only top `CUTTING_EDGE_TOP_N` (default 3) fire/latch deals.

## Installed profiles by category

| Category | Profile | Limb | Notes |
|----------|---------|------|-------|
| arbitrage | spatial_taker_cut, skew_maker_latch, quote_bridge_courier, datamaxi_cex_spread, hummingbot_spot_perp_basis | hunter / latch / courier / datamaxi / basis | Live spatial + paper basis |
| momentum | **momentum_volume_burst**, precision_level_swing | `momentum`, `swing` | Paper bursts; `MOMENTUM_LIVE=1` to arm; stop default 1.5% |
| vwap | **vwap_intraday_levels** | `vwap` | Session VWAP ±σ; enriches grid/latch |
| grid | grid_range_harvest | `grid` | Live when `EXCHANGE_GRID_LIVE=1` |

## Env knobs (new limbs)

- `MOMENTUM_ARM_ENABLED`, `MOMENTUM_LIVE`, `MOMENTUM_STOP_PCT`, `MOMENTUM_MIN_RETURN_BPS`, `MOMENTUM_MIN_VOLUME_RATIO`, `MOMENTUM_INTERVAL_SEC`
- `VWAP_ARM_ENABLED`, `VWAP_ENTRY_BPS`, `VWAP_LOOKBACK_MINUTES`, `VWAP_INTERVAL_SEC`

## Still worth looking through

| Profile | Fit | Why |
|---------|-----|-----|
| **Hummingbot cross-exchange MM** | medium | Cousin of latch + courier |
| **Factor-residual stat arb** | medium | Literature behind residual filters |
| **Stoic Meta regime** | inspiration | Head limb enable / kill-shot switching |
| **Cryptohopper marketplace** | browse | Strategy templates / paper lab |

## Links

- Hummingbot: https://github.com/hummingbot/hummingbot
- Stratcraft open algos: https://stratcraft.ai/algorithms
- DataMaxi strategies: https://docs.datamaxiplus.com/strategies/overview
