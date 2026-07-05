#!/usr/bin/env python3
"""Run forum camouflage agent — seeds threads as rotating community personas."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(description="Forum camouflage agent")
    parser.add_argument("--seed", action="store_true", help="Bootstrap if forum is empty")
    parser.add_argument("--threads", type=int, default=2, help="New threads per run")
    parser.add_argument("--replies", type=int, default=3, help="Replies per run")
    args = parser.parse_args()

    from backend.services.forum_agent_service import run_agent_cycle, seed_initial_content

    if args.seed:
        result = seed_initial_content()
    else:
        result = run_agent_cycle(max_new_threads=args.threads, max_replies=args.replies)

    print(result)
    return 0 if result.get("success", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
