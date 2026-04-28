#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upload shop static media + manifest + shop page without restarting uwsgi.

  python scripts/deploy_shop_upload_only.py

Collects:
  - data/shop_item_media.json
  - shop/index.html
  - backend/services/shop_media_service.py
  - all files under static/shop/ (recursive: items, clips, sounds, …)

Then runs deploy.py --upload-only with that file list.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _collect() -> list[str]:
    files: list[str] = []
    base = _ROOT
    shop_static = os.path.join(base, "static", "shop")
    if os.path.isdir(shop_static):
        for dirpath, _, filenames in os.walk(shop_static):
            for fn in filenames:
                if fn.startswith(".") or fn == ".gitkeep":
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, base).replace(os.sep, "/")
                files.append(rel)
    for rel in (
        "data/shop_item_media.json",
        "shop/index.html",
        "backend/services/shop_media_service.py",
        "backend/routes/shop_routes.py",
    ):
        p = os.path.join(base, rel.replace("/", os.sep))
        if os.path.isfile(p):
            files.append(rel)
    return sorted(set(files))


def main() -> int:
    os.chdir(_ROOT)
    files = _collect()
    if not files:
        print("No files to upload.")
        return 1
    deploy = os.path.join(_ROOT, "scripts", "deploy.py")
    argv = [sys.executable, deploy, "--files", *files, "--upload-only"]
    print("Uploading", len(files), "paths (no uwsgi restart)…")
    import subprocess

    r = subprocess.run(argv, cwd=_ROOT)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
