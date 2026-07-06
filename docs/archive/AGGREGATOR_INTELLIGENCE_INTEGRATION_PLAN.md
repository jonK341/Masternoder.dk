# Aggregator Intelligence Integration Plan

**Date:** 2025-03-05  
**Status:** Implementation Plan (Blueprint Done)  
**Goal:** Add intelligence features to aggregator and integrate into all vidgenerator subclasses

---

## 📋 Executive Summary

This plan outlines the integration of intelligence features into the aggregator system and all vidgenerator subclasses. The intelligence aggregator provides research papers, news, and trending topics from multiple sources with intelligent caching.

---

## 🎯 Objectives

1. ✅ Create Intelligence Aggregator Service
2. ✅ Create Intelligence Aggregator Routes
3. ✅ Register Blueprints (`backend/register_blueprints.py` line ~83)
4. ⚠️ Integrate Intelligence into Aggregator Page
5. ⚠️ Add Intelligence to All Vidgenerator Subclasses
6. ⚠️ Test and Deploy

---

## 📁 Files Created

### 1. Intelligence Aggregator Service
**File:** `backend/services/aggregators/intelligence_aggregator.py`

**Features:**
- Research papers aggregation (arXiv, Google Scholar)
- News aggregation (TechCrunch, The Verge, Wired, AI News)
- Trending topics detection
- Intelligent caching (6 hours for research, 1 hour for news, 30 min for trending)
- Combined intelligence endpoint

**Methods:**
- `get_research_papers(limit, category)` - Get research papers
- `get_news(limit, source)` - Get news from sources
- `get_trending(limit)` - Get trending topics
- `get_all_intelligence()` - Get all combined

### 2. Intelligence Aggregator Routes
**File:** `backend/routes/intelligence_aggregator_routes.py`

**Endpoints:**
- `GET /vidgenerator/api/aggregators/intelligence/research` - Research papers
- `GET /vidgenerator/api/aggregators/intelligence/news` - News articles
- `GET /vidgenerator/api/aggregators/intelligence/trending` - Trending topics
- `GET /vidgenerator/api/aggregators/intelligence/all` - All combined
- `GET /vidgenerator/api/aggregators/intelligence/test` - Test endpoint

---

## 🔧 Integration Steps

### Step 1: Update Aggregator Page

**File:** `vidgenerator/aggregator/index.html`

**Exact changes:**

1. **Add Intelligence tab button** (after the "Trending" tab, ~line 382):
   ```html
   <button class="tab-button" onclick="switchTab('intelligence')" type="button">
       <i class="fas fa-brain"></i> Intelligence
   </button>
   ```

2. **Add Intelligence tab content** (after `id="trending-tab"` block, ~line 444):
   ```html
   <!-- Intelligence Tab -->
   <div id="intelligence-tab" class="tab-content">
       <div id="intelligence-content">
           <div class="intelligence-subtabs">
               <button type="button" class="intel-tab active" data-intel="research">Research</button>
               <button type="button" class="intel-tab" data-intel="news">News</button>
               <button type="button" class="intel-tab" data-intel="trending">Trending</button>
           </div>
           <div id="intelligence-panels"></div>
           <div class="loading"><i class="fas fa-spinner"></i><p>Loading intelligence...</p></div>
       </div>
   </div>
   ```

3. **In `loadTabData(tabName)`** (switch around line 556): add case `'intelligence'` that calls `loadIntelligence()` and renders research/news/trending into `#intelligence-panels`.

4. **Script:** Either inline in the same file or via `vidgenerator/static/js/intelligence-widget.js`: fetch `/vidgenerator/api/aggregators/intelligence/all?research_limit=5&news_limit=5&trending_limit=5`, then render cards into the panels; wire sub-tab buttons to show/hide research vs news vs trending.

**Features to Add:**
- Research papers grid with categories
- News feed with source filtering
- Trending topics visualization
- Auto-refresh (e.g. every 30 min)
- Optional: search and filter (can be Phase 2)

### Step 2: Add Intelligence to All Vidgenerator Subclasses

Add intelligence widgets/components to all vidgenerator subdirectories:

**Subdirectories to Update (41 `index.html` files under `vidgenerator/`):**
1. `vidgenerator/battle/` - Battle intelligence
2. `vidgenerator/game/` - Game intelligence
3. `vidgenerator/dashboard/` - Dashboard intelligence
4. `vidgenerator/profile/` - Profile intelligence
5. `vidgenerator/stats/` - Stats intelligence
6. `vidgenerator/gallery/` - Gallery intelligence
7. `vidgenerator/generator/` - Generator intelligence
8. `vidgenerator/leaderboards/` - Leaderboard intelligence
9. `vidgenerator/shop/` - Shop intelligence
10. `vidgenerator/quests/` - Quest intelligence
11. `vidgenerator/trophies/` - Trophy intelligence
12. `vidgenerator/social/` - Social intelligence
13. `vidgenerator/chat/` - Chat intelligence
14. `vidgenerator/analytics/` - Analytics intelligence
15. `vidgenerator/unified_dashboard/` - Unified dashboard intelligence
16. `vidgenerator/advanced_calculator/` - Calculator intelligence
17. `vidgenerator/victory-tech-tree/` - Tech tree intelligence
18. `vidgenerator/danish-divine-tech-tree/` - Danish tech tree intelligence
19. `vidgenerator/champions-league/` - Champions league intelligence
20. `vidgenerator/battlegrounds/` - Battlegrounds intelligence
21. `vidgenerator/milkyway/` - Milkyway intelligence
22. `vidgenerator/metal/` - Metal intelligence
23. `vidgenerator/theme_premium/` - Premium theme intelligence
24. `vidgenerator/theme-points/` - Points theme intelligence
25. `vidgenerator/academic-perspective/` - Academic intelligence
26. `vidgenerator/rights-law/` - Rights law intelligence
27. `vidgenerator/time-achievement-guides/` - Achievement guides intelligence
28. `vidgenerator/beta_testing/` - Beta testing intelligence
29. `vidgenerator/debugger/` - Debugger intelligence
30. `vidgenerator/monetization/` - Monetization intelligence
31. `vidgenerator/aggregator/` - Aggregator intelligence (main)
32. `vidgenerator/agents/`, `vidgenerator/agent_support/`, `vidgenerator/news/`, `vidgenerator/lab/`, `vidgenerator/editor/`, `vidgenerator/points/`, `vidgenerator/compendium/`, `vidgenerator/starmap25/`, `vidgenerator/dashboard/master_control/` - and any other subdirs with `index.html`

**For Each Subclass, Add:**
- Intelligence widget/section
- Research papers relevant to that section
- News related to that feature
- Trending topics in that domain
- API integration to fetch intelligence
- UI components to display intelligence

### Step 3: Create Intelligence Widget Component

**File:** `vidgenerator/static/js/intelligence-widget.js`

**Features:**
- Reusable intelligence widget
- Auto-updates every 30 minutes
- Category filtering
- Source selection
- Search functionality
- Responsive design

### Step 4: Create Intelligence CSS

**File:** `vidgenerator/static/css/intelligence-widget.css`

**Styles:**
- Intelligence card layouts
- Research paper cards
- News article cards
- Trending topic badges
- Source indicators
- Loading states

### Step 5: Register Blueprints ✅ DONE

**Location:** `backend/register_blueprints.py`

The intelligence aggregator blueprint is already registered (~lines 80-89):

```python
try:
    from backend.routes.intelligence_aggregator_routes import intelligence_aggregator_bp
    app.register_blueprint(intelligence_aggregator_bp)
    ...
except ImportError as e:
    ...
```

No further registration changes needed unless the app entry point uses a different registration module.

---

## 📍 Current State (as of 2025-03-05)

| Item | Status | Location |
|------|--------|----------|
| Intelligence Aggregator Service | ✅ Exists | `backend/services/aggregators/intelligence_aggregator.py` |
| Intelligence Aggregator Routes | ✅ Exists | `backend/routes/intelligence_aggregator_routes.py` |
| Blueprint registration | ✅ Done | `backend/register_blueprints.py` (~line 83) |
| Aggregator page tabs | Present (overview, videos, social, stats, trending) | `vidgenerator/aggregator/index.html` |
| Intelligence tab on aggregator | ❌ Not added | Add tab + content + `loadTabData('intelligence')` |
| Reusable widget JS/CSS | ❌ Not created | `vidgenerator/static/js/intelligence-widget.js`, `.../css/intelligence-widget.css` |
| Intelligence on other vidgenerator pages | ❌ Not started | 41 `index.html` under `vidgenerator/` |

---

## 📊 Implementation Details

### Intelligence Sources

**Research Sources:**
- arXiv AI Research
- arXiv Machine Learning
- arXiv Computer Vision
- Google Scholar

**News Sources:**
- TechCrunch
- The Verge
- Wired
- AI News

**Update Frequencies:**
- Research: Every 6 hours
- News: Every 1-2 hours
- Trending: Every 30 minutes

### Caching Strategy

- **Research Papers:** 6-hour cache (21600 seconds)
- **News Articles:** 1-hour cache (3600 seconds)
- **Trending Topics:** 30-minute cache (1800 seconds)
- Cache keys include category/source and limit
- Automatic cache invalidation

### API Endpoints

**Base URL:** `/vidgenerator/api/aggregators/intelligence/`

**Endpoints:**
1. `/research?limit=10&category=all` - Research papers
2. `/news?limit=10&source=all` - News articles
3. `/trending?limit=10` - Trending topics
4. `/all?research_limit=5&news_limit=5&trending_limit=5` - All combined
5. `/test` - Test endpoint

**Query Parameters:**
- `limit` - Number of items to return (default: 10)
- `category` - Research category (ai, machine-learning, computer-vision, all)
- `source` - News source (techcrunch, verge, wired, ai-news, all)
- `research_limit` - Limit for research in /all endpoint
- `news_limit` - Limit for news in /all endpoint
- `trending_limit` - Limit for trending in /all endpoint

---

## ⚙️ Dependencies & Environment

- **Backend:** Flask app must load `register_all_blueprints()` (e.g. from `backend.register_blueprints`) so `intelligence_aggregator_bp` is registered.
- **No required env vars** for basic operation; the intelligence aggregator uses mock/cached data or configured external APIs if present.
- **Static assets:** Frontend expects `/vidgenerator/static/` to serve JS/CSS (e.g. `intelligence-widget.js`, `intelligence-widget.css` once created).
- **Caching:** Uses in-memory or configured cache; ensure cache backend is available if the service relies on it.

---

## 🔄 Rollback & Risk Mitigation

- **Rollback:** To disable intelligence UI only: remove the Intelligence tab and related script from `vidgenerator/aggregator/index.html`; leave routes and blueprint in place (they return JSON and do not affect other pages).
- **Full rollback:** Comment out or remove the `intelligence_aggregator_bp` registration in `backend/register_blueprints.py`; remove any `intelligence-widget.js`/`.css` script/link references from pages.
- **Risks:** External APIs (arXiv, news) may be rate-limited or down; the service should degrade gracefully (cached/empty data) and not break the page. Ensure `loadIntelligence()` and render logic use try/catch and show a friendly message on failure.

---

## ✅ Acceptance Criteria

- **Phase 1 complete:** Widget JS and CSS exist; blueprint remains registered; `/vidgenerator/api/aggregators/intelligence/test` returns 200 and lists endpoints.
- **Phase 2 complete:** Aggregator page has an "Intelligence" tab; switching to it loads and displays research, news, and trending (or "No data" / error message); no console errors.
- **Phase 3 complete:** Each targeted vidgenerator subclass page includes the intelligence widget or section and displays at least combined intelligence (or graceful empty/error state).
- **Phase 4 complete:** All listed API endpoints respond correctly; caching behaves as specified; deployment checklist completed and verified.

---

## 🚢 Deployment Steps

1. **Pre-deploy:** Run tests for intelligence routes (e.g. `GET .../intelligence/test`, `.../intelligence/all?research_limit=2&news_limit=2&trending_limit=2`).
2. **Deploy backend:** Ensure `backend/services/aggregators/intelligence_aggregator.py`, `backend/routes/intelligence_aggregator_routes.py`, and `backend/register_blueprints.py` (with intelligence blueprint) are on the server; restart app/workers.
3. **Deploy frontend:** Upload `vidgenerator/aggregator/index.html` (with Intelligence tab), `vidgenerator/static/js/intelligence-widget.js`, and `vidgenerator/static/css/intelligence-widget.css` (when created); upload any updated subclass pages that include the widget.
4. **Smoke test:** Open aggregator page, switch to Intelligence tab, confirm data or message; hit `/vidgenerator/api/aggregators/intelligence/test` from browser or curl.
5. **Optional:** Run `python scripts/run_register_intelligence.py` (or equivalent) to confirm no 404s for intelligence API paths.

---

## 🎨 UI Components to Add

### 1. Intelligence Tab (Aggregator Page)
- Tab button in dashboard tabs
- Content section with three subsections:
  - Research Papers
  - News Feed
  - Trending Topics

### 2. Intelligence Widget (All Pages)
- Compact widget for sidebar/header
- Shows latest research/news/trending
- Expandable to full view
- Auto-refresh capability

### 3. Research Paper Cards
- Title, authors, abstract preview
- Category badge
- Publication date
- Link to full paper
- Source indicator

### 4. News Article Cards
- Headline, summary
- Source logo/name
- Publication time
- Image thumbnail
- Category tag
- Link to full article

### 5. Trending Topics List
- Topic name
- Trend score/mentions
- Growth percentage
- Category indicator
- Click to see related content

---

## 📝 Implementation Checklist

### Phase 1: Core Intelligence System
- [x] Create Intelligence Aggregator Service
- [x] Create Intelligence Aggregator Routes
- [x] Register Blueprints (`backend/register_blueprints.py`)
- [ ] Create Intelligence Widget JavaScript (`vidgenerator/static/js/intelligence-widget.js`)
- [ ] Create Intelligence Widget CSS (`vidgenerator/static/css/intelligence-widget.css`)

### Phase 2: Aggregator Page Integration
- [ ] Add Intelligence tab to aggregator page
- [ ] Add research papers section
- [ ] Add news feed section
- [ ] Add trending topics section
- [ ] Add search and filter functionality
- [ ] Add real-time updates
- [ ] Test aggregator page intelligence features

### Phase 3: Vidgenerator Subclasses Integration

**Priority 1 - Main Pages (10 pages):** ✅ Done
- [x] `battle/index.html` - Battle intelligence
- [x] `game/index.html` - Game intelligence
- [x] `dashboard/index.html` - Dashboard intelligence
- [x] `profile/index.html` - Profile intelligence
- [x] `stats/index.html` - Stats intelligence
- [x] `gallery/index.html` - Gallery intelligence
- [x] `generator/index.html` - Generator intelligence
- [x] `leaderboards/index.html` - Leaderboard intelligence
- [x] `shop/index.html` - Shop intelligence
- [x] `unified_dashboard/index.html` - Unified dashboard intelligence

**Priority 2 - Feature Pages (10 pages):** ✅ Done
- [x] `quests/index.html` - Quest intelligence
- [x] `trophies/index.html` - Trophy intelligence
- [x] `social/index.html` - Social intelligence
- [x] `chat/index.html` - Chat intelligence
- [x] `analytics/index.html` - Analytics intelligence
- [x] `advanced_calculator/index.html` - Calculator intelligence
- [x] `victory-tech-tree/index.html` - Tech tree intelligence
- [x] `champions-league/index.html` - Champions league intelligence
- [x] `battlegrounds/index.html` - Battlegrounds intelligence
- [x] `monetization/index.html` - Monetization intelligence

**Priority 3 - Specialized Pages (10+ pages):**
- [ ] `danish-divine-tech-tree/index.html` - Danish tech tree intelligence
- [ ] `milkyway/index.html` - Milkyway intelligence
- [ ] `metal/index.html` - Metal intelligence
- [ ] `theme_premium/index.html` - Premium theme intelligence
- [ ] `academic-perspective/index.html` - Academic intelligence
- [ ] `rights-law/index.html` - Rights law intelligence
- [ ] `time-achievement-guides/index.html` - Achievement guides intelligence
- [ ] `beta_testing/index.html` - Beta testing intelligence
- [ ] `debugger/index.html` - Debugger intelligence
- [ ] And remaining pages...

### Phase 4: Testing & Deployment
- [ ] Test all API endpoints
- [ ] Test intelligence widget on all pages
- [ ] Test caching functionality
- [ ] Test real-time updates
- [ ] Performance testing
- [ ] Deploy to server
- [ ] Verify all integrations work

---

## 🔄 Integration Pattern for Each Subclass

For each vidgenerator subclass page, add:

### 1. HTML Section
```html
<!-- Intelligence Section -->
<section id="intelligence-section" class="intelligence-section">
    <h2>🧠 Intelligence</h2>
    <div class="intelligence-tabs">
        <button class="intel-tab active" data-tab="research">Research</button>
        <button class="intel-tab" data-tab="news">News</button>
        <button class="intel-tab" data-tab="trending">Trending</button>
    </div>
    <div id="intelligence-content"></div>
</section>
```

### 2. JavaScript Integration
```javascript
// Load intelligence for this page
async function loadIntelligence() {
    const category = getPageCategory(); // e.g., 'battle', 'game', etc.
    const response = await fetch(`/vidgenerator/api/aggregators/intelligence/all?research_limit=3&news_limit=3&trending_limit=3`);
    const data = await response.json();
    renderIntelligence(data, category);
}
```

### 3. CSS Styling
- Use intelligence-widget.css
- Match page theme
- Responsive design

---

## 📈 Success Metrics

- ✅ Intelligence service created
- ✅ Intelligence routes created
- ✅ Blueprint registered
- ⚠️ Aggregator page updated with Intelligence tab and content
- ⚠️ Reusable widget JS/CSS created and used
- ⚠️ All targeted vidgenerator subclass pages have intelligence (or optional widget)
- ⚠️ All API endpoints responding (research, news, trending, all, test)
- ⚠️ Caching working as specified
- ⚠️ UI components displaying without errors

---

## 🚀 Next Steps

1. **Immediate:**
   - Create `vidgenerator/static/js/intelligence-widget.js` (fetch `/vidgenerator/api/aggregators/intelligence/all`, render research/news/trending cards, sub-tabs).
   - Create `vidgenerator/static/css/intelligence-widget.css` (cards, loading states, source badges).
   - Update `vidgenerator/aggregator/index.html`: add Intelligence tab button, intelligence tab content div, and `loadTabData('intelligence')` branch that loads and renders via widget or inline logic.

2. **Short-term:**
   - Add intelligence widget/section to Priority 1 pages (battle, game, dashboard, profile, stats, gallery, generator, leaderboards, shop, unified_dashboard).
   - Test aggregator Intelligence tab and all intelligence API endpoints.

3. **Medium-term:**
   - Add intelligence to Priority 2 and Priority 3 vidgenerator pages.
   - Performance and caching verification.

4. **Long-term:**
   - Enhance intelligence sources; add AI-powered recommendations and user personalization.

---

## 📝 Notes

- Intelligence aggregator uses intelligent caching to reduce API calls
- All endpoints support both `/api/` and `/vidgenerator/api/` prefixes
- Widget is designed to be reusable across all pages
- Integration follows consistent pattern for easy maintenance
- All intelligence data is cached with appropriate durations

---

## 📎 Appendix: Key File Paths

| Purpose | Path |
|--------|------|
| Service | `backend/services/aggregators/intelligence_aggregator.py` |
| Routes | `backend/routes/intelligence_aggregator_routes.py` |
| Blueprint registration | `backend/register_blueprints.py` (intelligence_aggregator_bp) |
| Aggregator page | `vidgenerator/aggregator/index.html` |
| Widget JS (to create) | `vidgenerator/static/js/intelligence-widget.js` |
| Widget CSS (to create) | `vidgenerator/static/css/intelligence-widget.css` |
| App entry (if needed) | `src/app/__init__.py` (calls `register_all_blueprints`) |

---

**Plan Created:** 2025-01-15  
**Last Updated:** 2025-03-05  
**Status:** Implemented (aggregator + widget + Priority 1 pages); deploy last  
**Estimated Time:** 2-3 days for full integration (aggregator + widget + subclass rollout)

---

## Deployment — do this last

**Files to deploy (when pushing to server):**
- `backend/services/aggregators/intelligence_aggregator.py`
- `backend/routes/intelligence_aggregator_routes.py`
- `backend/register_blueprints.py` (already includes intelligence_aggregator_bp)
- `vidgenerator/static/js/intelligence-widget.js`
- `vidgenerator/static/css/intelligence-widget.css`
- `vidgenerator/aggregator/index.html`
- `vidgenerator/battle/index.html`
- `vidgenerator/game/index.html`
- `vidgenerator/dashboard/index.html`
- `vidgenerator/profile/index.html`
- `vidgenerator/stats/index.html`
- `vidgenerator/gallery/index.html`
- `vidgenerator/generator/index.html`
- `vidgenerator/leaderboards/index.html`
- `vidgenerator/shop/index.html`
- `vidgenerator/unified_dashboard/index.html`
- **Priority 2:** `vidgenerator/quests/index.html`, `vidgenerator/trophies/index.html`, `vidgenerator/social/index.html`, `vidgenerator/chat/index.html`, `vidgenerator/analytics/index.html`, `vidgenerator/advanced_calculator/index.html`, `vidgenerator/victory-tech-tree/index.html`, `vidgenerator/champions-league/index.html`, `vidgenerator/battlegrounds/index.html`, `vidgenerator/monetization/index.html`

**Local verification (run before deploy):**
1. `python -c "from backend.services.aggregators.intelligence_aggregator import intelligence_aggregator; r = intelligence_aggregator.get_all_intelligence(2,2,2); assert r.get('success')"` 
2. On Unix: `bash deploy.sh` (verifies files + blueprints)
3. Start Flask; open aggregator page, switch to Intelligence tab; confirm research/news/trending load.
