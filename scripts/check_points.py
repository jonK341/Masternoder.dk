"""Check points awarded after video generation."""
import requests, json

BASE = "https://masternoder.dk/vidgenerator/api"

r = requests.get(f"{BASE}/points/all?user_id=default_user", timeout=10)
data = r.json()
pts = data.get("points", {})

print("=== POINTS FOR default_user ===\n")

important = [
    "xp_total", "level", "generation_points", "xp_points",
    "activity_points", "knowledge_points", "coins", "credits",
    "trophy_points", "trophies_collected", "achievements_earned",
    "battle_points", "quest_points", "social_points",
    "communication_psychology_points",
]
for k in important:
    val = pts.get(k, pts.get("systems", {}).get(k, 0))
    if val:
        print(f"  {k:40s} = {val}")

systems = pts.get("systems", {})
if systems:
    print(f"\n=== ALL SYSTEMS ({len(systems)} types) ===\n")
    for k, v in sorted(systems.items()):
        if v:
            print(f"  {k:40s} = {v}")
