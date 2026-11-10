# The Profit Daemon Jon — finished-product roadmap

Snapshot of how many improvements remain for a polished GitHub download.

Run live counts anytime:

```bash
.venv/bin/python profit_daemon_jon/run.py --backlog
```

## Strategy next (highest leverage)

1. **NonKYC quote top-up** — convert dust/base → USDT so buy-back exits fill (venue is quote-starved).
2. **Dynamic level cap** — shrink `levels` / `max_open_orders` from free quote so entries stop crowding exits.
3. **PPP edge filter** — only ladder symbols with positive recent hit-rate / net bps.
4. **Fee table refresh** — pull maker/taker bps per venue each day; refuse pairs where `exit_bps < 2*fee`.
5. **Fill-model online retrain** — scheduled retrain from `ladder_fills.jsonl` with calibration plot in Grafana.

## Packaging next

6. Signed Windows + macOS Release assets on every tag.
7. Docker Compose profile (`daemon + redis + prometheus + grafana`).
8. First-run wizard (keys, paper/live unlock, balance check).
9. Tray / simple GUI status for desktop users.
10. CI smoke: `run.py --once --profile paper` on PRs.

## Already shipped in this product folder

- Branded runner + install scripts
- Top-25 technology catalog + installer
- PyInstaller build scripts
- GitHub Actions release workflow
- Slim `.env.example`
- Exit-funding + fill-model calibration (ladder)
- Sales report CLI + Grafana metrics stack
