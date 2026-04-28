# Production Readiness & Loose Ends

**Purpose:** Check production, public readiness, and tie loose ends for News, Rodo/GPS, Social, Statistics, Analytics, Chat, RDO, Recap, Agent Skill Sets — then execute the Profile/Points sync plan.

---

## 1. Production & Public Readiness

| Check | Status | Notes |
|-------|--------|--------|
| Profile ↔ Points sync | ✅ In plan | refreshProfilePoints, Sync session, URLs fixed |
| User ID / session | ✅ | bind-session, identity card, Sync session |
| Shop categories | ✅ | starmap25, boosts, gametime, trophies |
| Quests API | ✅ | /api/user/quests, progress, claim |
| Nav: Social, Chat, Stats, Analytics | ✅ | In PAGES and nav toolbar |
| News page | ✅ Done | `/vidgenerator/news` added; in PAGES and nav |
| Rodo / GPS | ⚠️ Doc | Geo in profile + hunters geo-ref; no standalone rodo/gps page yet |
| Recap | ✅ Done | Dashboard has "Daily recap" strip (Stats, Quests, Profile, News) |
| RDO | ⚠️ Doc | Documented as future; clarify with product |
| Agent skill sets | ✅ Done | Nav: Agents + Agent Support; both in PAGES |
| Statistics | ✅ Done | Stats in PAGES + nav as "Statistics" |
| Quests in nav | ✅ Done | Quests link added to nav; more quests in user_engagement |

---

## 2. Extended Loose Ends (to solve)

**Profile & Points (from PROFILE_POINTS_SYNC_PLAN.md)**  
- LE1–LE27: Already listed there (refresh points, URLs, loadPointsStats, etc.).

**Navigation & discovery**  
- **LE28:** Nav — ✅ Added "Statistics" (stats) and "Quests" to nav.  
- **LE29:** Quests in nav — ✅ Done.  
- **LE30:** Agent skill sets — ✅ Nav has "AI Agents" (agents) + "Agent Support"; both linked.  

**Missing / placeholder pages**  
- **LE31:** News — ✅ Added `/vidgenerator/news` (placeholder with platform updates); in PAGES and nav.  
- **LE32:** Rodo/GPS — Documented; profile identity + hunters geo-ref cover geo; standalone page optional.  
- **LE33:** Recap — ✅ Dashboard "Daily recap" strip links to Statistics, Quests, Profile, News.  
- **LE34:** RDO — Documented as future; clarify with product.  

**Shop & Quests**  
- **LE35:** More quests — ✅ Added 8 new templates (Star Map Scout, Chatter, Shopper, Reward Claim, Game Points, Segmentum Explorer, Content Creator, Social Week).  
- **LE36:** More gametime in shop — ✅ Added Game Time +1h, +4h, Weekend Pass; Star Map 25 +1h.  
- **LE37:** More boosters in shop — ✅ Added XP 2h, Battle Power 1h, Quest Booster; Star Map 25 Booster 6h.  

**Chat, Social, Analytics**  
- **LE38:** Chat — ✅ history and messages requests now include `user_id` from localStorage (game_user_id).  
- **LE39:** Social — ✅ already uses `game_user_id` for all API calls; links to profile.  
- **LE40:** Analytics — ✅ overview, trends, quality, usage, performance, errors now include `user_id` query param.  

**Agent skill sets**  
- **LE41:** Profile and Game — ✅ Profile has "Agent skills" link to agent_support; Game nav has "Agents" and "Agent skills" links.  
- **LE42:** Shop — ✅ "Skills" category exists; added "View agent skills & support" link to agent_support.  

---

## 3. Implementation Plan (execute)

1. **Profile & points (done)**  
   - refreshProfilePoints(), Refresh points button, Sync session → refresh points.  
   - Game/Battle/Dashboard points URLs fixed.  
   - loadPointsStats shape + game_points; Statistics section filled on load.  

2. **Quests**  
   - Add 8+ new quest templates (daily + weekly) in `user_engagement._QUEST_TEMPLATES`.  

3. **Shop**  
   - Add more gametime items (General +1h, +4h, Weekend Pass).  
   - Add more booster items (General XP 2h, Battle 1h, Quest Booster, Star Map 25 6h).  

4. **Nav**  
   - Add "Statistics" (or keep Stats discoverable via Dashboard).  
   - Add "Quests" link to nav.  
   - Optional: "Agent Skills" or ensure agents link is clear.  

5. **Placeholder / discovery**  
   - Add `news` to PAGES if we add `vidgenerator/news/index.html`, or document as coming soon.  
   - Recap: add "Recap" or "Daily recap" section/card on dashboard linking to stats/quests.  
   - Rodo/GPS: document in profile identity or add simple `/vidgenerator/gps` that shows geo status.  

6. **Chat / Social / Analytics**  
   - Ensure each uses `user_id` from localStorage (game_user_id) for API calls.  

---

## 4. Summary

- **Minimum 42 loose ends** identified (27 profile/points + 15 extended).  
- **Production:** Profile/points sync and URL fixes improve readiness; nav, quests, shop, and missing pages (news, recap, gps/rodo) need the above steps.  
- **Next:** Execute quests, shop, nav, then optional placeholders.
