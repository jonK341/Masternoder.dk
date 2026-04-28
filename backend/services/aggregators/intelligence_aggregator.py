"""
Intelligence Aggregator Service
Aggregates research papers, news, and intelligence from multiple external API sources.
Sources are configured in data/intelligence_sources.json (arXiv, Hacker News, NewsAPI, Open-Meteo, etc.).
"""
import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SOURCES_PATH = os.path.join(BASE_DIR, "data", "intelligence_sources.json")


def _load_sources_config() -> Dict[str, Any]:
    """Load intelligence sources config from data/intelligence_sources.json."""
    if not os.path.exists(SOURCES_PATH):
        return {"sources": [], "request_timeout_seconds": 15}
    try:
        with open(SOURCES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"sources": [], "request_timeout_seconds": 15}


def _ns(tag: str) -> str:
    """arXiv API uses Atom namespace."""
    return f"{http://www.w3.org/2005/Atom}{tag}" if "}" not in tag else tag


class IntelligenceAggregator:
    """Aggregates intelligence from multiple external sources."""

    def __init__(self):
        self.cache_duration = {
            "research": 21600,  # 6 hours
            "news": 3600,       # 1 hour
            "trending": 1800,   # 30 minutes
            "weather": 3600,
        }
        self.cache = {}
        self._request_timeout = 15

    def get_sources(self) -> Dict[str, Any]:
        """List configured intelligence sources and their status (enabled, has_api_key)."""
        config = _load_sources_config()
        sources = config.get("sources", [])
        timeout = config.get("request_timeout_seconds", 15)
        out = []
        for s in sources:
            env_key = s.get("env_key")
            has_key = True
            if env_key:
                has_key = bool(os.environ.get(env_key))
            out.append({
                "id": s.get("id"),
                "name": s.get("name"),
                "type": s.get("type"),
                "enabled": s.get("enabled", True),
                "description": s.get("description"),
                "has_api_key": has_key if env_key else None,
                "configured": s.get("enabled", True) and (has_key if env_key else True),
            })
        return {
            "success": True,
            "sources": out,
            "request_timeout_seconds": timeout,
        }

    def _fetch_url(self, url: str, timeout: Optional[int] = None) -> Optional[requests.Response]:
        """GET URL with timeout; returns None on failure."""
        try:
            t = timeout or getattr(self, "_request_timeout", 15)
            r = requests.get(url, timeout=t)
            r.raise_for_status()
            return r
        except Exception:
            return None

    def get_research_papers(self, limit: int = 10, category: str = "all") -> Dict[str, Any]:
        """
        Get research papers from arXiv (real API). Fallback to mock if API fails.
        Categories: ai, machine-learning, computer-vision, all
        """
        cache_key = f"research_{category}_{limit}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_duration["research"]:
                return cached_data

        config = _load_sources_config()
        arxiv = next((s for s in config.get("sources", []) if s.get("id") == "arxiv" and s.get("enabled")), None)
        papers = []

        if arxiv:
            category_map = arxiv.get("category_map") or {
                "ai": "cs.AI",
                "machine-learning": "cs.LG",
                "computer-vision": "cs.CV",
                "all": "cs.AI+OR+cat:cs.LG+OR+cat:cs.CV",
            }
            cat_query = category_map.get(category, category_map.get("all", "cs.AI"))
            url = arxiv.get("url_template", "").replace("{category}", cat_query).replace("{limit}", str(min(limit, 30)))
            resp = self._fetch_url(url)
            if resp is not None:
                try:
                    root = ET.fromstring(resp.content)
                    ns = "http://www.w3.org/2005/Atom"
                    for entry in root.findall(f".//{{{ns}}}entry")[:limit]:
                        title_el = entry.find(f"{{{ns}}}title")
                        id_el = entry.find(f"{{{ns}}}id")
                        published_el = entry.find(f"{{{ns}}}published")
                        summary_el = entry.find(f"{{{ns}}}summary")
                        authors = entry.findall(f"{{{ns}}}author")
                        title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""
                        link = (id_el.text or "").strip() if id_el is not None else ""
                        arxiv_id = link.split("/")[-1] if "/" in link else link
                        published = (published_el.text or "")[:19].replace("T", " ") if published_el is not None else ""
                        abstract = (summary_el.text or "").strip().replace("\n", " ")[:500] if summary_el is not None else ""
                        author_names = []
                        for a in authors:
                            name_el = a.find(f"{{{ns}}}name")
                            if name_el is not None and name_el.text:
                                author_names.append(name_el.text.strip())
                        papers.append({
                            "id": f"arxiv:{arxiv_id}",
                            "title": title,
                            "authors": author_names or ["Unknown"],
                            "abstract": abstract,
                            "published": published,
                            "category": category,
                            "url": link or f"https://arxiv.org/abs/{arxiv_id}",
                            "source": "arXiv",
                        })
                except Exception:
                    pass

        if not papers:
            for i in range(limit):
                papers.append({
                    "id": f"arxiv:mock_{i}",
                    "title": f"Research Paper {i+1}: Advanced AI Techniques",
                    "authors": [f"Author {i+1}A", f"Author {i+1}B"],
                    "abstract": "This paper presents novel approaches to AI and machine learning...",
                    "published": (datetime.now() - timedelta(days=i)).isoformat()[:19],
                    "category": category,
                    "url": "https://arxiv.org/",
                    "source": "arXiv (fallback)",
                })

        result = {
            "success": True,
            "papers": papers,
            "total": len(papers),
            "category": category,
            "cached": False,
            "timestamp": datetime.now().isoformat(),
        }
        self.cache[cache_key] = (result, time.time())
        return result

    def get_news(self, limit: int = 10, source: str = "all") -> Dict[str, Any]:
        """
        Get news from Hacker News (real API) and optionally NewsAPI if key set. Fallback to mock.
        """
        cache_key = f"news_{source}_{limit}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_duration["news"]:
                return cached_data

        news_items: List[Dict[str, Any]] = []
        config = _load_sources_config()

        # Hacker News (public)
        hn = next((s for s in config.get("sources", []) if s.get("id") == "hackernews" and s.get("enabled")), None)
        if hn:
            resp = self._fetch_url(hn.get("url_template", "https://hacker-news.firebaseio.com/v0/topstories.json"))
            if resp is not None:
                try:
                    ids = resp.json()[: limit * 2]
                    for sid in ids[:limit]:
                        item_resp = self._fetch_url(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                        if item_resp is not None:
                            item = item_resp.json()
                            news_items.append({
                                "id": f"hn_{item.get('id', sid)}",
                                "title": (item.get("title") or "")[:200],
                                "summary": (item.get("title") or "")[:300],
                                "source": "hackernews",
                                "published": datetime.fromtimestamp(item.get("time", 0)).isoformat() if item.get("time") else "",
                                "url": item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id', sid)}",
                                "category": "technology",
                            })
                except Exception:
                    pass

        # NewsAPI (optional, needs key)
        newsapi = next((s for s in config.get("sources", []) if s.get("id") == "newsapi" and s.get("enabled")), None)
        if newsapi and not news_items:
            api_key = os.environ.get(newsapi.get("env_key") or "NEWSAPI_API_KEY")
            if api_key:
                url = (newsapi.get("url_template") or "").replace("{limit}", str(limit)).replace("{api_key}", api_key)
                resp = self._fetch_url(url)
                if resp is not None:
                    try:
                        data = resp.json()
                        for art in (data.get("articles") or [])[:limit]:
                            if art.get("title") and art.get("title") != "[Removed]":
                                news_items.append({
                                    "id": f"newsapi_{art.get('publishedAt', '')}_{len(news_items)}",
                                    "title": (art.get("title") or "")[:200],
                                    "summary": (art.get("description") or art.get("title", ""))[:300],
                                    "source": "newsapi",
                                    "published": (art.get("publishedAt") or "")[:19],
                                    "url": art.get("url") or "",
                                    "image": art.get("urlToImage") or "",
                                    "category": "technology",
                                })
                    except Exception:
                        pass

        if not news_items:
            for i in range(limit):
                news_items.append({
                    "id": f"news_{i}",
                    "title": f"Tech News {i+1}: Latest Updates",
                    "summary": "Breaking news from technology and AI...",
                    "source": "fallback",
                    "published": (datetime.now() - timedelta(hours=i)).isoformat()[:19],
                    "url": "https://masternoder.dk",
                    "category": "technology",
                })

        result = {
            "success": True,
            "news": news_items[:limit],
            "total": len(news_items[:limit]),
            "sources": list({n.get("source") for n in news_items}),
            "cached": False,
            "timestamp": datetime.now().isoformat(),
        }
        self.cache[cache_key] = (result, time.time())
        return result

    def get_trending(self, limit: int = 10) -> Dict[str, Any]:
        """Get trending intelligence topics (curated list; can be extended with external APIs)."""
        cache_key = f"trending_{limit}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_duration["trending"]:
                return cached_data

        topics = [
            "AI Video Generation",
            "Machine Learning Advances",
            "Computer Vision Breakthroughs",
            "Neural Networks",
            "Deep Learning",
            "Natural Language Processing",
            "Reinforcement Learning",
            "Generative AI",
            "Large Language Models",
            "AI Ethics",
        ]
        trending = []
        for i, topic in enumerate(topics[:limit]):
            trending.append({
                "id": f"trending_{i}",
                "topic": topic,
                "trend_score": 100 - i * 5,
                "mentions": 1000 - i * 50,
                "growth": f"+{(10 - i) * 5}%",
                "category": "ai" if i < 5 else "technology",
                "timestamp": datetime.now().isoformat(),
            })
        result = {
            "success": True,
            "trending": trending,
            "total": len(trending),
            "cached": False,
            "timestamp": datetime.now().isoformat(),
        }
        self.cache[cache_key] = (result, time.time())
        return result

    def get_weather(self) -> Dict[str, Any]:
        """Get current weather from Open-Meteo (public API). Optional intelligence for context."""
        cache_key = "weather"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if time.time() - cached_time < self.cache_duration.get("weather", 3600):
                return cached_data

        config = _load_sources_config()
        meteo = next((s for s in config.get("sources", []) if s.get("id") == "open_meteo" and s.get("enabled")), None)
        if not meteo:
            result = {"success": False, "error": "Open-Meteo not enabled", "source": None}
        else:
            url = meteo.get("url_template", "https://api.open-meteo.com/v1/forecast?latitude=55.68&longitude=12.57&current=temperature_2m,weather_code&timezone=Europe/Copenhagen")
            resp = self._fetch_url(url)
            if resp is not None:
                try:
                    data = resp.json()
                    current = data.get("current", {})
                    result = {
                        "success": True,
                        "temperature_2m": current.get("temperature_2m"),
                        "weather_code": current.get("weather_code"),
                        "source": "open_meteo",
                        "timestamp": datetime.now().isoformat(),
                    }
                except Exception as e:
                    result = {"success": False, "error": str(e), "source": "open_meteo"}
            else:
                result = {"success": False, "error": "Request failed", "source": "open_meteo"}
        self.cache[cache_key] = (result, time.time())
        return result

    def get_all_intelligence(self, research_limit: int = 5, news_limit: int = 5, trending_limit: int = 5) -> Dict[str, Any]:
        """Get research, news, and trending combined; optionally include weather."""
        try:
            research = self.get_research_papers(limit=research_limit)
            news = self.get_news(limit=news_limit)
            trending = self.get_trending(limit=trending_limit)
            weather = self.get_weather()
            return {
                "success": True,
                "research": research.get("papers", []),
                "news": news.get("news", []),
                "trending": trending.get("trending", []),
                "weather": weather if weather.get("success") else None,
                "summary": {
                    "total_research": len(research.get("papers", [])),
                    "total_news": len(news.get("news", [])),
                    "total_trending": len(trending.get("trending", [])),
                    "total_items": len(research.get("papers", [])) + len(news.get("news", [])) + len(trending.get("trending", [])),
                },
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "research": [],
                "news": [],
                "trending": [],
            }


intelligence_aggregator = IntelligenceAggregator()
