# Profit trading profiles & addons

Look-through catalog for the profit body. Code: `backend/config/profit_trading_profiles.py`.

## Cutting edge (internal, live)

One score, three bands — `cutting_edge()` in the technique executor:

| Band | Meaning | Action |
|------|---------|--------|
| **fire** | `cut_bps` clears floor after skew−noise | Hunter / executor taker path |
| **latch** | Fat net, thin cut | Latch maker wait |
| **skip** | Phantom / dust | Drop |

`cut_bps = net − max(0, \|mid_skew\| − local_noise)` where local_noise is average half micro-spread. Hunter keeps only top `CUTTING_EDGE_TOP_N` (default 3) fire/latch deals.

## Best-fit addons to look through

| Profile | Fit | Why |
|---------|-----|-----|
| **Hummingbot spot–perp / funding** | high | Delta-neutral basis — next limb after spatial |
| **DataMaxi CEX–CEX spread** | high | Same job as BN↔NK hunter; fee/slip playbooks |
| **Hummingbot cross-exchange MM** | medium | Cousin of latch + courier |
| **Factor-residual stat arb** | medium | Literature behind residual filters (strip BTC PC1) |
| **Stoic Meta regime** | inspiration | Head limb enable / kill-shot switching |
| **Cryptohopper marketplace** | browse | Strategy templates / paper lab |
| **Bitsgap GRID** | already grid | We have grid leg; DCA/COMBO is directional (low fit) |
| **Triangular** | already_present | Already in `EXCHANGE_PROFIT_PROFILE=max` |

## Links

- Hummingbot: https://github.com/hummingbot/hummingbot
- Stratcraft open algos: https://stratcraft.ai/algorithms
- DataMaxi strategies: https://docs.datamaxiplus.com/strategies/overview
- Cryptohopper: https://www.cryptohopper.com/
- Bitsgap: https://bitsgap.com/
- Stoic: https://stoic.ai/
