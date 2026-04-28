# Hard Test Generator – 25 Steps to Working Vids & Clips

Use `scripts/hard_test_generator_urls.py`. **Default is the web server URL** (same GET/POST tests, no local server needed).

## Steps 1–5: Environment & API health
1. **Web server** – Script defaults to `https://masternoder.dk` (or set `BASE_URL`). Use `--local` for `http://127.0.0.1:5000`.
2. **Verify BASE_URL** – Run `python scripts/hard_test_generator_urls.py --quick` to hit GET endpoints (no create).
3. **Check /api/generator/test** – Returns `database_available`, `video_pipeline_available`.
4. **Check /api/generator/jobs** – Returns `success` and `jobs` list.
5. **Check /api/gallery/list** – Returns `videos` (and count).

## Steps 6–10: Documentary creation pipeline
6. **Reset for test** – GET `/api/generator/reset-for-test?confirm=test` clears in-memory jobs.
7. **POST create** – POST `/api/generator/create` with title, description, user_id, duration (e.g. 60).
8. **Poll progress** – GET `/api/documentary/progress/<doc_id>` until status is `completed` or `failed`.
9. **GET video** – GET `/api/documentary/video/<doc_id>` returns 200 and video bytes or JSON with video_url.
10. **Verify file** – Video file exists under `vidgenerator/videos/<doc_id>.mp4` (or `output/videos`).

## Steps 11–15: Gallery & browser
11. **Gallery list** – GET `/api/gallery/list` returns `videos` array (includes new documentary).
12. **Gallery video** – GET `/api/gallery/video/<doc_id>` returns single video details.
13. **Browser: generator** – Open `{BASE_URL}/vidgenerator/generator/` and create a video.
14. **Browser: gallery** – Open `{BASE_URL}/vidgenerator/gallery/` and confirm new video appears.
15. **Browser: play** – Click play on the new video and confirm it plays.

## Steps 16–20: Clips & robustness
16. **POST ai-clips** – POST `/api/generator/ai-clips` with prompt; returns job_id and 202.
17. **Poll clips status** – GET `/api/generator/ai-clips/<job_id>` returns status and optional clips list.
18. **History** – GET `/api/generator/history?user_id=hardtest` shows recent jobs.
19. **Statistics** – GET `/api/generator/statistics?user_id=hardtest` shows counts.
20. **Performance** – GET `/api/generator/performance?user_id=hardtest` shows success rate.

## Steps 21–25: End-to-end and repeat
21. **Full script** – Run `python scripts/hard_test_generator_urls.py` (no --quick) for full create→poll→video.
22. **Gallery after create** – Script verifies gallery list contains the new doc_id.
23. **Smooth run** – Ensure no 500s; video generation uses MoviePy or sample fallback.
24. **Make vid for gallery** – One full run creates one documentary and it appears in gallery.
25. **Test interface again** – Re-open gallery and generator in browser; create one more video and confirm both show.

## One-command flow (web server)
```bash
# Run full test against web server (GET + POST create, poll, video, gallery, clips)
python scripts/hard_test_generator_urls.py --poll 90
```

## Local server (optional)
```bash
# Terminal 1: start server
python run.py

# Terminal 2: run same test against localhost
python scripts/hard_test_generator_urls.py --local --poll 90
```

Or use `scripts/run_generation_and_test.py --no-start` to run only the test (server already running elsewhere).
