"""
Sellable film pipeline — story-first GIF-line movies with sound every time.

Components
  1. StoryArchitect   — coherent beat script locked to the user prompt (more story)
  2. HeroFrameLab     — Pollinations free models (flux / z-image-turbo / gptimage)
                        Credit-blocked Stability / OpenAI / Gemini imagen are skipped
  3. MotionStudio     — story_gif_line (4–5s story GIFs mixed in one horizontal strip)
                        + premium_local fallback. Blocked paid I2V is deactivated.
  4. SoundtrackDesk   — narration + music bed, ALWAYS muxed into the MP4
  5. DeliveryMaster   — concat, 1280x720 grade, Xvid package
  6. QualityGate      — sellable when story motion + audio + size pass
"""
from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
import uuid
from typing import Any, Callable, Dict, List, Optional

from backend.services import ai_provider_gate as gate

ProgressCb = Optional[Callable[[int, str], None]]

# Each story panel lives 4–5 seconds (user product requirement).
_BEAT_SEC_MIN = 4.0
_BEAT_SEC_MAX = 5.0


def _progress(cb: ProgressCb, pct: int, message: str) -> None:
    if cb:
        try:
            cb(int(pct), str(message))
        except Exception:
            pass


def _scene_core(prompt: str) -> str:
    core = (prompt or "").split("[face reference")[0].strip()
    core = core.split("\n\nStoryboard direction:")[0].strip()
    return core[:220] or "cinematic real-world scene"


def _bible(prompt: str) -> str:
    core = _scene_core(prompt)
    return (
        "Photoreal cinematic plate of: %s. Same people, wardrobe,location and lighting "
        "in every shot. Natural skin, real clothing, shallow depth of field, 16:9, "
        "no text, no watermark, no cartoon, no psychedelic color FX."
    ) % core


def _beat_budget(duration_sec: int) -> int:
    """One beat ≈ 4–5s GIF panel. Keep enough panels to fill the run."""
    seconds = max(4, min(120, int(duration_sec or 8)))
    return max(1, min(8, int(round(seconds / 4.5))))


def design_sellable_story(
    prompt: str,
    duration_sec: int,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """StoryArchitect — invent a tight story beat script every run (4–5s panels)."""
    run_id = run_id or ("sell_%s" % uuid.uuid4().hex[:12])
    want = _beat_budget(duration_sec)
    seconds = max(4, min(120, int(duration_sec or 8)))
    core = _scene_core(prompt)
    salt = int(hashlib.sha1(("%s|%s" % (run_id, core)).encode("utf-8")).hexdigest()[:8], 16)

    # Story-heavy arcs — cause → action → consequence, not random FX moods.
    arcs = (
        ("hook", "rising_action", "turn", "payoff", "settle"),
        ("arrival", "discovery", "conflict", "choice", "resolve"),
        ("setup", "push", "complication", "climax", "close"),
        ("establish", "motive", "obstacle", "breakthrough", "land"),
    )
    arc = arcs[salt % len(arcs)]
    moods = ("urgent", "hopeful", "tense", "warm", "gritty", "serene")
    styles = (
        "documentary realism", "wet chrome cinematic", "golden-hour realism",
        "night neon realism", "soft daylight realism", "harbour steel realism",
    )
    mood = moods[salt % len(moods)]
    style = styles[(salt // 5) % len(styles)]
    shot_cycle = ("establishing", "character", "action", "detail", "reaction", "closing")
    verbs = (
        "steps into", "notices", "pushes through", "holds onto", "turns toward",
        "reveals", "faces", "claims", "returns to", "settles into",
    )

    beats: List[Dict[str, Any]] = []
    remaining = float(seconds)
    for index in range(want):
        left = want - index
        # Prefer 4–5s; last beat absorbs remainder within the same band.
        if left == 1:
            beat_sec = max(_BEAT_SEC_MIN, min(_BEAT_SEC_MAX + 1.5, remaining))
        else:
            target = remaining / float(left)
            beat_sec = max(_BEAT_SEC_MIN, min(_BEAT_SEC_MAX, round(target, 2)))
        remaining = max(0.0, round(remaining - beat_sec, 2))
        role = arc[min(index, len(arc) - 1)]
        shot = shot_cycle[index % len(shot_cycle)]
        verb = verbs[(salt + index) % len(verbs)]
        title = ("%s · %s" % (role.replace("_", " ").title(), shot))[:48]
        description = (
            "Beat %s (%s): someone %s the story of %s — %s shot, %s, mood %s. "
            "Keep continuity with the same characters and place; show what happens next."
            % (index + 1, role, verb, core[:90], shot, style, mood)
        )[:320]
        image_prompt = (
            "%s Continuity bible locked. Story beat '%s' (%s): %s. "
            "Clear narrative moment, readable faces, real environment, no abstract FX."
            % (_bible(prompt), role, shot, description)
        )[:480]
        narration = (
            "%s. %s"
            % (title, description[:160])
        )[:220]
        beats.append({
            "index": index,
            "title": title,
            "role": role,
            "shot_type": shot,
            "description": description,
            "image_prompt": image_prompt,
            "narration": narration,
            "duration_sec": beat_sec,
            "seed": (salt * 17 + index * 91 + secrets.randbelow(4000)) % 999999,
        })

    story = (
        "A %s %s story about %s: we open on %s, press through %s, and land on %s."
        % (
            mood,
            style,
            core,
            beats[0]["title"] if beats else "the scene",
            beats[len(beats) // 2]["title"] if len(beats) > 1 else "the turn",
            beats[-1]["title"] if beats else "the close",
        )
    )[:420]
    return {
        "success": True,
        "run_id": run_id,
        "provider": "sellable_architect",
        "title": ("%s · %s" % (style, mood))[:80],
        "style": style,
        "mood": mood,
        "story": story,
        "narration": [b["narration"] for b in beats],
        "beats": beats,
        "bible": _bible(prompt),
        "panel_sec": [_BEAT_SEC_MIN, _BEAT_SEC_MAX],
    }


def _make_hero_still(prompt: str, dest_dir: str, seed: int) -> Dict[str, Any]:
    """HeroFrameLab — Pollinations free models only (blocked paid image AIs skipped)."""
    os.makedirs(dest_dir, exist_ok=True)
    gate.ensure_defaults()

    # Deactivated: Stability / OpenAI image / Gemini imagen (credit locks).
    for blocked in ("stability", "openai_image", "google_imagen"):
        if not gate.is_blocked(blocked):
            gate.block(blocked, "credit_or_quota_probe")

    try:
        from backend.services import free_image_service as free_img
        models = list(gate.POLLINATIONS_IMAGE_MODELS)
        model = models[int(seed) % len(models)]
        out = free_img.generate_image(
            prompt=prompt[:420],
            width=1280,
            height=720,
            dest_dir=dest_dir,
            seed=int(seed) % 999999,
            model=model,
        )
        if out.get("success") and out.get("local_path") and os.path.isfile(out["local_path"]):
            out["source"] = out.get("source") or ("pollinations_%s" % model)
            return out
    except Exception as exc:
        return {"success": False, "error": "hero still failed: %s" % exc}

    # Last resort: canvas helper (also Pollinations flux).
    try:
        from backend.services import film_canvas_service as canvas
        path = canvas._try_free_beat_image(prompt, dest_dir, seed=seed, timeout=18)
        if path and os.path.isfile(path):
            return {"success": True, "local_path": path, "source": "pollinations_flux"}
    except Exception:
        pass
    return {"success": False, "error": "hero still failed"}


def _render_premium_local_clip(
    image_paths: List[str],
    dest_path: str,
    duration_sec: float,
) -> Dict[str, Any]:
    """Credit-free motion: smooth cinematic crossfade + gentle zoom across hero stills."""
    paths = [p for p in image_paths if p and os.path.isfile(p)]
    if not paths:
        return {"success": False, "error": "no premium local stills"}
    seconds = max(_BEAT_SEC_MIN, min(20.0, float(duration_sec or 4.5)))
    if len(paths) == 1:
        frames = max(48, int(round(seconds * 24)))
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", ("%.3f" % seconds), "-i", paths[0],
            "-vf",
            "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
            "zoompan=z='min(1.0+0.0015*on,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            ":d=%d:s=1280x720:fps=24,eq=contrast=1.05:saturation=1.04,format=yuv420p" % frames,
            "-t", ("%.3f" % seconds),
            "-c:v", "libx264", "-crf", "19", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            dest_path,
        ]
    else:
        n = min(4, len(paths))
        paths = paths[:n]
        fade = min(0.55, max(0.25, seconds / (n * 3.5)))
        hold = max(fade + 0.8, (seconds + fade * (n - 1)) / float(n))
        cmd = ["ffmpeg", "-y"]
        for path in paths:
            cmd.extend(["-loop", "1", "-t", ("%.3f" % hold), "-i", path])
        parts = []
        for i in range(n):
            parts.append(
                "[%d:v]scale=1280:720:force_original_aspect_ratio=increase,"
                "crop=1280:720,setsar=1,fps=24[s%d]" % (i, i)
            )
        current = "[s0]"
        offset = hold - fade
        for i in range(1, n):
            label = "[x%d]" % i
            parts.append(
                "%s[s%d]xfade=transition=fade:duration=%.3f:offset=%.3f%s"
                % (current, i, fade, max(0.05, offset), label)
            )
            current = label
            offset += hold - fade
        parts.append(
            "%seq=contrast=1.05:saturation=1.04,format=yuv420p[vout]" % current
        )
        cmd.extend([
            "-filter_complex", ";".join(parts),
            "-map", "[vout]",
            "-t", ("%.3f" % seconds),
            "-r", "24",
            "-c:v", "libx264", "-crf", "19", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            dest_path,
        ])
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=max(60, int(seconds) + 45), check=False,
        )
    except Exception as exc:
        return {"success": False, "error": "premium local ffmpeg failed: %s" % exc}
    if proc.returncode != 0 or not os.path.isfile(dest_path):
        return {"success": False, "error": (proc.stderr or "premium local encode failed")[:280]}
    return {
        "success": True,
        "local_path": dest_path,
        "motion_backend": "premium_local",
        "fps": 24,
        "duration_sec": seconds,
    }


def _render_story_gif_line(
    *,
    still_paths: List[str],
    dest_path: str,
    duration_sec: float,
    motion: str = "zoom_in",
) -> Dict[str, Any]:
    """
    MotionStudio primary — mix 3 story-locked stills as moving GIFs in one line.
    Each panel animates for 4–5 seconds and stays on the same story.
    """
    from backend.services import film_canvas_service as canvas

    paths = [p for p in still_paths if p and os.path.isfile(p)]
    if not paths:
        return {"success": False, "error": "no story stills for gif line"}
    seconds = max(_BEAT_SEC_MIN, min(_BEAT_SEC_MAX + 0.5, float(duration_sec or 4.5)))
    out = canvas._ffmpeg_gif_strip_clip(
        paths,
        dest_path,
        duration=seconds,
        motion=motion or "zoom_in",
    )
    if out.get("success") and out.get("local_path") and os.path.isfile(out["local_path"]):
        out = dict(out)
        out["motion_backend"] = "story_gif_line"
        out["mode"] = "story_gif_line"
        out["duration_sec"] = seconds
        return out
    return {"success": False, "error": out.get("error") or "story gif line failed"}


def _render_motion_clip(
    *,
    prompt: str,
    duration_sec: float,
    dest_dir: str,
    start_image: Optional[str] = None,
    timeout: int = 120,
    alt_stills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    MotionStudio — story GIF line first; skip deactivated paid I2V wallets.
    Paid backends stay in code but are gated off until credits return.
    """
    errors: List[str] = []
    gate.ensure_defaults()
    stills: List[str] = []
    if start_image:
        stills.append(start_image)
    for path in alt_stills or []:
        if path and path not in stills:
            stills.append(path)

    clip_sec = max(_BEAT_SEC_MIN, min(_BEAT_SEC_MAX, float(duration_sec or 4.5)))

    # 1) Primary product path: story GIFs in one line (4–5s).
    if stills:
        dest = os.path.join(dest_dir, "gif_line_%s.mp4" % uuid.uuid4().hex[:8])
        line = _render_story_gif_line(
            still_paths=stills[:3],
            dest_path=dest,
            duration_sec=clip_sec,
            motion="zoom_in",
        )
        if line.get("success"):
            return line
        errors.append("story_gif_line: %s" % (line.get("error") or "fail"))

    # 2) Optional paid I2V — only if not deactivated (normally all blocked).
    paid_backends = (
        ("runway", "backend.services.runwayml_service"),
        ("pika", "backend.services.pika_service"),
        ("modelslab", "backend.services.modelslab_video_service"),
        ("replicate", "backend.services.replicate_video_service"),
    )
    for backend, module_path in paid_backends:
        if gate.is_blocked(backend):
            errors.append("%s: deactivated (%s)" % (backend, (gate.status()["blocked"].get(backend) or "blocked")[:60]))
            continue
        try:
            import importlib
            mod = importlib.import_module(module_path)
            if not getattr(mod, "is_available", lambda: False)():
                errors.append("%s: not configured" % backend)
                continue
            kwargs: Dict[str, Any] = {
                "prompt": prompt[:500],
                "dest_dir": dest_dir,
                "timeout": min(timeout, 120),
            }
            if backend == "runway":
                kwargs["duration"] = int(round(clip_sec))
                kwargs["start_image_path"] = start_image
                kwargs["prompt"] = prompt[:900]
            elif backend == "pika":
                kwargs["duration"] = min(int(round(clip_sec)), 5)
            elif backend == "modelslab":
                kwargs = {"prompt": prompt[:500], "timeout": min(timeout, 120)}
            out = mod.generate_clip(**kwargs)
            if out.get("success") and out.get("local_path") and os.path.isfile(out["local_path"]):
                out = dict(out)
                out["motion_backend"] = backend
                return out
            err = out.get("error") or "fail"
            errors.append("%s: %s" % (backend, err))
            gate.note_error(backend, err)
        except Exception as exc:
            errors.append("%s: %s" % (backend, exc))
            gate.note_error(backend, str(exc))

    # fal — only if not skipped/blocked
    if not gate.is_blocked("fal"):
        try:
            from backend.services import film_canvas_service as canvas
            if hasattr(canvas, "_generate_fal_queue_clip") and not canvas._fal_is_skipped():
                out = canvas._generate_fal_queue_clip(
                    prompt[:500], dest_dir=dest_dir, timeout=min(timeout, 120),
                )
                if out.get("success") and out.get("local_path") and os.path.isfile(out["local_path"]):
                    out = dict(out)
                    out["motion_backend"] = "fal"
                    return out
                err = out.get("error") or "fail"
                errors.append("fal: %s" % err)
                gate.note_error("fal", err)
        except Exception as exc:
            errors.append("fal: %s" % exc)
            gate.note_error("fal", str(exc))
    else:
        errors.append("fal: deactivated")

    # 3) Premium local cine from hero stills
    if stills:
        dest = os.path.join(dest_dir, "premium_local_%s.mp4" % uuid.uuid4().hex[:8])
        local = _render_premium_local_clip(stills, dest, float(duration_sec or clip_sec))
        if local.get("success"):
            local["prior_errors"] = errors[:6]
            return local
        errors.append("premium_local: %s" % (local.get("error") or "fail"))

    return {"success": False, "error": " | ".join(errors)[:400] or "no motion backend"}


def _build_music_bed(dest_path: str, duration_sec: float) -> Optional[str]:
    """Soft pink-noise + low sine bed — guarantees an audio track every time."""
    seconds = max(2.0, float(duration_sec or 8.0))
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=98:sample_rate=44100:duration=%.3f" % seconds,
        "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.025:sample_rate=44100:duration=%.3f" % seconds,
        "-filter_complex",
        "[0:a]volume=0.045[a0];[1:a]volume=0.035[a1];"
        "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2,aformat=fltp:44100:stereo[aout]",
        "-map", "[aout]",
        "-c:a", "aac",
        "-b:a", "128k",
        dest_path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40, check=False)
        if proc.returncode == 0 and os.path.isfile(dest_path) and os.path.getsize(dest_path) > 500:
            return dest_path
    except Exception:
        return None
    return None


def _synthesize_narration(story: Dict[str, Any], dest_dir: str) -> Optional[str]:
    """SoundtrackDesk voice — humanized ElevenLabs (George) first."""
    lines = []
    if story.get("story"):
        lines.append(str(story["story"])[:280])
    for beat in story.get("beats") or []:
        line = beat.get("narration") or beat.get("description")
        if line:
            lines.append(str(line)[:180])
    script = " ".join(lines).strip()[:1200]
    if not script:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    try:
        from backend.services import tts_service as tts
        # Warm storyteller — less robotic than legacy Rachel defaults.
        path = tts.synthesize(script, voice_key="george")
        if path and os.path.isfile(path):
            return path
        path = tts.generate_speech(
            script,
            dest_path=os.path.join(dest_dir, "narr_%s.mp3" % uuid.uuid4().hex[:8]),
        )
        if path and os.path.isfile(path):
            return path
    except Exception:
        return None
    return None


def _shop_sfx_paths() -> List[str]:
    """Resolve shop WAV sound effects shipped with the app."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sound_dir = os.path.join(root, "static", "shop", "sounds")
    names = (
        "shop-1.wav", "shop-4.wav", "shop-10.wav", "shop-15.wav", "shop-20.wav",
        "shop-25.wav", "shop-26.wav", "shop-27.wav", "shop-32.wav", "shop-33.wav",
        "shop-34.wav", "shop-35.wav", "shop-36.wav",
    )
    paths = [os.path.join(sound_dir, name) for name in names]
    return [p for p in paths if os.path.isfile(p)]


def _build_sfx_bed(
    dest_path: str,
    duration_sec: float,
    sfx_count: int,
) -> Optional[str]:
    """
    Build one SFX bed with exactly `sfx_count` hits (same count as live FX).
    Uses shop WAVs when present; fills remaining slots with short procedural hits.
    """
    seconds = max(2.0, float(duration_sec or 8.0))
    want = max(1, int(sfx_count or 1))
    shop = _shop_sfx_paths()
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)

    # Build a filter that places `want` hits evenly across the timeline.
    cmd: List[str] = ["ffmpeg", "-y"]
    # Silent base so amix always has a full-length canvas.
    cmd.extend([
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo:d=%.3f" % seconds,
    ])
    parts: List[str] = ["[0:a]volume=0.0[base]"]
    labels = ["[base]"]
    for index in range(want):
        delay_ms = int(round((seconds * 1000.0) * ((index + 0.5) / float(want))))
        delay_ms = max(40, min(int(seconds * 1000) - 200, delay_ms))
        if shop:
            src = shop[index % len(shop)]
            cmd.extend(["-i", src])
            inp = index + 1
            parts.append(
                "[%d:a]aformat=fltp:44100:stereo,volume=0.55,"
                "adelay=%d|%d,apad=whole_dur=%.3f[s%d]"
                % (inp, delay_ms, delay_ms, seconds, index)
            )
        else:
            # Procedural click/whoosh when shop bank is missing.
            freq = 220 + (index % 6) * 55
            cmd.extend([
                "-f", "lavfi",
                "-i",
                "sine=frequency=%d:sample_rate=44100:duration=0.18" % freq,
            ])
            inp = index + 1
            parts.append(
                "[%d:a]aformat=fltp:44100:stereo,volume=0.35,"
                "adelay=%d|%d,apad=whole_dur=%.3f[s%d]"
                % (inp, delay_ms, delay_ms, seconds, index)
            )
        labels.append("[s%d]" % index)

    parts.append(
        "%samix=inputs=%d:duration=first:dropout_transition=0,"
        "aformat=fltp:44100:stereo,volume=1.0[aout]"
        % ("".join(labels), len(labels))
    )
    cmd.extend([
        "-filter_complex", ";".join(parts),
        "-map", "[aout]",
        "-t", ("%.3f" % seconds),
        "-c:a", "aac",
        "-b:a", "160k",
        dest_path,
    ])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
        if proc.returncode == 0 and os.path.isfile(dest_path) and os.path.getsize(dest_path) > 500:
            return dest_path
    except Exception:
        return None
    return None


def _mux_soundtrack(
    video_path: str,
    dest_path: str,
    narration_path: Optional[str],
    bed_path: Optional[str],
    sfx_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Mux narration + music + FX-matched SFX under picture."""
    if not video_path or not os.path.isfile(video_path):
        return {"success": False, "error": "video missing for mux"}
    inputs = ["ffmpeg", "-y", "-i", video_path]
    filter_parts: List[str] = []
    audio_labels: List[str] = []
    idx = 1
    if narration_path and os.path.isfile(narration_path):
        inputs.extend(["-i", narration_path])
        filter_parts.append("[%d:a]volume=0.92,aformat=fltp:44100:stereo[narr]" % idx)
        audio_labels.append("[narr]")
        idx += 1
    if bed_path and os.path.isfile(bed_path):
        inputs.extend(["-i", bed_path])
        filter_parts.append("[%d:a]volume=0.18,aformat=fltp:44100:stereo[bed]" % idx)
        audio_labels.append("[bed]")
        idx += 1
    if sfx_path and os.path.isfile(sfx_path):
        inputs.extend(["-i", sfx_path])
        filter_parts.append("[%d:a]volume=0.70,aformat=fltp:44100:stereo[sfx]" % idx)
        audio_labels.append("[sfx]")
        idx += 1
    if not audio_labels:
        return {"success": True, "local_path": video_path, "has_audio": False}

    if len(audio_labels) == 1:
        filter_complex = ";".join(filter_parts + [
            "%svolume=1.0[aout]" % audio_labels[0]
        ])
    else:
        filter_complex = ";".join(filter_parts + [
            "%samix=inputs=%d:duration=longest:dropout_transition=2[aout]"
            % ("".join(audio_labels), len(audio_labels))
        ])

    cmd = inputs + [
        "-filter_complex", filter_complex,
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        dest_path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    except Exception as exc:
        return {"success": False, "error": "mux failed: %s" % exc, "has_audio": False}
    if proc.returncode != 0 or not os.path.isfile(dest_path):
        return {
            "success": False,
            "error": (proc.stderr or proc.stdout or "mux encode failed")[:300],
            "has_audio": False,
        }
    return {"success": True, "local_path": dest_path, "has_audio": True}


def _normalize_delivery(video_path: str, dest_path: str) -> Dict[str, Any]:
    """DeliveryMaster grade pass — consistent 1280x720 H.264."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
               "pad=1280:720:(ow-iw)/2:(oh-ih)/2,eq=contrast=1.04:saturation=1.04,fps=24",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        dest_path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    if proc.returncode != 0 or not os.path.isfile(dest_path):
        return {"success": False, "error": (proc.stderr or "normalize failed")[:300]}
    return {"success": True, "local_path": dest_path}


def evaluate_quality_gate(
    *,
    local_path: str,
    has_audio: bool,
    motion_backends: List[str],
    duration_sec: float,
    has_narration: bool = False,
    sfx_count: int = 0,
    fx_count: int = 0,
    hero_frames: int = 0,
    beats: int = 0,
) -> Dict[str, Any]:
    """QualityGate — sellable + 0–100 quality_pct (gallery auto-store when > 90)."""
    size = os.path.getsize(local_path) if local_path and os.path.isfile(local_path) else 0
    # Draft-only leftovers — NOT the story GIF line product path.
    rejected = {"draft", "acting_morph", "free_still"}
    accepted_local = {"story_gif_line", "gif_storyboard", "gif_strip", "premium_local"}
    real_motion = [b for b in motion_backends if b and b not in rejected]
    paid = [b for b in real_motion if b not in accepted_local]
    local_ok = [b for b in real_motion if b in accepted_local]
    sellable = bool(
        local_path
        and os.path.isfile(local_path)
        and has_audio
        and len(real_motion) >= 1
        and size >= 180_000
        and float(duration_sec or 0) >= 2.0
    )
    reasons = []
    if not has_audio:
        reasons.append("missing_audio")
    if not real_motion:
        reasons.append("no_motion_backend")
    if size < 180_000:
        reasons.append("file_too_small")
    quality = "draft"
    if sellable and paid:
        quality = "sellable"
    elif sellable and local_ok:
        quality = "sellable_local"
    elif sellable:
        quality = "sellable_local"

    # Percent score used for gallery auto-store (kval > 90).
    score = 0
    if has_audio:
        score += 22
    if has_narration:
        score += 10
    if real_motion:
        score += 22
    if paid:
        score += 18
    elif local_ok:
        score += 16
    if size >= 500_000:
        score += 12
    elif size >= 300_000:
        score += 9
    elif size >= 180_000:
        score += 5
    if float(duration_sec or 0) >= 8:
        score += 8
    elif float(duration_sec or 0) >= 4:
        score += 5
    if hero_frames >= 3:
        score += 4
    if beats >= 2:
        score += 3
    # Matching SFX to FX count is part of product quality.
    if fx_count > 0 and sfx_count >= fx_count:
        score += 8
    elif sfx_count > 0:
        score += 3
    quality_pct = int(max(0, min(100, score)))

    return {
        "sellable": sellable,
        "quality": quality,
        "quality_pct": quality_pct,
        "quality_score": round(quality_pct / 100.0, 4),
        "reasons": reasons,
        "bytes": size,
        "motion_backends": real_motion,
        "paid_motion": paid,
        "local_motion": local_ok,
        "sfx_count": int(sfx_count or 0),
        "fx_count": int(fx_count or 0),
    }


def _auto_store_gallery(
    *,
    local_path: str,
    prompt: str,
    story: Dict[str, Any],
    gate_result: Dict[str, Any],
    duration_sec: float,
    motion_backends: List[str],
) -> Dict[str, Any]:
    """
    Automatically store important videos in the gallery when quality_pct > 90.
    Copies into VIDEOS_DIR with status sidecar so /vidgenerator/gallery lists them.
    """
    quality_pct = int(gate_result.get("quality_pct") or 0)
    if quality_pct <= 90:
        return {
            "stored": False,
            "reason": "quality_pct_below_threshold",
            "quality_pct": quality_pct,
        }
    if not local_path or not os.path.isfile(local_path):
        return {"stored": False, "reason": "missing_video", "quality_pct": quality_pct}

    try:
        from backend.services.video_generator_service import VIDEOS_DIR as _VIDEOS_DIR
        videos_dir = _VIDEOS_DIR or os.environ.get("VIDEOS_DIR")
    except Exception:
        videos_dir = os.environ.get("VIDEOS_DIR")
    if not videos_dir:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        videos_dir = os.path.join(root, "vidgenerator", "videos")
    os.makedirs(videos_dir, exist_ok=True)

    doc_id = "film_%s" % uuid.uuid4().hex[:12]
    dest_mp4 = os.path.join(videos_dir, "%s.mp4" % doc_id)
    try:
        import shutil
        shutil.copy2(local_path, dest_mp4)
    except Exception as exc:
        return {"stored": False, "reason": "copy_failed: %s" % exc, "quality_pct": quality_pct}

    title = (
        str(story.get("title") or "").strip()
        or ("Film · %s" % (_scene_core(prompt)[:48]))
    )[:120]
    description = (
        str(story.get("story") or "").strip()
        or str(prompt or "").strip()
    )[:500]
    meta = {
        "id": doc_id,
        "title": title,
        "description": description,
        "prompt": (prompt or "")[:500],
        "status": "completed",
        "duration": int(round(float(duration_sec or 0))),
        "quality_level": "high",
        "quality_score": gate_result.get("quality_score"),
        "quality_pct": quality_pct,
        "category_name": "Film",
        "pipeline": "sellable_v1",
        "motion_backends": list(motion_backends or []),
        "sellable": bool(gate_result.get("sellable")),
        "quality": gate_result.get("quality"),
        "auto_gallery": True,
        "gallery_threshold": 90,
    }
    status_path = os.path.join(videos_dir, "%s.status.json" % doc_id)
    try:
        import json
        with open(status_path, "w", encoding="utf-8") as handle:
            json.dump(meta, handle, indent=2)
    except Exception:
        pass

    db_ok = False
    try:
        from backend.services.gallery_db_service import upsert_gallery_item
        db_ok = bool(upsert_gallery_item(
            item_id=doc_id,
            title=title,
            file_path=dest_mp4,
            status="completed",
            duration=int(round(float(duration_sec or 0))),
            category_name="Film",
            description=description,
            prompt=(prompt or "")[:500],
            quality_level="high",
            quality_score=float(gate_result.get("quality_score") or (quality_pct / 100.0)),
        ))
    except Exception:
        db_ok = False

    try:
        from backend.routes.gallery_routes import invalidate_gallery_cache
        invalidate_gallery_cache()
    except Exception:
        pass

    return {
        "stored": True,
        "gallery_id": doc_id,
        "gallery_path": dest_mp4,
        "status_path": status_path,
        "quality_pct": quality_pct,
        "db_upsert": db_ok,
        "title": title,
    }


def compose_sellable_movie(
    prompt: str,
    *,
    dest_dir: Optional[str] = None,
    duration_sec: int = 8,
    face_path: Optional[str] = None,
    timeout: int = 240,
    on_progress: ProgressCb = None,
    allow_draft_fallback: bool = True,
) -> Dict[str, Any]:
    """
    Run the full sellable pipeline.
    Returns local_path + sellable flag + component metadata.
    """
    brief = (prompt or "").strip()
    if not brief:
        return {"success": False, "error": "prompt is required", "sellable": False}
    try:
        duration_sec = max(4, min(120, int(round(float(duration_sec)))))
    except (TypeError, ValueError):
        duration_sec = 8
    if dest_dir is None:
        dest_dir = os.environ.get("VIDEOS_DIR") or os.getcwd()
    os.makedirs(dest_dir, exist_ok=True)
    work = os.path.join(dest_dir, "sellable_%s" % uuid.uuid4().hex[:10])
    os.makedirs(work, exist_ok=True)
    attempts: List[str] = []
    gate.ensure_defaults()

    _progress(on_progress, 8, "Sellable pipeline — designing story…")
    story = design_sellable_story(brief, duration_sec)
    beats = list(story.get("beats") or [])
    if not beats:
        return {"success": False, "error": "story architect produced no beats", "sellable": False}

    _progress(on_progress, 18, "Sellable pipeline — hero frames (Pollinations)…")
    hero_paths: List[str] = []
    for beat in beats:
        beat_stills: List[str] = []
        # Three story plates per beat → left / mid / right GIF panels.
        for plate in range(3):
            still = _make_hero_still(
                ("%s. Story panel %s of 3, same locked scene and characters, photoreal, "
                 "clear narrative moment, no abstract color FX."
                 % (beat.get("image_prompt") or brief, plate + 1))[:480],
                work,
                int(beat.get("seed") or 1000) + plate * 17,
            )
            if not (still.get("success") and still.get("local_path")):
                if plate == 0:
                    attempts.append("still@%s: %s" % (beat.get("index"), still.get("error") or "fail"))
                continue
            path = str(still["local_path"])
            if face_path and os.path.isfile(face_path) and plate == 0:
                try:
                    from backend.services.film_canvas_service import _composite_face_onto_still
                    composited = os.path.join(work, "face_%s.jpg" % beat.get("index"))
                    path = _composite_face_onto_still(path, face_path, composited) or path
                except Exception:
                    pass
            beat_stills.append(path)
            if path not in hero_paths:
                hero_paths.append(path)
        if beat_stills:
            beat["still_path"] = beat_stills[0]
            beat["still_paths"] = beat_stills
            beat["still_source"] = "hero_lab_pollinations"

    _progress(on_progress, 35, "Sellable pipeline — story GIF line (4–5s)…")
    clip_paths: List[str] = []
    motion_backends: List[str] = []
    per_timeout = max(45, min(120, int(timeout // max(1, len(beats)))))
    for beat in beats:
        _progress(
            on_progress,
            35 + int(40 * (int(beat.get("index") or 0) / max(1, len(beats)))),
            "Story GIF line · beat %s/%s…" % ((beat.get("index") or 0) + 1, len(beats)),
        )
        panel_stills = list(beat.get("still_paths") or [])
        if len(panel_stills) < 3:
            # Borrow continuity stills from the shared hero set so the strip stays full.
            for path in hero_paths:
                if path not in panel_stills:
                    panel_stills.append(path)
                if len(panel_stills) >= 3:
                    break
        motion = _render_motion_clip(
            prompt=str(beat.get("image_prompt") or brief),
            duration_sec=float(beat.get("duration_sec") or 4.5),
            dest_dir=work,
            start_image=beat.get("still_path"),
            timeout=per_timeout,
            alt_stills=panel_stills[:3] or hero_paths[:3],
        )
        if motion.get("success") and motion.get("local_path"):
            clip_paths.append(str(motion["local_path"]))
            motion_backends.append(str(motion.get("motion_backend") or "story_gif_line"))
            beat["motion_backend"] = motion.get("motion_backend")
            beat["clip_path"] = motion.get("local_path")
            if motion.get("prior_errors"):
                attempts.extend(list(motion["prior_errors"])[:2])
        else:
            attempts.append(
                "motion@%s: %s" % (beat.get("index"), motion.get("error") or "fail")
            )

    used_draft = False
    if not clip_paths and allow_draft_fallback:
        _progress(on_progress, 55, "Motion backends unavailable — draft fallback…")
        try:
            from backend.services.film_canvas_service import _generate_free_still_movie
            draft = _generate_free_still_movie(
                brief,
                dest_dir=work,
                duration=float(duration_sec),
                face_path=face_path if face_path and os.path.isfile(face_path) else None,
                ai_pipeline={
                    "success": True,
                    "run_id": story.get("run_id"),
                    "style": story.get("style"),
                    "mood": story.get("mood"),
                    "story": story.get("story"),
                    "narration": story.get("narration"),
                    "beats": beats,
                    "provider": "sellable_draft_bridge",
                },
            )
            if draft.get("success") and draft.get("local_path"):
                clip_paths = [str(draft["local_path"])]
                # Prefer story_gif_line label when draft used gif_storyboard mode.
                mode = str(draft.get("mode") or "draft")
                motion_backends = ["story_gif_line" if "gif" in mode else "draft"]
                used_draft = True
                attempts.append("draft_fallback_used")
        except Exception as exc:
            attempts.append("draft_fallback: %s" % exc)

    if not clip_paths:
        return {
            "success": False,
            "error": "sellable pipeline produced no clips: " + " | ".join(attempts)[:400],
            "sellable": False,
            "attempts": attempts,
            "story": story.get("story"),
            "pipeline": "sellable_v1",
            "provider_gate": gate.status(),
        }

    _progress(on_progress, 78, "Delivery master — stitching…")
    from backend.services.film_canvas_service import _ffmpeg_concat_movies, _ffmpeg_encode_xvid

    stitched = os.path.join(work, "stitched_%s.mp4" % uuid.uuid4().hex[:8])
    if len(clip_paths) == 1:
        merged_path = clip_paths[0]
    else:
        merged = _ffmpeg_concat_movies(clip_paths, stitched)
        if not (merged.get("success") and merged.get("local_path")):
            return {
                "success": False,
                "error": merged.get("error") or "concat failed",
                "sellable": False,
                "attempts": attempts,
                "pipeline": "sellable_v1",
            }
        merged_path = str(merged["local_path"])

    _progress(on_progress, 84, "Soundtrack desk — human voice + FX-matched SFX…")
    # FX pack drives both visual accents and the matching SFX count.
    try:
        from backend.services.film_canvas_service import _build_fx_pack
        fx_pack = _build_fx_pack(
            str(story.get("run_id") or uuid.uuid4().hex[:10]),
            style=str(story.get("style") or ""),
            mood=str(story.get("mood") or ""),
        )
    except Exception:
        fx_pack = {
            "effects": ["mist_01"] * 12,
            "live_count": 12,
            "background": "fog",
            "sound": "harbour",
            "intensity": 0.28,
            "story_first": True,
        }
    fx_count = int(fx_pack.get("live_count") or len(fx_pack.get("effects") or []) or 12)
    fx_pack["sfx_count"] = fx_count
    fx_pack["sfx_bank"] = "shop"

    narr = _synthesize_narration(story, work)
    bed = _build_music_bed(os.path.join(work, "bed_%s.aac" % uuid.uuid4().hex[:6]), float(duration_sec))
    if not bed:
        bed = _build_music_bed(os.path.join(work, "bed_retry_%s.aac" % uuid.uuid4().hex[:6]), float(duration_sec))
    sfx = _build_sfx_bed(
        os.path.join(work, "sfx_%s.aac" % uuid.uuid4().hex[:6]),
        float(duration_sec),
        fx_count,
    )
    sfx_count = fx_count if sfx else 0
    mixed = os.path.join(work, "mixed_%s.mp4" % uuid.uuid4().hex[:8])
    mux = _mux_soundtrack(merged_path, mixed, narr, bed, sfx_path=sfx)
    has_audio = bool(mux.get("has_audio"))
    pictured = str(mux.get("local_path") or merged_path)
    if not has_audio and bed and os.path.isfile(bed):
        retry_path = os.path.join(work, "mixed_retry_%s.mp4" % uuid.uuid4().hex[:8])
        mux2 = _mux_soundtrack(merged_path, retry_path, None, bed, sfx_path=sfx)
        if mux2.get("has_audio") and mux2.get("local_path"):
            has_audio = True
            pictured = str(mux2["local_path"])
            attempts.append("audio_retry_bed_sfx")

    _progress(on_progress, 93, "Delivery master — grade + package…")
    final_path = os.path.join(dest_dir, "sellable_%s.mp4" % uuid.uuid4().hex[:8])
    graded = _normalize_delivery(pictured, final_path)
    if graded.get("success") and graded.get("local_path"):
        final_path = str(graded["local_path"])
    else:
        final_path = pictured
        attempts.append("grade: %s" % (graded.get("error") or "skipped"))

    xvid_path = None
    xvid = _ffmpeg_encode_xvid(final_path)
    if xvid.get("success"):
        xvid_path = xvid.get("local_path")

    gate_result = evaluate_quality_gate(
        local_path=final_path,
        has_audio=has_audio,
        motion_backends=motion_backends,
        duration_sec=float(duration_sec),
        has_narration=bool(narr and os.path.isfile(narr)),
        sfx_count=sfx_count,
        fx_count=fx_count,
        hero_frames=len(hero_paths),
        beats=len(beats),
    )

    _progress(on_progress, 97, "Gallery check — auto-store if quality > 90%…")
    gallery = _auto_store_gallery(
        local_path=final_path,
        prompt=brief,
        story=story,
        gate_result=gate_result,
        duration_sec=float(duration_sec),
        motion_backends=motion_backends,
    )
    if gallery.get("stored"):
        attempts.append("gallery_auto_store:%s" % gallery.get("gallery_id"))

    _progress(
        on_progress,
        100,
        (
            "Sellable pipeline complete"
            if gate_result["sellable"]
            else "Draft pipeline complete"
        )
        + (
            (" · gallery %s%%" % gate_result.get("quality_pct"))
            if gallery.get("stored")
            else (" · kval %s%%" % gate_result.get("quality_pct"))
        ),
    )
    return {
        "success": True,
        "local_path": final_path,
        "xvid_path": xvid_path,
        "canvas": "sellable_v1",
        "renderer": "sellable_v1",
        "pipeline": "sellable_v1",
        "mode": (
            "sellable_i2v" if gate_result.get("quality") == "sellable"
            else "sellable_local" if gate_result.get("quality") == "sellable_local"
            else "sellable_draft"
        ),
        "sellable": gate_result["sellable"],
        "quality": gate_result["quality"],
        "quality_pct": gate_result.get("quality_pct"),
        "quality_score": gate_result.get("quality_score"),
        "quality_gate": gate_result,
        "has_audio": has_audio,
        "has_narration": bool(narr),
        "sfx_count": sfx_count,
        "fx_count": fx_count,
        "fx_pack": fx_pack,
        "gallery": gallery,
        "gallery_id": gallery.get("gallery_id") if gallery.get("stored") else None,
        "fps": 24,
        "duration_sec": duration_sec,
        "beats": len(beats),
        "beat_plan": beats,
        "story": story.get("story"),
        "narration": story.get("narration"),
        "pipeline_run_id": story.get("run_id"),
        "pipeline_style": story.get("style"),
        "pipeline_mood": story.get("mood"),
        "pipeline_title": story.get("title"),
        "motion_backends": motion_backends,
        "hero_frames": len(hero_paths),
        "used_draft_fallback": used_draft,
        "attempts": attempts[:12],
        "prompt_used": brief[:500],
        "has_face": bool(face_path and os.path.isfile(face_path)),
        "provider_gate": gate.status(),
        "image_providers": list(gate.ACTIVE_IMAGE_PROVIDERS),
        "motion_providers": list(gate.ACTIVE_MOTION_PROVIDERS),
        "voice_profile": "george",
    }
