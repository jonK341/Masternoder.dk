#!/usr/bin/env python3
"""
Diagnose why generator works locally but not on production.
Run on server: ssh root@masternoder.dk "cd /var/www/html && python3 scripts/diagnose_production_generator.py"
Or locally against production: python scripts/diagnose_production_generator.py --remote
"""
import os
import sys
import json

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

def check(name, ok, msg=""):
    sym = "OK" if ok else "FAIL"
    print(f"  [{sym}] {name}" + (f": {msg}" if msg else ""))

def main():
    print("=" * 60)
    print("PRODUCTION GENERATOR DIAGNOSTIC")
    print("=" * 60)

    # 1. Paths
    print("\n[1] Paths")
    try:
        from backend.services.video_generator_service import VIDEOS_DIR
        videos_dir = VIDEOS_DIR
    except Exception:
        videos_dir = os.path.join(_root, 'vidgenerator', 'videos')
    check("Project root", os.path.isdir(_root), _root)
    check("VIDEOS_DIR", os.path.isdir(videos_dir), videos_dir)
    check("VIDEOS_DIR writable", os.access(videos_dir, os.W_OK) if os.path.isdir(videos_dir) else False)

    # 2. MoviePy
    print("\n[2] MoviePy (video pipeline)")
    try:
        from moviepy import ColorClip
        check("MoviePy import", True)
    except ImportError:
        try:
            from moviepy.editor import ColorClip
            check("MoviePy (editor) import", True)
        except ImportError:
            check("MoviePy import", False, "pip install moviepy imageio-ffmpeg")

    # 3. Generator DB
    print("\n[3] Generator DB (multi-worker job persistence)")
    try:
        from backend.services.generator_db_service import generator_tables_exist
        db_ok = generator_tables_exist()
        check("video_generation_jobs table", db_ok)
    except Exception as e:
        check("Generator DB", False, str(e))

    # 4. API (if --remote)
    if '--remote' in sys.argv:
        print("\n[4] Production API (https://masternoder.dk)")
        try:
            import urllib.request
            for path in ['/vidgenerator/api/generator/test', '/vidgenerator/api/version']:
                url = f'https://masternoder.dk{path}'
                try:
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req, timeout=10) as r:
                        data = json.loads(r.read().decode())
                        if 'generator' in path:
                            check(path, True, f"db={data.get('database_available')} pipeline={data.get('video_pipeline_available')}")
                        else:
                            check(path, data.get('success', False))
                except Exception as e:
                    check(path, False, str(e))
        except ImportError:
            print("  [--] urllib for remote check (use requests if available)")

    print("\n" + "=" * 60)
    print("If VIDEOS_DIR writable=FAIL: chmod 755 /var/www/html/vidgenerator/videos")
    print("If MoviePy=FAIL: pip install moviepy imageio-ffmpeg (in venv)")
    print("If DB=FAIL: run generator migration; jobs need DB for multi-worker")
    print("=" * 60)

if __name__ == '__main__':
    main()
