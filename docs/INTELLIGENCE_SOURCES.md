# Intelligence sources — external API integration

**Purpose:** The app pulls **intelligence from other sources** (research, news, weather) via the **Intelligence Aggregator**. Sources are configured in `data/intelligence_sources.json` and used by `backend/services/aggregators/intelligence_aggregator.py`.

---

## 1. Configured sources

| Source ID   | Type    | Description                    | API key      | Status   |
|------------|---------|--------------------------------|--------------|----------|
| **arxiv**  | research| CS/AI/ML/CV preprints          | None         | Real API |
| **hackernews** | news | HN top stories                 | None         | Real API |
| **newsapi**| news    | Headlines (technology)         | `NEWSAPI_API_KEY` | Optional |
| **open_meteo** | weather | Current weather (Copenhagen)   | None         | Real API |

- **arXiv** — `https://export.arxiv.org/api/query` (public). Used by `get_research_papers()`; fallback to mock if request fails.
- **Hacker News** — `https://hacker-news.firebaseio.com/v0/topstories.json` and `/v0/item/{id}.json` (public). Used by `get_news()`.
- **NewsAPI** — Set `NEWSAPI_API_KEY` in `.env` and set `"enabled": true` for `newsapi` in `intelligence_sources.json` to use it when Hacker News is not enough.
- **Open-Meteo** — `https://api.open-meteo.com/v1/forecast` (public). Used by `get_weather()` for optional context (e.g. “current conditions” in content).

---

## 2. Config file: `data/intelligence_sources.json`

```json
{
  "sources": [
    {
      "id": "arxiv",
      "name": "arXiv",
      "type": "research",
      "enabled": true,
      "description": "CS/AI/ML/CV preprints",
      "url_template": "https://export.arxiv.org/api/query?search_query=cat:{category}&max_results={limit}&sortBy=submittedDate&sortOrder=descending",
      "category_map": { "ai": "cs.AI", "machine-learning": "cs.LG", "computer-vision": "cs.CV", "all": "cs.AI+OR+cat:cs.LG+OR+cat:cs.CV" },
      "env_key": null,
      "cache_seconds": 21600
    }
  ],
  "request_timeout_seconds": 15
}
```

- **id** — Unique key (e.g. `arxiv`, `newsapi`).
- **enabled** — If `false`, the aggregator skips this source.
- **url_template** — URL with placeholders `{category}`, `{limit}`, `{api_key}` as needed.
- **env_key** — Env var name for API key (e.g. `NEWSAPI_API_KEY`). Omit or `null` for public APIs.
- **cache_seconds** — How long to cache responses (aggregator uses its own cache durations per type).

---

## 3. API endpoints (prefix `/api/aggregators/intelligence`)

| Method | Endpoint   | Description |
|--------|------------|-------------|
| GET    | `/research?limit=10&category=all` | Research papers (arXiv; categories: ai, machine-learning, computer-vision, all). |
| GET    | `/news?limit=10&source=all`        | News (Hacker News, optionally NewsAPI if key set). |
| GET    | `/trending?limit=10`               | Trending topics (curated). |
| GET    | `/all?research_limit=5&news_limit=5&trending_limit=5` | Combined research + news + trending + optional weather. |
| GET    | `/sources`                         | List sources and status (enabled, has_api_key). |
| GET    | `/weather`                         | Current weather (Open-Meteo). |
| GET    | `/test`                            | Health and list of endpoints/sources. |

---

## 4. Adding more sources

1. **Add an entry** to `sources` in `data/intelligence_sources.json`:
   - `id`, `name`, `type` (e.g. `research`, `news`, `weather`, `custom`),
   - `enabled`, `url_template`, optional `env_key`, `cache_seconds`.
2. **Optional: wire it in code** — In `intelligence_aggregator.py`, add a branch in `get_research_papers()`, `get_news()`, or a new method (e.g. `get_from_source(source_id)`) that builds the URL from `url_template`, calls `_fetch_url()`, and parses the response.
3. **API key** — If the source needs a key, set the env var (e.g. in `.env`) and set `env_key` in the config. `get_sources()` will report `has_api_key` so the UI can show “configured” or “missing key”.

**Example: add a “custom” JSON API**

- In `intelligence_sources.json` add a source with `"type": "custom"` and `url_template` pointing at a JSON endpoint.
- In the aggregator, add a generic fetcher that loads the source by `id`, replaces `{api_key}` from env if `env_key` is set, calls `_fetch_url()`, and returns `response.json()` (or a normalized shape) so other code can consume it.

---

## 5. Caching and timeouts

- Research: 6 h; news: 1 h; trending: 30 min; weather: 1 h (in code). Config `cache_seconds` can be used when implementing per-source cache.
- All outbound requests use a timeout (config `request_timeout_seconds`, default 15). Failed requests fall back to mock or empty data so the app stays responsive.

---

## 6. References

- **Aggregator service:** `backend/services/aggregators/intelligence_aggregator.py`
- **Routes:** `backend/routes/intelligence_aggregator_routes.py`
- **Config:** `data/intelligence_sources.json`
