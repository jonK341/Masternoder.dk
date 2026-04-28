# Generator Page – Cache Fix (Browser Always Gets Latest)

## The Problem

Browser interface updates were not visible because multiple cache layers served old content:
- **HTTP cache** – Browser cached the HTML (meta tags don't prevent this)
- **Service Worker** – Cached responses
- **Nginx** – May serve static files with default caching

## Research Finding

**HTTP `Cache-Control: no-store` from the server is the only reliable way** to prevent HTML caching. Meta tags and client-side tricks do not reliably affect the initial request.

## The Solution (Server-Side)

### 1. Nginx config

`scripts/setup_generator_no_cache.py` adds a dedicated location for `/vidgenerator/generator`:

- Proxies requests to Flask (instead of serving static files)
- Sends `Cache-Control: no-store, no-cache, must-revalidate`
- Ensures the browser always fetches fresh HTML

### 2. How to apply

**Run once (or as part of deploy):**
```bash
python scripts/setup_generator_no_cache.py
```

**Or use full deploy (includes this step):**
```bash
python scripts/deploy_vidgenerator_solution.py
```

### 3. Result

- Visiting https://masternoder.dk/vidgenerator/generator/ will always hit the server
- No hard refresh or manual cache clear needed
- Deploy changes and reload the page to see updates

## If Updates Still Don't Show

1. Run: `python scripts/setup_generator_no_cache.py` (reapply nginx config)
2. Unregister Service Worker: DevTools → Application → Service Workers → Unregister
3. Hard refresh: Ctrl+Shift+R (Cmd+Shift+R on Mac)
