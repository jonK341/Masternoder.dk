# Video Storage Strategy — 25GB Server Rethink

**Problem:** Server has only 25GB disk; videos fill it quickly. Need alternatives.

---

## 1. What We're Storing

| Item | Size | Purpose |
|------|------|---------|
| MP4 files | ~2–10 MB each | Final video output |
| `.status.json` | ~1 KB | Job status, metadata |
| `.pipeline.json` | ~5–20 KB | Segments, config |
| Temp files (TTS, images) | ~50–200 MB during encoding | Deleted after encode |

**JSON cannot store video data** — video is binary. JSON only stores metadata (URLs, paths, titles). We keep JSON for metadata; the question is where to put the actual MP4 files.

---

## 2. Options Overview

| Strategy | Cost | Complexity | Best for |
|----------|------|------------|----------|
| **Cloud object storage** | Free (10GB) | Low | Primary recommendation |
| **Generate → upload → delete** | Free | Low | Keeps server clean |
| **Temp-only + cloud** | Free | Medium | Minimal server footprint |
| **Increase disk** | ~$5–10/mo | None | Quick fix |
| **Browser IndexedDB** | Free | High | Client-side only; not for server |

---

## 3. Free Cloud Storage Options

### 3.1 Cloudflare R2 (Recommended)

- **Free tier:** 10 GB storage, 10M reads/month, **no egress fees** when using Cloudflare
- **API:** S3-compatible (boto3, `aiobotocore`)
- **Why:** No egress = no surprise bills when videos are streamed. Very popular for video hosting.

```
https://developers.cloudflare.com/r2/
```

### 3.2 Backblaze B2

- **Free tier:** 10 GB storage, 1 GB egress/day free
- **API:** S3-compatible
- **Cost:** ~$0.01/GB after free tier

### 3.3 Supabase Storage

- **Free tier:** 1 GB storage, 2 GB bandwidth
- **API:** REST/JS SDK
- **Note:** Smaller free tier; good for low volume

### 3.4 Cloudinary

- **Free tier:** 25 GB storage, 25 GB bandwidth/month
- **API:** REST/JS SDK
- **Note:** Video-focused; transcoding included

### 3.5 Bunny.net Storage

- **Not free:** ~$0.01/GB storage + bandwidth
- **API:** REST/JS SDK
- **Note:** Very cheap for video hosting

---

## 4. Recommended Architecture: Generate → Upload → Delete

```
[Server] Generate MP4 → Upload to R2/B2 → Delete local → Store URL in metadata
```

**Flow:**
1. Video generation writes to `VIDEOS_DIR/{doc_id}.mp4` (as now)
2. On success: upload to cloud, get public URL
3. Delete local MP4 (or move to temp, delete after upload)
4. Store `video_url` (cloud URL) in `.status.json` and job
5. Documentary/video route: if file exists locally → serve; else redirect to `video_url`

**Benefits:**
- Server only stores temp during encoding (~100–200 MB peak)
- No long-term video storage on 25GB disk
- Gallery and player use cloud URLs when available

---

## 5. Implementation Sketch

### 5.1 Storage abstraction

```python
# backend/services/video_storage_service.py
def get_video_url(doc_id: str) -> Optional[str]:
    """Return URL to serve video: local path or cloud URL."""
    # 1. Check local file
    local = _local_path(doc_id)
    if local and os.path.isfile(local) and os.path.getsize(local) >= 1024:
        return None  # caller will send_file
    # 2. Check cloud URL in status.json
    sidecar = _read_status(doc_id)
    return sidecar.get("video_url")  # e.g. https://pub-xxx.r2.dev/videos/{doc_id}.mp4

def upload_and_delete(doc_id: str, local_path: str) -> Optional[str]:
    """Upload to cloud, delete local, return public URL."""
    # Use boto3 for R2 (S3-compatible)
    # Upload local_path
    # Delete local_path
    # Return public URL
```

### 5.2 Documentary video route change

```python
# Instead of only send_file(local_path):
url = get_video_url(doc_id)
if url:
    return redirect(url)  # 302 to cloud
path = _get_video_file_path(doc_id)
if path and os.path.isfile(path):
    return send_file(path, ...)
```

### 5.3 Post-generation hook

After `generate_rich_video_sync` or `_generate_video_sync` succeeds:

```python
cloud_url = upload_to_cloud(doc_id, out_path)
if cloud_url:
    _write_status_sidecar(..., video_url=cloud_url)
    os.remove(out_path)  # or keep for N days, then delete
```

---

## 6. Local Temp + Top 10 (Implemented)

- Videos are stored temporarily on the server. User gets a **download link** when generation completes.
- **5 minute window**: After 5 min, a video is eligible for cleanup unless it is in the **top 10 by file size** (best quality).
- **Gallery** shows only the top 10 best-quality videos.
- **Profile page** has a "Download din clip (5 min)" section with a countdown and backup download link.
- **Cleanup** runs when gallery list or recent-temp API is called; no cron required. Optional one-time cleanup:
  ```bash
  cd /var/www/html/vidgenerator && python scripts/cleanup_videos_keep_top10.py
  ```
- Optional **cron** to run cleanup periodically (e.g. every 5 min):
  ```bash
  */5 * * * * cd /var/www/html/vidgenerator && python -c "from backend.services.video_retention_service import run_cleanup; print(run_cleanup())"
  ```

## 7. Quick Wins (No Code Change)

1. **Cron job** (legacy) — Delete videos older than 7 days:
   ```bash
   0 3 * * * find /var/www/html/vidgenerator/videos -name "*.mp4" -mtime +7 -delete
   ```

2. **Increase disk** — If your host allows, upgrade to 50GB for ~$5/mo.

3. **Lower video quality** — Reduce bitrate in `write_videofile` (e.g. `bitrate="500k"`) to shrink file size.

---

## 8. Summary

| Recommendation | Action |
|----------------|--------|
| **Short term** | Add cron to delete old videos; optionally lower bitrate |
| **Medium term** | Implement Cloudflare R2 (or B2) upload; generate → upload → delete |
| **Metadata** | Keep JSON in `VIDEOS_DIR` (tiny). Add `video_url` when cloud is used |
| **Local storage** | Use only for temp during encoding; never persist long-term |

**JSON** = metadata only; **cloud** = video storage; **local** = temp workspace.
