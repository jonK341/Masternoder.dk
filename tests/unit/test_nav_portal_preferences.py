"""Portal nav preferences API validation."""
import json
from pathlib import Path

from backend.services.nav_portal_preferences_service import (
    validate_template,
    validate_theme,
)

ROOT = Path(__file__).resolve().parents[2]


def test_validate_template_and_theme_ids():
    manifest = json.loads(
        (ROOT / "static" / "data" / "nav_portal_manifest.json").read_text(encoding="utf-8")
    )
    tpl = next(iter(manifest["templates"]))
    th = next(iter(manifest["themes"]))
    assert validate_template(tpl)
    assert validate_theme(th)
    assert not validate_template("not_a_real_template")
    assert not validate_theme("not_a_real_theme")
