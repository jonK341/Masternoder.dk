#!/usr/bin/env python3
"""
Call the gallery clean API: run retention cleanup (remove expired, keep top 10).
Optionally pass --full to clear all video storage.

Usage:
  python scripts/clean_gallery.py
  python scripts/clean_gallery.py --full
  BASE_URL=https://masternoder.dk python scripts/clean_gallery.py
"""
import os
import sys
import argparse

BASE_URL = os.getenv("BASE_URL", "https://masternoder.dk")
CLEAN_PATH = "/vidgenerator/api/gallery/clean"
TIMEOUT = int(os.getenv("TIMEOUT", "90"))


def main():
    parser = argparse.ArgumentParser(description="Clean gallery directory via API")
    parser.add_argument("--full", action="store_true", help="Clear all video storage (use with care)")
    args = parser.parse_args()
    try:
        import requests
    except ImportError:
        print("Install requests: pip install requests")
        sys.exit(1)
    url = BASE_URL.rstrip("/") + CLEAN_PATH
    body = {"full": args.full}
    print(f"Cleaning gallery via {url} (full={args.full}, timeout={TIMEOUT}s) ...")
    try:
        r = requests.post(url, json=body, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "success" or data.get("cleaned"):
            n = data.get("deleted_count", 0)
            print(f"Done. Deleted: {n}")
            if data.get("deleted_ids"):
                for vid in data["deleted_ids"][:10]:
                    print(f"  - {vid}")
            if data.get("full_clean") and data.get("deleted"):
                for p in data["deleted"][:5]:
                    print(f"  - {p}")
        else:
            print("Response:", data.get("error", data))
    except requests.exceptions.ConnectionError:
        print("Could not connect. Is the app running?")
        sys.exit(1)
    except requests.exceptions.ReadTimeout:
        print(f"Read timed out after {TIMEOUT}s. Try: TIMEOUT=120 python scripts/clean_gallery.py")
        sys.exit(1)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
