"""Test agent API endpoints on production."""
import requests

BASE = "https://masternoder.dk"
USER_ID = "user_b4984c3befca47a7"

endpoints = [
    f"/vidgenerator/api/agents/my-agents?user_id={USER_ID}",
    f"/vidgenerator/api/agents/activity-feed?user_id={USER_ID}&limit=10",
    f"/vidgenerator/api/agents/sync",
    f"/vidgenerator/api/agent-points/all-value",
    f"/vidgenerator/agents/",
]

for ep in endpoints:
    try:
        if 'sync' in ep:
            r = requests.post(BASE + ep, json={'user_id': USER_ID}, timeout=10)
        else:
            r = requests.get(BASE + ep, timeout=10)
        print(f"  [{r.status_code}] {ep}")
        if r.status_code == 200 and 'api' in ep:
            d = r.json()
            print(f"    success={d.get('success')} keys={list(d.keys())[:5]}")
    except Exception as e:
        print(f"  [ERR] {ep}: {e}")
