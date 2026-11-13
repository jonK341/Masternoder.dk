"""camgirls_post_deploy_verify milestone helpers."""
import json

from scripts.camgirls_post_deploy_verify import (
    _milestone_minimum,
    _spotcheck_wave2_media,
    _status_roster_ok,
)


def test_milestone_minimum_mapping():
    assert _milestone_minimum(50) == 50
    assert _milestone_minimum(None) is None


def test_status_roster_ok_counts_current():
    body = json.dumps({"success": True, "performers_count": 40, "roster_scale": {"current": 40, "target": 250}})
    assert _status_roster_ok(body, 40) is True
    assert _status_roster_ok(body, 50) is False


def test_spotcheck_wave2_media_requires_avatar():
    body = json.dumps(
        {
            "success": True,
            "performers": [
                {"id": "performer_wave2_studio_host_a", "avatar_url": "/static/camgirls/media/studio-host-a/icon.svg"}
            ],
        }
    )
    assert _spotcheck_wave2_media(body) is True
