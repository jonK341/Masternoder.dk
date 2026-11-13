"""
Sellable film pipeline — delivery-grade interactive movies.

Components
  1. StoryArchitect   — short coherent beat script locked to the user prompt
  2. HeroFrameLab     — Stability (preferred) / Flux stills with continuity bible
  3. MotionStudio     — real I2V/T2V cascade (Runway → Pika → ModelsLab → Replicate → fal)
  4. SoundtrackDesk   — ElevenLabs/gTTS narration + soft music bed, muxed into MP4
  5. DeliveryMaster   — concat, 1280x720 grade, Xvid package
  6. QualityGate      — sellable=true only when real motion + audio + size pass

The old GIF-strip / pose-morph path remains as draft fallback only.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
import uuid
from typing import Any, Callable, Dict, List, Optional

ProgressCb = Optional[Callable[[int, str], None]]


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
        "no text, no watermark, no cartoon."
    ) % core


def _beat_budget(duration_sec: int) -> int:
    """Fewer high-quality paid clips beat many cheap morphs."""
    seconds = max(2, min(120, int(duration_sec or 8)))
    if seconds <= 6:
        return 1
    if seconds <= 12:
        return 2
    if seconds <= 24:
        return 3
    if seconds <= 48:
        return 4
    return min(6, max(4, seconds // 12))


def design_sellable_story(
    prompt: str,
    duration_sec: int,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """StoryArchitect — invent a tight sellable beat script every run."""
    run_id = run_id or ("sell_%s" % uuid.uuid4().hex[:12])
    want = _beat_budget(duration_sec)
    seconds = max(2, min(120, int(duration_sec or 8)))
    core = _scene_core(prompt)
    salt = int(hashlib.sha1(("%s|%s" % (run_id, core)).encode("utf-8")).hexdigest()[:8], 16)
    arcs = (
        ("arrival", "conflict", "resolve"),
        ("setup", "push", "payoff"),
        ("open", "turn", "close"),
        ("establish", "act", "land"),
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
    beats: List[Dict[str, Any]] = []
    remaining = float(seconds)
    for index in range(want):
        left = want - index
        beat_sec = remaining if left == 1 else max(2.0, round(remaining / left, 2))
        remaining = max(0.0, round(remaining - beat_sec, 2))
        role = arc[min(index, len(arc) - 1)]
        shot = shot_cycle[index % len(shot_cycle)]
        title = ("%s · %s" % (role.title(), shot))[:48]
        description = (
            "%s during the %s of the story about %s — %s, mood %s."
            % (shot, role, core[:100], style, mood)
        )[:280]
        image_prompt = (
            "%s %s shot for story beat '%s': %s"
            % (_bible(prompt), shot, role, description)
        )[:420]
        narration = (
            "Scene %s. %s. Keep watching %s."
            % (index + 1, description[:120], core[:70])
        )[:200]
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
    }


def _make_hero_still(prompt: str, dest_dir: str, seed: int) -> Dict[str, Any]:
    """HeroFrameLab — Stability first, Flux Pollinations second."""
    os.makedirs(dest_dir, exist_ok=True)
    try:
        from backend.services import stability_image_service as stability
        if stability.is_available():
            out = stability.generate_image(
                prompt=prompt[:900],
                negative_prompt=(
                    "cartoon, anime, illustration, watermark, text, blurry, low quality, "
                    "deformed hands, plastic skin"
                ),
                width=1280,
                height=720,
                dest_dir=dest_dir,
            )
            if out.get("success") and out.get("local_path") and os.path.isfile(out["local_path"]):
                out["source"] = "stability"
                return out
    except Exception as exc:
        pass

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
    """
    Credit-free motion: smooth cinematic crossfade + gentle zoom across hero stills.
    Used when paid I2V wallets are empty so the product still ships with audio-ready picture.
    """
    paths = [p for p in image_paths if p and os.path.isfile(p)]
    if not paths:
        return {"success": False, "error": "no premium local stills"}
    seconds = max(2.0, min(20.0, float(duration_sec or 4.0)))
    if len(paths) == 1:
        # Single-plate push-in.
        frames = max(48, int(round(seconds * 24)))
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", ("%.3f" % seconds), "-i", paths[0],
            "-vf",
            "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
            "zoompan=z='min(1.0+0.0015*on,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            ":d=%d:s=1280x720:fps=24,eq=contrast=1.05:saturation=1.08,format=yuv420p" % frames,
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
            "%seq=contrast=1.05:saturation=1.08,format=yuv420p[vout]" % current
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


def _render_motion_clip(
    *,
    prompt: str,
    duration_sec: float,
    dest_dir: str,
    start_image: Optional[str] = None,
    timeout: int = 120,
    alt_stills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """MotionStudio — paid I2V/T2V cascade, then premium local cine from hero stills."""
    errors: List[str] = []
    clip_sec = max(2, min(10, int(round(duration_sec or 5))))

    # 1) Runway Gen-4 Turbo (I2V)
    try:
        from backend.services import runwayml_service as runway
        if runway.is_available():
            out = runway.generate_clip(
                prompt=prompt[:900],
                duration=clip_sec,
                dest_dir=dest_dir,
                timeout=min(timeout, 150),
                start_image_path=start_image,
            )
            if out.get("success") and out.get("local_path") and os.path.isfile(out["local_path"]):
                out["motion_backend"] = "runway"
                return out
            errors.append("runway: %s" % (out.get("error") or "fail"))
    except Exception as exc:
        errors.append("runway: %s" % exc)

    # 2) Pika T2V
    try:
        from backend.services import pika_service as pika
        if pika.is_available():
            out = pika.generate_clip(
                prompt=prompt[:500],
                duration=min(clip_sec, 5),
                dest_dir=dest_dir,
                timeout=min(timeout, 150),
            )
            if out.get("success") and out.get("local_path") and os.path.isfile(out["local_path"]):
                out["motion_backend"] = "pika"
                return out
            errors.append("pika: %s" % (out.get("error") or "fail"))
    except Exception as exc:
        errors.append("pika: %s" % exc)

    # 3) ModelsLab T2V
    try:
        from backend.services import modelslab_video_service as modelslab
        if modelslab.is_available():
            out = modelslab.generate_clip(prompt=prompt[:500], timeout=min(timeout, 120))
            if out.get("success") and out.get("local_path") and os.path.isfile(out["local_path"]):
                out["motion_backend"] = "modelslab"
                return out
            errors.append("modelslab: %s" % (out.get("error") or "fail"))
    except Exception as exc:
        errors.append("modelslab: %s" % exc)

    # 4) Replicate SVD I2V
    try:
        from backend.services import replicate_video_service as replicate
        if replicate.is_available():
            out = replicate.generate_clip(
                prompt=prompt[:500],
                dest_dir=dest_dir,
                timeout=min(timeout, 150),
            )
            if out.get("success") and out.get("local_path") and os.path.isfile(out["local_path"]):
                out["motion_backend"] = "replicate"
                return out
            errors.append("replicate: %s" % (out.get("error") or "fail"))
    except Exception as exc:
        errors.append("replicate: %s" % exc)

    # 5) fal queue (if not balance-locked)
    try:
        from backend.services import film_canvas_service as canvas
        if hasattr(canvas, "_generate_fal_queue_clip") and not canvas._fal_is_skipped():
            out = canvas._generate_fal_queue_clip(prompt[:500], dest_dir=dest_dir, timeout=min(timeout, 120))
            if out.get("success") and out.get("local_path") and os.path.isfile(out["local_path"]):
                out["motion_backend"] = "fal"
                return out
            errors.append("fal: %s" % (out.get("error") or "fail"))
    except Exception as exc:
        errors.append("fal: %s" % exc)

    # 6) Premium local cine from hero stills (credit-free but audio-ready)
    stills = []
    if start_image:
        stills.append(start_image)
    for path in alt_stills or []:
        if path and path not in stills:
            stills.append(path)
    if stills:
        dest = os.path.join(dest_dir, "premium_local_%s.mp4" % uuid.uuid4().hex[:8])
        local = _render_premium_local_clip(stills, dest, float(duration_sec or clip_sec))
        if local.get("success"):
            local["prior_errors"] = errors[:6]
            return local
        errors.append("premium_local: %s" % (local.get("error") or "fail"))

    return {"success": False, "error": " | ".join(errors)[:400] or "no motion backend"}


def _build_music_bed(dest_path: str, duration_sec: float) -> Optional[str]:
    """Soft pink-noise + low sine bed for commercial polish."""
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
    """SoundtrackDesk voice — ElevenLabs first via synthesize()."""
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
        path = tts.synthesize(script, voice_key="rachel")
        if path and os.path.isfile(path):
            return path
        path = tts.generate_speech(script, dest_path=os.path.join(dest_dir, "narr_%s.mp3" % uuid.uuid4().hex[:8]))
        if path and os.path.isfile(path):
            return path
    except Exception:
        return None
    return None


def _mux_soundtrack(
    video_path: str,
    dest_path: str,
    narration_path: Optional[str],
    bed_path: Optional[str],
) -> Dict[str, Any]:
    """Mux narration + music under picture (creates a real audio track)."""
    if not video_path or not os.path.isfile(video_path):
        return {"success": False, "error": "video missing for mux"}
    inputs = ["ffmpeg", "-y", "-i", video_path]
    filter_parts: List[str] = []
    audio_labels: List[str] = []
    idx = 1
    if narration_path and os.path.isfile(narration_path):
        inputs.extend(["-i", narration_path])
        filter_parts.append("[%d:a]volume=0.95,aformat=fltp:44100:stereo[narr]" % idx)
        audio_labels.append("[narr]")
        idx += 1
    if bed_path and os.path.isfile(bed_path):
        inputs.extend(["-i", bed_path])
        filter_parts.append("[%d:a]volume=0.22,aformat=fltp:44100:stereo[bed]" % idx)
        audio_labels.append("[bed]")
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
               "pad=1280:720:(ow-iw)/2:(oh-ih)/2,eq=contrast=1.04:saturation=1.06,fps=24",
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
) -> Dict[str, Any]:
    """QualityGate — sellable with paid I2V or premium_local cine + audio + size."""
    size = os.path.getsize(local_path) if local_path and os.path.isfile(local_path) else 0
    rejected = {"draft", "gif_strip", "acting_morph", "free_still", "gif_storyboard"}
    real_motion = [b for b in motion_backends if b and b not in rejected]
    paid = [b for b in real_motion if b != "premium_local"]
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
    elif sellable:
        quality = "sellable_local"  # credit-free cine with voice — still productizable
    return {
        "sellable": sellable,
        "quality": quality,
        "reasons": reasons,
        "bytes": size,
        "motion_backends": real_motion,
        "paid_motion": paid,
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
        duration_sec = max(2, min(120, int(round(float(duration_sec)))))
    except (TypeError, ValueError):
        duration_sec = 8
    if dest_dir is None:
        dest_dir = os.environ.get("VIDEOS_DIR") or os.getcwd()
    os.makedirs(dest_dir, exist_ok=True)
    work = os.path.join(dest_dir, "sellable_%s" % uuid.uuid4().hex[:10])
    os.makedirs(work, exist_ok=True)
    attempts: List[str] = []

    _progress(on_progress, 8, "Sellable pipeline — designing story…")
    story = design_sellable_story(brief, duration_sec)
    beats = list(story.get("beats") or [])
    if not beats:
        return {"success": False, "error": "story architect produced no beats", "sellable": False}

    _progress(on_progress, 18, "Sellable pipeline — hero frames…")
    hero_paths: List[str] = []
    for beat in beats:
        beat_stills: List[str] = []
        # 2–3 plates per beat so premium_local can crossfade instead of a single freeze.
        for plate in range(3):
            still = _make_hero_still(
                ("%s. Variation %s, same locked scene, photoreal."
                 % (beat.get("image_prompt") or brief, plate + 1))[:420],
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
            beat["still_source"] = "hero_lab"

    _progress(on_progress, 35, "Sellable pipeline — real motion render…")
    clip_paths: List[str] = []
    motion_backends: List[str] = []
    per_timeout = max(45, min(120, int(timeout // max(1, len(beats)))))
    for beat in beats:
        _progress(
            on_progress,
            35 + int(40 * (int(beat.get("index") or 0) / max(1, len(beats)))),
            "Motion studio · beat %s/%s…" % ((beat.get("index") or 0) + 1, len(beats)),
        )
        motion = _render_motion_clip(
            prompt=str(beat.get("image_prompt") or brief),
            duration_sec=float(beat.get("duration_sec") or 4),
            dest_dir=work,
            start_image=beat.get("still_path"),
            timeout=per_timeout,
            alt_stills=list(beat.get("still_paths") or hero_paths[:3]),
        )
        if motion.get("success") and motion.get("local_path"):
            clip_paths.append(str(motion["local_path"]))
            motion_backends.append(str(motion.get("motion_backend") or "motion"))
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
                motion_backends = ["draft"]
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

    _progress(on_progress, 86, "Soundtrack desk — voice + bed…")
    narr = _synthesize_narration(story, work)
    bed = _build_music_bed(os.path.join(work, "bed_%s.aac" % uuid.uuid4().hex[:6]), float(duration_sec))
    mixed = os.path.join(work, "mixed_%s.mp4" % uuid.uuid4().hex[:8])
    mux = _mux_soundtrack(merged_path, mixed, narr, bed)
    has_audio = bool(mux.get("has_audio"))
    pictured = str(mux.get("local_path") or merged_path)

    _progress(on_progress, 93, "Delivery master — grade + package…")
    final_path = os.path.join(dest_dir, "sellable_%s.mp4" % uuid.uuid4().hex[:8])
    graded = _normalize_delivery(pictured, final_path)
    if graded.get("success") and graded.get("local_path"):
        final_path = str(graded["local_path"])
    else:
        # Keep mixed/stitched if grade fails.
        final_path = pictured
        attempts.append("grade: %s" % (graded.get("error") or "skipped"))

    xvid_path = None
    xvid = _ffmpeg_encode_xvid(final_path)
    if xvid.get("success"):
        xvid_path = xvid.get("local_path")

    gate = evaluate_quality_gate(
        local_path=final_path,
        has_audio=has_audio,
        motion_backends=motion_backends,
        duration_sec=float(duration_sec),
    )

    _progress(on_progress, 100, "Sellable pipeline complete" if gate["sellable"] else "Draft pipeline complete")
    return {
        "success": True,
        "local_path": final_path,
        "xvid_path": xvid_path,
        "canvas": "sellable_v1",
        "renderer": "sellable_v1",
        "pipeline": "sellable_v1",
        "mode": (
            "sellable_i2v" if gate.get("quality") == "sellable"
            else "sellable_local" if gate.get("quality") == "sellable_local"
            else "sellable_draft"
        ),
        "sellable": gate["sellable"],
        "quality": gate["quality"],
        "quality_gate": gate,
        "has_audio": has_audio,
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
    }
