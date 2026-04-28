#!/usr/bin/env python3
"""
Assign Rulebook Todo 25 and Star Map 25 Todo to free agents.
Call the debugger API to assign tasks to content_generator_agent, learning_agent, analytics_agent.
Requires the Flask app to be running (e.g. locally or on server).

Usage:
  python scripts/assign_rulebook_todo_to_agents.py
  BASE_URL=https://masternoder.dk python scripts/assign_rulebook_todo_to_agents.py
"""
import os
import sys

BASE_URL = os.getenv("BASE_URL", "https://masternoder.dk")
ASSIGN_PATH = "/vidgenerator/api/debugger/tasks/assign-rulebook-todo"
TIMEOUT = int(os.getenv("TIMEOUT", "90"))


def main():
    try:
        import requests
    except ImportError:
        print("Install requests: pip install requests")
        sys.exit(1)

    url = BASE_URL.rstrip("/") + ASSIGN_PATH
    print(f"Assigning 25 daily tasks (rulebook + starmap25) to free agents via {url} (timeout={TIMEOUT}s) ...")
    try:
        r = requests.post(url, json={"max_tasks": 25, "daily": True}, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("success"):
            n = data.get("total_assigned", 0)
            agents = data.get("agents_used", [])
            print(f"Assigned {n} tasks to agents: {agents}")
            for a in data.get("assigned", [])[:15]:
                print(f"  {a.get('task_id')} -> {a.get('agent_id')}: {a.get('description', '')[:60]}")
            if n > 15:
                print(f"  ... and {n - 15} more.")
        else:
            print("Response:", data.get("error", data))
    except requests.exceptions.ConnectionError:
        print("Could not connect. Is the app running? Try: BASE_URL=https://masternoder.dk python scripts/assign_rulebook_todo_to_agents.py")
        sys.exit(1)
    except requests.exceptions.ReadTimeout:
        print(f"Read timed out after {TIMEOUT}s. Server may be slow. Try: TIMEOUT=120 python scripts/assign_rulebook_todo_to_agents.py")
        sys.exit(1)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
