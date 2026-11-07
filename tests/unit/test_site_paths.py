from backend.services.site_paths import root_relative_href, strip_legacy_vidgenerator_prefix


def test_strip_legacy_vidgenerator_prefix():
    assert strip_legacy_vidgenerator_prefix("/vidgenerator") == "/"
    assert strip_legacy_vidgenerator_prefix("/vidgenerator/") == "/"
    assert strip_legacy_vidgenerator_prefix("/vidgenerator/generator") == "/generator"
    assert strip_legacy_vidgenerator_prefix("/generator") == "/generator"


def test_root_relative_href():
    assert root_relative_href("game") == "/game"
    assert root_relative_href("/profile/") == "/profile"
