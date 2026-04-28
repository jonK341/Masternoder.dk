"""
Move all content from vidgenerator/ to project root so we can delete the folder (keep only vidgenerator/src).
Run from project root. Backs up nothing; ensure repo is committed or backed up first.
Copies only static, index.html, service-worker.js, and page dirs (not run.py, docs, scripts).
"""
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VG = PROJECT_ROOT / "vidgenerator"
KEEP_IN_VIDGENERATOR = {"src", ".git", "__pycache__"}  # keep src for Python imports

# Page dirs used by all_page_routes + agents, admin, compendium, dashboard
PAGE_DIRS = {
    "academic-perspective", "admin", "advanced_calculator", "agent_support", "agents", "aggregator",
    "analytics", "battle", "battlegrounds", "beta_testing", "champions-league", "chat", "compendium",
    "danish-divine-tech-tree", "dashboard", "debugger", "editor", "gallery", "game", "generator",
    "lab", "leaderboards", "metal", "milkyway", "monetization", "news", "points", "profile",
    "quests", "rights-law", "shop", "social", "starmap25", "stats", "theme_premium", "theme-points",
    "time-achievement-guides", "trophies", "unified_dashboard", "victory-tech-tree", "videos",
}


def main():
    if not VG.is_dir():
        print("vidgenerator/ not found")
        return
    # 1) Merge static: copy vidgenerator/static/* into root static/
    root_static = PROJECT_ROOT / "static"
    vg_static = VG / "static"
    if vg_static.is_dir():
        root_static.mkdir(parents=True, exist_ok=True)
        for item in vg_static.iterdir():
            dest = root_static / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        print("[OK] Merged vidgenerator/static -> static/")
    # 2) Single files at root
    for name in ["index.html", "service-worker.js"]:
        src = VG / name
        if src.is_file():
            shutil.copy2(src, PROJECT_ROOT / name)
            print(f"[OK] {name} -> root")
    # 3) Page dirs only (do not overwrite root run.py, docs, scripts)
    for name in PAGE_DIRS:
        item = VG / name
        if not item.exists():
            continue
        dest = PROJECT_ROOT / name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
            print(f"[OK] vidgenerator/{name} -> {name}/")
    # 4) Remove from vidgenerator everything except src
    for item in VG.iterdir():
        if item.name in KEEP_IN_VIDGENERATOR:
            continue
        if item.is_dir():
            shutil.rmtree(item)
            print(f"[DEL] vidgenerator/{item.name}/")
        else:
            item.unlink()
            print(f"[DEL] vidgenerator/{item.name}")
    print("Done. vidgenerator/ now only contains: src/")


if __name__ == "__main__":
    main()
