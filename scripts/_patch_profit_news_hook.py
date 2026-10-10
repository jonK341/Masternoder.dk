#!/usr/bin/env python3
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "scripts" / "all_profit_daemons.py"
text = p.read_text(encoding="utf-8")
old = """            _write_heartbeat("exchange", summary)
        except Exception as exc:
            print(f"[all-profit] exchange error: {exc}", flush=True)"""
new = """            _write_heartbeat("exchange", summary)
            try:
                from backend.services.profit_daemon_news_service import maybe_publish_tick_news
                maybe_publish_tick_news("exchange", summary, res=res)
            except Exception:
                pass
        except Exception as exc:
            print(f"[all-profit] exchange error: {exc}", flush=True)"""
if old not in text:
    raise SystemExit("patch target not found")
p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched")
