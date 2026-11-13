# Profit daemon body — head Top 10

**Anatomy (locked)**

| Limb | Name | Role |
|------|------|------|
| Arm 1 | `hunter` | Reach — wide BN↔NK spread hunt + execute when funded |
| Arm 2 | `dual_farm` | Reach — dual-venue farm + prefund |
| Leg 1 | `pbook` | Stance map — top5 hitlist, ledger, techniques (read/plan) |
| Leg 2 | `grid` | Stance maker — resting ladders; thin-quote = fully quiet until resume+reseed |
| Head | `head` | Steer — enables/disables/budget limbs; learns; speaks one heartbeat |

**Head rule:** arms reach for edges; legs hold stance; head decides *who may spend quote, who must stay quiet, and what we learn*.

---

## Top 10 head actions

1. **Gate limbs on quote** — If free USDC/USDT is thin, force **grid fully quiet** and optionally throttle arm buys; keep `pbook` mapping. Clear thin-quote and allow **grid auto-resume + reseed** only when quote recovers.
2. **Allocate quote budget** — Split free quote across hunter / dual_farm / grid (e.g. arm reserve vs leg reserve) so one limb cannot starve the others.
3. **Arm enable / disable** — Turn hunter or dual_farm on/off for this cycle based on regime (skew too wide → pause hunter; no dual edge → pause dual_farm).
4. **Leg enable / disable** — Keep pbook always-on as the map; enable grid only when quote + API health pass; never leave grid “live” while all venues are paused without saying so.
5. **Quarantine losers** — Halt a single `(venue, asset)` (e.g. BINANCE:XRP) without killing the whole venue; shrink the tick universe to fundable inventory/quote.
6. **Pick the next strike** — From pbook top5 + hunter/dual qualifiers, choose at most one funded action this cycle (or none) — no parallel conflicting spends on the same quote.
7. **Prefund / rotate when blocked** — When best edge is unfunded, order a technique (prefund buy quote, sell-to-free, quote-bridge) instead of `exec=no` forever.
8. **Honest body heartbeat** — One rollup: arm1/arm2/leg1/leg2 status, head decision, free quote, pauses, quarantines — not `open_orders=0` alone.
9. **File + learn** — Append guard/decision events to ledgers; call exchange agent learning on quarantine, resume, fills, and skip reasons so the body improves.
10. **Circuit / kill switch** — Manual pause any limb or whole body; respect hard caps; never auto-clear operator pauses; surface API 401 / bad keys as head blockers.

---

## What else to daemonise after head

With 2 arms + 2 legs + head, the remaining “organs” (optional later) are: **eyes** (market feed freshness), **mouth** (alerts/YouTube/news already partial), **spine** (shared state/heartbeat file — exists). Head + four limbs is the full control concept.
