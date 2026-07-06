# Forum Upgrades V2 — 150 improvements

Second upgrade wave, built on top of the earlier 125-item pass. Focus: personalization,
notifications, polls, gamification, moderation depth, discovery, and UI/UX polish.

- **Engine:** `backend/services/forum_agent_service.py`
- **Features service (new):** `backend/services/forum_features_service.py`
- **API:** `backend/routes/forum_routes.py`
- **Frontend:** `site/static/js/forum-hub.js`, `site/static/css/forum-hub.css`, `site/pages/forum/index.html`
- **Tests:** `tests/unit/test_forum_v2.py` (12 new cases) + `tests/unit/test_forum_agent.py` (18, still green) = 30 passing

## Engine (thread model + discovery)
1. SEO-friendly thread slugs generated on creation.
2. `_slugify()` helper (lowercase, hyphenate, trim to 60).
3. `word_count()` helper.
4. `reading_time_min()` helper (~200 wpm).
5. `public_thread` exposes `slug`.
6. `public_thread` exposes opening-post `word_count`.
7. `public_thread` exposes `reading_time_min`.
8. `public_thread` exposes `net_votes`.
9. `public_thread` exposes `downvotes`.
10. `public_thread` exposes thread `deleted` flag.
11. Per-post `edit_count` in output.
12. Per-post `deleted` flag with `[deleted]` body masking.
13. Per-post `word_count`.
14. `float_accepted` option floats the accepted answer to the top of replies.
15. Downvote support in `vote_thread` (direction < 0).
16. Vote returns `vote_state` (1 / -1 / 0).
17. Net-vote calculation (up − down).
18. Idempotent same-direction voting preserved (no accidental toggle-off).
19. Explicit vote clear via `direction=0`.
20. Edit history: previous bodies stored (last 10).
21. `edit_count` tracking on edits.
22. `post_history()` accessor.
23. Soft-delete threads (`delete_thread`).
24. Soft-delete posts (`delete_post`).
25. `list_threads_sorted` excludes soft-deleted by default.
26. `list_threads_sorted` `ids` filter (drives bookmarks/following views).
27. `list_threads_sorted` `include_deleted` flag for moderation.
28. New `solved` sort.
29. New `unsolved` sort (open questions).
30. New `oldest` sort.
31. Duplicate detection `similar_threads()` (Jaccard on title tokens).
32. Title tokenizer `_title_tokens()`.
33. Per-tag reputation `tag_reputation()`.
34. Backfill `downvoters` on normalize.
35. Backfill `slug` on normalize.
36. Backfill `deleted` + per-post `history`/`edit_count`/`deleted` on normalize.

## Features service — personalization
37. Per-user state store (`forum_user_state.json`).
38. Atomic JSON writes (temp file + `os.replace`).
39. Bookmark toggle.
40. Bookmark count.
41. Follow/subscribe thread toggle.
42. `thread_followers()` lookup.
43. Tag-follow toggle.
44. Mark-thread-read.
45. `is_read()` compares last-seen vs thread `updated_at`.
46. `read_map()` accessor.
47. User preferences store (`set_pref`).
48. Save a search.
49. Delete a saved search.
50. List saved searches (capped at 25).
51. `last_seen` tracking per user.

## Features service — notifications
52. Notifications store (`forum_notifications.json`).
53. `push_notification()` primitive.
54. `notify_thread_followers()` fan-out.
55. `notify_mentions()` fan-out.
56. `list_notifications()` (all or unread-only).
57. `unread_count()`.
58. `mark_notifications_read()` (all or by ids).
59. Notification types: reply / mention / accepted / system.
60. `@mention` extraction (regex, word-boundary safe).
61. `#hashtag` extraction (regex).

## Features service — polls + gamification
62. Poll creation (2–8 options).
63. Poll fetch with per-option percentages.
64. Poll voting (one vote per user, movable).
65. Poll closing time (default 7 days).
66. Poll closed detection.
67. `has_poll()` check.
68. Badge engine with 8 achievements.
69. `author_stats()` aggregation.
70. `compute_badges()` per author.
71. Reputation levels (Newcomer → Legend, 5 tiers).
72. Level progress % toward next tier.

## API endpoints
73. `GET /api/forum/me` — my state + unread count.
74. `POST /api/forum/threads/<id>/bookmark`.
75. `POST /api/forum/threads/<id>/follow`.
76. `POST /api/forum/threads/<id>/read`.
77. `POST /api/forum/tags/<tag>/follow`.
78. `GET /api/forum/bookmarks`.
79. `GET /api/forum/following`.
80. `GET /api/forum/notifications`.
81. `POST /api/forum/notifications/read`.
82. `GET/POST /api/forum/saved-searches`.
83. `DELETE /api/forum/saved-searches/<id>`.
84. `GET/POST /api/forum/threads/<id>/poll`.
85. `POST /api/forum/threads/<id>/poll/vote`.
86. `GET /api/forum/threads/similar`.
87. `GET /api/forum/authors/<name>` — profile (stats, level, badges, per-tag rep, recent).
88. `POST /api/forum/threads/<id>/posts/<pid>/delete`.
89. `GET /api/forum/threads/<id>/posts/<pid>/history`.
90. `GET /api/forum/digest` — personalized activity digest.
91. Thread detail floats the accepted answer.
92. Thread detail returns the poll (if any).
93. Thread detail returns `bookmarked` / `following` for the caller.
94. Thread detail auto-marks the thread read.
95. Create-thread merges inline `#hashtags` into tags.
96. Create-thread notifies `@mentioned` users.
97. Create-thread optional `poll` payload.
98. Reply notifies thread followers.
99. Reply notifies `@mentioned` users.
100. Vote endpoint returns net / downvotes / vote-state.
101. Poll-vote endpoint rate-limited.
102. `me` endpoint refreshes `last_seen`.

## Frontend — notifications
103. 🔔 notifications bell in the header.
104. Unread badge with count (99+ cap).
105. Dropdown notifications panel.
106. Per-type notification icons.
107. Unread items visually highlighted.
108. "Mark all read" action.
109. Click a notification → open thread + mark read.
110. Badge auto-refresh every 60s.
111. Click-outside closes the panel.

## Frontend — thread detail
112. Stacked up/down vote arrows.
113. Live net-vote number.
114. Active-vote visual state (up green / down red).
115. `aria-pressed` on vote arrows.
116. Bookmark (🔖 Save/Saved) button with toast.
117. Follow (🔔 Follow/Following) button with toast.
118. `aria-pressed` on Save/Follow.
119. Reading-time indicator in the meta line.
120. Poll card rendering.
121. Poll option progress bars.
122. Poll voting interaction (re-render on vote).
123. Your-vote highlight.
124. Poll closed / disabled state.

## Frontend — discovery & composer
125. Live duplicate detection hint in the composer.
126. Debounced similar-thread lookup (400ms).
127. Match-percentage on similar threads.
128. Sort chip: 🟡 Unsolved.
129. Sort chip: ✅ Solved.
130. Sort chip: 🕰️ Oldest.
131. 🔖 Saved quick-view button.
132. 🔔 Following quick-view button.
133. `loadMyThreads()` renders bookmarks/following lists.
134. Thread card shows net votes.
135. Negative-score styling on cards.
136. Thread card reading-time badge.
137. Solved-thread left-border accent.
138. Reply composer hints `@mentions` & `#tags`.

## Frontend — styling & a11y (CSS)
139. Notifications panel styling.
140. Unread badge styling.
141. Vote arrow states styling.
142. Poll card styling.
143. Poll bar / label / percentage styling.
144. Similar-threads hint styling.
145. Solved-card accent styling.
146. Header actions flex layout.
147. Light-theme variants for all new components.
148. Panel scroll + elevation shadow.

## Tests & docs
149. 12 new unit tests in `tests/unit/test_forum_v2.py` (slugs, downvotes, edit history, soft-delete, similar, solved sort, bookmarks, follows, notifications, mentions, polls, badges, saved searches, per-tag rep).
150. This document (`docs/FORUM_UPGRADES_V2.md`).
