#!/usr/bin/env python3
"""Crawl masternoder.dk public pages into the site_pages table.

READ-ONLY: issues plain HTTP GETs to public pages, stores title + visible text +
raw HTML + discovered links. No auth, no writes to the site, bounded page list.
Stdlib only (urllib). Upserts on path, so re-running refreshes rather than duplicates.
"""
import argparse
import json
import re
import sqlite3
import sys
import urllib.request
from html.parser import HTMLParser

DEFAULT_BASE = "https://masternoder.dk"
DEFAULT_PATHS = [
    "/", "/agents", "/agent_support", "/shop", "/wallets", "/news", "/podcast",
    "/game", "/casino/", "/generator", "/lab", "/create-app/", "/debugger",
    "/staking-leaderboard", "/staking-teams", "/starmap25/",
]
UA = "Mozilla/5.0 (compatible; mn2-migration-crawler/1.0)"


class Extractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "template"}

    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self.text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.SKIP:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._skip_depth == 0:
            s = data.strip()
            if s:
                self.text.append(s)


def fetch(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return resp.getcode(), body


def crawl_one(base, path, timeout):
    url = base.rstrip("/") + ("/" + path.lstrip("/") if path != "/" else "/")
    try:
        status, body = fetch(url, timeout)
    except Exception as exc:  # noqa: BLE001
        print(f"[crawl] {path:24} ERROR {exc}")
        return None
    html = body.decode("utf-8", errors="replace")
    ex = Extractor()
    try:
        ex.feed(html)
    except Exception:  # noqa: BLE001
        pass
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(ex.text))
    links = sorted(set(ex.links))
    print(f"[crawl] {path:24} {status}  {len(body):>7}B  title={ex.title.strip()[:40]!r}")
    return {
        "path": path if path != "/" else "/",
        "url": url,
        "title": ex.title.strip(),
        "http_status": status,
        "content_text": text,
        "content_html": html,
        "byte_size": len(body),
        "links_json": json.dumps(links),
    }


def upsert_page(conn, p):
    conn.execute(
        """INSERT INTO site_pages
             (path, url, title, http_status, content_text, content_html,
              byte_size, links_json, crawled_at)
           VALUES (?,?,?,?,?,?,?,?, CURRENT_TIMESTAMP)
           ON CONFLICT(path) DO UPDATE SET
             url=excluded.url, title=excluded.title, http_status=excluded.http_status,
             content_text=excluded.content_text, content_html=excluded.content_html,
             byte_size=excluded.byte_size, links_json=excluded.links_json,
             crawled_at=CURRENT_TIMESTAMP""",
        (p["path"], p["url"], p["title"], p["http_status"], p["content_text"],
         p["content_html"], p["byte_size"], p["links_json"]),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--paths", nargs="*", default=None,
                    help="override page paths (default: built-in list)")
    ap.add_argument("--no-html", action="store_true",
                    help="store visible text only, drop raw HTML to save space")
    args = ap.parse_args()

    paths = args.paths or DEFAULT_PATHS
    conn = sqlite3.connect(args.db)
    ok = fail = 0
    try:
        for path in paths:
            p = crawl_one(args.base, path, args.timeout)
            if not p:
                fail += 1
                continue
            if args.no_html:
                p["content_html"] = None
            upsert_page(conn, p)
            ok += 1
        conn.commit()
    finally:
        conn.close()
    print(f"[done] crawled ok={ok} fail={fail} -> site_pages")


if __name__ == "__main__":
    sys.exit(main())
