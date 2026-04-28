# Conspiracy, Religious Conspiracy & Alternative Theories — Content Categories & Unified Points

**Purpose:** Add content categories to the site (conspiracy theories, religious conspiracy ideas, and “other unnormal theories”) and reward them through the **unified point system**.

---

## 1. Content Categories (25 methods in sections)

| Category | Description | Role on site |
|----------|-------------|--------------|
| **Conspiracy theories** | Conspiracy as a distinct category; can be contrasted with other unnormal theories. | User can pick when creating a clip; earns base + category bonus in unified points. |
| **Religious conspiracy ideas** | Conspiracy ideas with a religious angle (prophecy, end-times, hidden religious powers). | Same as above; separate category and optional higher bonus. |
| **Alternative / unnormal theories** | Other non-mainstream or “unnormal” ways and theories (fringe, alternative explanations). | Contrast bucket to conspiracy; also earns unified points. |
| **General** | Standard documentary/clip; no specific theory type. | Default; base points only. |

Data: `data/content_categories.json` — defines **sections** (for UI grouping) and **categories** (25 methods + general). Each method has `id`, `name`, `description`, `section_id`, `context`, `bonus_unified_points`, `unified_point_type`. Used for both video and clip generation.

---

## 2. Unified Point System (how categories plug in)

- **Single source of truth:** All rewards still go through `unified_points_database.add_points(...)`.
- **Base reward:** Every completed video gives **generation_points** (25 full documentary, 10 short clip).
- **Category bonus:** Optional extra added to **generation_points** and/or to a category-specific counter:
  - **conspiracy** → `conspiracy_points` (e.g. +5 per video).
  - **religious_conspiracy** → `religious_conspiracy_points` (e.g. +8 per video).
  - **alternative_theories** → `alternative_theory_points` (e.g. +5 per video).
- **Total unified points:** `generation_points` (and optionally XP/level) reflect the full amount (base + bonus). Category-specific keys are for stats and achievements (e.g. “10 conspiracy clips”, “5 religious conspiracy”).

So: one **unified** point system, with category-specific counters for variety and achievements.

---

## 3. Implementation outline

1. **API**
   - `GET /api/content-categories/list` returns `sections` and `categories` (25 methods) from `data/content_categories.json`.
2. **Generator create (video + clip)**
   - Request body may include `content_category` (one of the 25 method ids, e.g. `deep_state`, `religious_prophecy`, `general`) and optional `content_context` (rich description for the selected method). Stored in job `config.content_category` and `config.content_context`.
3. **Awarding points**
   - On video or clip completion, read `config.content_category`, look up bonus and `unified_point_type` in `content_categories.json`.
   - Add **generation_points** = base + category bonus; also add to category’s `unified_point_type` for stats.
4. **Frontend**
   - Generator page loads content categories and shows a **dropdown grouped by section** (optgroups). Same selector used for both full documentary and quick clip.
   - Selected method’s `context` is shown below the dropdown and sent with the request (prompt is augmented with content context for richer generation).

---

## 4. Summary

| Topic | Summary |
|-------|---------|
| **Conspiracy vs others** | Conspiracy is one category; “alternative/unnormal theories” is another, so the site can contrast them. |
| **Religious conspiracy** | Separate category (religious conspiracy ideas); can have its own bonus and stats. |
| **Unified points** | One system: base + optional category bonus → `generation_points`; category-specific keys for stats. |
| **Data** | `data/content_categories.json`; API exposes it; create flow and video_generator_service use it for points. |

---

## 5. Implementation status

| Item | Status |
|------|--------|
| `data/content_categories.json` (sections + 25 methods) | ✅ Done |
| `GET /api/content-categories/list` | ✅ Done |
| Unified create + fallback create accept `content_category`, `content_context` | ✅ Done |
| Points: base + category bonus in `video_generator_service` | ✅ Done |
| Generator UI: dropdown by section, context display, prompt augmentation | ✅ Done |
| Unit tests `test_10_content_categories.py` | ✅ Done |

*Align with GENERATOR_PAGE_AND_POINTS_OVERVIEW.md for the overall generator and unified point system.*
