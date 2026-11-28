#!/usr/bin/env python3
"""Generate static/html/mn-portal-topnav.html from nav manifest + toolbar link defs."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "static" / "data" / "nav_portal_manifest.json"
NAV_JS = ROOT / "static" / "js" / "navigation-toolbar.js"
OUT = ROOT / "static" / "html" / "mn-portal-topnav.html"

ICON_IMAGES = {
    "home": "/static/img/nav/home.svg",
    "battle": "/static/img/agents/battle_strategy_agent.svg",
    "trophies": "/static/img/nav/trophy.svg",
    "stories": "/static/img/nav/stories.svg",
    "game": "/static/img/nav/game.svg",
    "casino": "/static/img/nav/casino.svg",
    "generator": "/static/img/agents/content_generator_agent.svg",
    "podcast": "/static/img/nav/news.svg",
    "quests": "/static/img/agents/workflow_agent.svg",
    "agents": "/static/img/agents/ai_intelligence_agent.svg",
    "agent_support": "/static/img/agents/master_support_agent.svg",
    "gallery": "/static/img/agents/user_experience_agent.svg",
    "battlegrounds": "/static/img/nav/battlegrounds.svg",
    "profile": "/static/img/nav/profile.svg",
    "social": "/static/img/agents/social_engagement_agent.svg",
    "shop": "/static/img/nav/shop.svg",
    "market": "/static/img/agents/analytics_agent.svg",
    "nft": "/static/img/nft/vault-holo.svg",
    "customers": "/static/img/nav/customers.svg",
    "agents_control": "/static/img/agents/master_dashboard_agent.svg",
    "chat": "/static/img/nav/chat.svg",
    "debugger": "/static/img/agents/tester_agent.svg",
    "lab": "/static/img/nav/lab.svg",
    "starmap25": "/static/img/nav/starmap.svg",
    "explorer": "/static/img/nav/explorer.svg",
    "news": "/static/img/nav/news.svg",
    "library": "/static/img/nav/stories.svg",
    "wallets": "/static/img/nav/profile.svg",
    "staking_leaderboard": "/static/img/nav/trophy.svg",
    "staking_teams": "/static/img/agents/social_engagement_agent.svg",
}


def parse_links(nav_js: str) -> dict[str, dict]:
    links: dict[str, dict] = {}
    for match in re.finditer(
        r"\{\s*name:\s*'([^']*)'.*?id:\s*'([^']*)'",
        nav_js,
        re.S,
    ):
        block = match.group(0)
        name = match.group(1)
        link_id = match.group(2)
        url_m = re.search(r"url:\s*APP_BASE\s*\+\s*'([^']*)'", block)
        icon_m = re.search(r"icon:\s*'([^']*)'", block)
        title_m = re.search(r"title:\s*'([^']*)'", block)
        if not url_m:
            continue
        links[link_id] = {
            "name": name,
            "id": link_id,
            "url": url_m.group(1),
            "icon": icon_m.group(1) if icon_m else "✨",
            "title": title_m.group(1) if title_m else "",
            "favorite": "favorite: true" in block,
        }
    return links


def icon_html(link: dict, extra: str = "") -> str:
    src = ICON_IMAGES.get(link["id"])
    pulse = " nav-toolbar-link-img--pulse" if link.get("favorite") else ""
    avatar = " nav-toolbar-link-img--avatar" if src and "/agents/" in src else ""
    if src:
        return (
            f'<span class="nav-toolbar-link-icon{extra}">'
            f'<img class="nav-toolbar-link-img{pulse}{avatar}" src="{src}" alt="" '
            f'width="20" height="20" loading="lazy" decoding="async" '
            f"onerror=\"this.style.display='none';var fb=this.nextElementSibling;"
            f'if(fb){{fb.hidden=false;}}">'
            f'<span class="nav-toolbar-link-emoji-fallback" hidden aria-hidden="true">'
            f'{html.escape(link["icon"])}</span></span>'
        )
    return (
        f'<span class="nav-toolbar-link-icon{extra}">'
        f'{html.escape(link["icon"])}</span>'
    )


def link_anchor(link: dict) -> str:
    fav = " nav-toolbar-link-favorite" if link.get("favorite") else ""
    if link.get("title"):
        title = f' title="{html.escape(link["title"], quote=True)}"'
    elif link.get("favorite"):
        title = ' title="Favorite"'
    else:
        title = ""
    return (
        f'<a href="{html.escape(link["url"])}" '
        f'class="nav-toolbar-link nav-toolbar-portal-grid-link{fav}" '
        f'data-page-id="{html.escape(link["id"])}"{title}>'
        f"{icon_html(link)}"
        f'<span>{html.escape(link["name"])}</span></a>'
    )


def cat_gif(cat: dict, cls: str) -> str:
    src = f'/static/img/nav/categories/{cat.get("gif") or (cat["id"] + ".gif")}'
    return (
        f'<img class="{cls}" src="{src}" alt="" width="28" height="28" '
        f'loading="lazy" decoding="async">'
        f'<span class="nav-toolbar-cat-smiley" aria-hidden="true">'
        f'{html.escape(cat.get("smiley") or "✨")}</span>'
    )


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cats = manifest["templates"]["home_portal_void_v1"]["categories"]
    by_id = parse_links(NAV_JS.read_text(encoding="utf-8"))

    sections: list[str] = []
    missing: list[str] = []
    for cat in cats:
        items = []
        for link_id in cat["ids"]:
            if link_id in by_id:
                items.append(by_id[link_id])
            else:
                missing.append(link_id)
        if not items:
            continue
        title = cat.get("menuTitle") or cat["label"]
        grid = "".join(link_anchor(link) for link in items)
        sections.append(
            f'<section class="nav-toolbar-portal-section" '
            f'aria-labelledby="nav-cat-{html.escape(cat["id"])}">'
            f'<h3 class="nav-toolbar-portal-section-title" '
            f'id="nav-cat-{html.escape(cat["id"])}">'
            f'<span class="nav-toolbar-portal-section-art">'
            f'{cat_gif(cat, "nav-toolbar-cat-gif nav-toolbar-cat-gif--section")}'
            f"</span><span>{html.escape(title)}</span></h3>"
            f'<div class="nav-toolbar-portal-grid">{grid}</div></section>'
        )

    brand_icon = (
        '<span class="nav-toolbar-link-icon nav-toolbar-brand-icon-wrap">'
        '<img class="nav-toolbar-link-img nav-toolbar-link-img--pulse '
        'nav-toolbar-link-img--lg" src="/static/img/nav/brand.svg" alt="" '
        'width="20" height="20" loading="lazy" decoding="async" '
        "onerror=\"this.style.display='none';var fb=this.nextElementSibling;"
        'if(fb){fb.hidden=false;}">'
        '<span class="nav-toolbar-link-emoji-fallback" hidden aria-hidden="true">'
        "🏠</span></span>"
    )

    out_html = f"""<!-- MasterNoder static Portals topnav. Loaded by /static/js/mn-portal-topnav.js -->
<nav class="nav-toolbar nav-toolbar--portal-void nav-toolbar--categorized" id="navToolbar" data-mn-portal-static="1">
  <div class="nav-toolbar-content">
    <a href="/" class="nav-toolbar-brand">
      {brand_icon}
      <span>MasterNoder</span>
    </a>
    <div class="nav-toolbar-portal-wrap">
      <button type="button" class="nav-toolbar-portal-trigger" id="navPortalTrigger" aria-expanded="false" aria-haspopup="true" aria-controls="navPortalPanel">
        <span class="nav-toolbar-portal-trigger-icon nav-toolbar-portal-trigger-icon--spin">🌀</span>
        <span>Portals</span>
      </button>
    </div>
    <div class="nav-toolbar-user">
      <div class="nav-toolbar-user-controls" id="navToolbarUserControls">
        <button class="nav-toolbar-control-btn" id="navToolbarUserBtn" title="User Settings"><span>👤</span></button>
        <button class="nav-toolbar-control-btn" id="navToolbarSettingsBtn" title="Settings"><span>⚙️</span></button>
        <button class="nav-toolbar-control-btn" id="navToolbarNotificationsBtn" title="Notifications">
          <span>🔔</span><span class="nav-toolbar-badge" id="navToolbarNotificationsBadge" style="display: none;">0</span>
        </button>
      </div>
      <div class="nav-toolbar-currency" id="navToolbarCurrency">
        <span class="nav-toolbar-currency-icon">🪙</span><span id="navToolbarCurrencyAmount">0</span>
      </div>
      <button class="nav-toolbar-toggle" id="navToolbarToggle" aria-label="Toggle menu">☰</button>
    </div>
  </div>
  <div id="navPortalPanel" class="nav-toolbar-portal-panel" role="menu" aria-hidden="true" hidden>
    <div class="nav-toolbar-portal-inner">
      <p class="nav-toolbar-portal-hint">Browse by category — all site portals</p>
      <div class="nav-toolbar-portal-sections" id="navPortalGrid">
        {''.join(sections)}
      </div>
    </div>
  </div>
</nav>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out_html, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    print(f"sections={len(sections)} links={len(by_id)} missing={missing}")


if __name__ == "__main__":
    main()
