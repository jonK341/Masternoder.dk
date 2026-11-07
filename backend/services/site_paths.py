"""Canonical public paths for the root site (no /vidgenerator prefix)."""  # pragma: allowlist secret


def strip_legacy_vidgenerator_prefix(path: str) -> str:
    """Map /vidgenerator/... to /... for redirects and link generation."""
    raw = (path or "").strip()
    if not raw.startswith("/"):
        raw = "/" + raw
    if raw == "/vidgenerator" or raw == "/vidgenerator/":
        return "/"
    prefix = "/vidgenerator/"
    if raw.startswith(prefix):
        rest = raw[len(prefix) :].lstrip("/")
        return "/" + rest if rest else "/"
    return raw


def root_relative_href(subpath: str) -> str:
    """Build a site path from a page slug (no legacy prefix)."""
    slug = (subpath or "").strip().strip("/")
    return "/" + slug if slug else "/"
