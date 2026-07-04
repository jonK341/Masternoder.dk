#!/usr/bin/env python3
"""Generate docs/PLATFORM_UPGRADES_BATCH2.md from data/platform_upgrades_batch2.json."""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE, "data", "platform_upgrades_batch2.json"), encoding="utf-8") as f:
    data = json.load(f)

lines = [
    "# Platform Upgrades — Batch 2 (Items 101–300)",
    "",
    f"_Roadmap version: {data.get('version', '')}_",
    "",
    "Second wave: 10 areas × 20 upgrades each. Builds on [PLATFORM_100_UPGRADES.md](PLATFORM_100_UPGRADES.md).",
    "",
    "## Summary",
    "",
]
total = done = planned = 0
for area in data["areas"]:
    for u in area["upgrades"]:
        total += 1
        if u["status"] == "done":
            done += 1
        else:
            planned += 1
lines.append(f"- **{done} done** / **{planned} planned** / **{total} total** (batch 2)")
lines.append(f"- **Batch 1 reference:** see [PLATFORM_100_UPGRADES.md](PLATFORM_100_UPGRADES.md)")
lines.append("")

for area in data["areas"]:
    lines.append(f"## {area['name']} (`{area['path']}`)")
    if area.get("batch1_ref"):
        lines.append(f"_Extends batch 1 items {area['batch1_ref']}_")
    lines.append("")
    lines.append("| # | Priority | Upgrade | Status | Batch 1 ref |")
    lines.append("|---|----------|---------|--------|-------------|")
    for u in area["upgrades"]:
        st = "✅ done" if u["status"] == "done" else "📋 planned"
        ref = u.get("ref_batch1", "—")
        lines.append(f"| {u['id']} | {u['priority']} | {u['title']} | {st} | {ref} |")
    lines.append("")

out_path = os.path.join(BASE, "docs", "PLATFORM_UPGRADES_BATCH2.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(out_path)
