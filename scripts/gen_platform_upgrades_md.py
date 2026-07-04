#!/usr/bin/env python3
"""Generate docs/PLATFORM_100_UPGRADES.md from data/platform_upgrades.json."""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(BASE, "data", "platform_upgrades.json"), encoding="utf-8") as f:
    data = json.load(f)

lines = [
    "# Platform 100 Upgrades",
    "",
    f"_Roadmap version: {data.get('version', '')}_",
    "",
    "Cross-area UX roadmap for Masternoder.dk — 10 areas × 10 upgrades each.",
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
lines.append(f"- **{done} done** / **{planned} planned** / **{total} total**")
lines.append("")

for area in data["areas"]:
    lines.append(f"## {area['name']} (`{area['path']}`)")
    lines.append("")
    lines.append("| # | Priority | Upgrade | Status |")
    lines.append("|---|----------|---------|--------|")
    for u in area["upgrades"]:
        st = "✅ done" if u["status"] == "done" else "📋 planned"
        lines.append(f"| {u['id']} | {u['priority']} | {u['title']} | {st} |")
    lines.append("")

out_path = os.path.join(BASE, "docs", "PLATFORM_100_UPGRADES.md")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(out_path)
