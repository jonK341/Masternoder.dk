"""Portal nav template manifest — structure for site-wide toolbar themes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "static" / "data" / "nav_portal_manifest.json"


def test_nav_portal_manifest_loads():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["defaultTemplate"] in data["templates"]
    assert data["defaultTheme"] in data["themes"]


def test_nav_portal_categories_reference_valid_link_ids():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    nav_js = (ROOT / "static" / "js" / "navigation-toolbar.js").read_text(encoding="utf-8")
    ids = set()
    for line in nav_js.splitlines():
        if "id: '" in line and "url:" in line:
            part = line.split("id: '", 1)[-1].split("'", 1)[0]
            ids.add(part)
    for tpl in data["templates"].values():
        for cat in tpl.get("categories", []):
            for link_id in cat.get("ids", []):
                assert link_id in ids, f"unknown link id {link_id} in template"
