#!/usr/bin/env python3
"""E2E tab click smoke test on live masternoder.dk (Playwright + system browser)."""
import sys

from playwright.sync_api import sync_playwright

CASES = [
    (
        "Profile",
        "https://masternoder.dk/profile",
        "#profile-hub-nav",
        '.profile-hub-tab[data-hub-scroll="wallet"]',
        "#profile-mn2-wallet-card:not([hidden])",
        "wallet",
    ),
    (
        "Casino",
        "https://masternoder.dk/casino/",
        "#casino-games-nav",
        '.casino-game-tab[data-game="plinko"]',
        '.casino-card.casino-game-active[data-casino-game="plinko"]',
        "game=plinko",
    ),
    (
        "Lab",
        "https://masternoder.dk/lab",
        "#lab-hub-nav",
        '.lab-hub-tab[data-lab-tab="chapter"]',
        "#lab-chapter-2:not([hidden])",
        "tab=chapter",
    ),
    (
        "Monetization",
        "https://masternoder.dk/monetization",
        "#mon-hub-nav",
        '.mon-hub-tab[data-mon-tab="streams"]',
        '.mon-tab-panel[data-mon-tab="streams"]:not([hidden])',
        "tab=streams",
    ),
    (
        "Aggregator",
        "https://masternoder.dk/aggregator",
        "#agg-hub-nav",
        '.agg-hub-tab[data-agg-tab="ideas"]',
        '.agg-tab-panel[data-agg-tab="ideas"]:not([hidden])',
        "tab=ideas",
    ),
    (
        "Milky Way",
        "https://masternoder.dk/milkyway",
        "#milky-hub-nav",
        '.milky-hub-tab[data-milky-tab="tech"]',
        '.milky-tab-panel[data-milky-tab="tech"]:not([hidden])',
        "tab=tech",
    ),
    (
        "MN2 Crypto Hub",
        "https://masternoder.dk/explorer",
        "#mn2-hub-nav",
        '.mn2-hub-tab[data-mn2-tab="staking"]',
        '.mn2-tab-panel[data-mn2-tab="staking"]:not([hidden])',
        "tab=staking",
    ),
    (
        "Star Map 25",
        "https://masternoder.dk/starmap25",
        "#starmap-hub-nav",
        '.starmap-hub-tab[data-starmap-tab="economy"]',
        '.starmap-tab-panel[data-starmap-tab="economy"]:not([hidden])',
        "tab=economy",
    ),
]


def launch_browser(playwright):
    for channel in ("msedge", "chrome", None):
        try:
            if channel:
                return playwright.chromium.launch(channel=channel, headless=True), channel
            return playwright.chromium.launch(headless=True), "bundled-chromium"
        except Exception as exc:
            print(f"Launch failed ({channel}): {exc}")
    return None, None


def click_tab(page, selector: str) -> None:
    loc = page.locator(selector)
    loc.scroll_into_view_if_needed()
    try:
        loc.click(timeout=8000)
    except Exception:
        loc.evaluate("el => el.click()")


def safe_err(exc: BaseException) -> str:
    return str(exc).encode("ascii", errors="replace").decode("ascii")


def main() -> int:
    failed = 0
    with sync_playwright() as p:
        browser, label = launch_browser(p)
        if not browser:
            print("ERROR: no Playwright browser available")
            return 2
        print(f"Browser: {label}\n")
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        for name, url, nav, tab, panel, url_need in CASES:
            print(f"=== {name} ===")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                if name == "Profile":
                    page.wait_for_selector("#profile-hub-nav", timeout=45000, state="attached")
                    page.wait_for_function(
                        "() => { const b = document.getElementById('profile-content-block'); "
                        "const o = document.getElementById('profile-loading-overlay'); "
                        "return b && b.style.display !== 'none' && (!o || o.offsetParent === null); }",
                        timeout=90000,
                    )
                    page.wait_for_selector("#profile-hub-nav", timeout=30000, state="visible")
                page.wait_for_selector(nav, timeout=20000)
                click_tab(page, tab)
                page.wait_for_timeout(500)
                if page.locator(panel).count() == 0:
                    print(f"  FAIL panel not visible: {panel}")
                    failed += 1
                    continue
                if url_need not in page.url:
                    print(f"  FAIL URL missing {url_need!r} (got {page.url})")
                    failed += 1
                    continue
                print("  PASS tab click, panel visible, URL updated")
            except Exception as exc:
                print(f"  FAIL {safe_err(exc)}")
                failed += 1

        browser.close()

    print("\n" + ("FAILED" if failed else "ALL PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
