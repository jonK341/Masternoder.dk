"""
Text-to-Speech Service — generates narration audio for video segments.
Priority: Piper (free, local) or ElevenLabs (if key) -> gTTS (free) -> pyttsx3 (offline).
"""
import os
import tempfile
import time
import subprocess
import wave
from typing import List, Dict, Optional

_DEFAULT_MODEL = "eleven_multilingual_v2"

# Human-leaning defaults — lower stability + mild style avoids flat robot tone.
_HUMAN_VOICE_SETTINGS = {
    "stability": 0.35,
    "similarity_boost": 0.82,
    "style": 0.45,
    "use_speaker_boost": True,
}


def _elevenlabs_key() -> Optional[str]:
    """Return ELEVENLABS_API_KEY if set."""
    return (os.environ.get("ELEVENLABS_API_KEY") or "").strip() or None


def _humanize_script(text: str) -> str:
    """Light copy edits so TTS breathes more like a person."""
    script = (text or "").strip()
    if not script:
        return ""
    # Prefer short spoken clauses over dense machine lines.
    script = script.replace(" · ", ". ")
    script = script.replace(" — ", "... ")
    script = script.replace(" - ", "... ")
    for stiff, warm in (
        ("Scene 1.", "Okay — scene one."),
        ("Scene 2.", "Next..."),
        ("Scene 3.", "Then..."),
        ("Keep watching", "Stay with"),
        ("during the", "as we"),
    ):
        script = script.replace(stiff, warm)
    # Soft pauses help ElevenLabs / gTTS sound less clipped.
    if "..." not in script[:40]:
        script = script[0].upper() + script[1:] if len(script) > 1 else script
    return script[:5000]


def _humanize_audio_file(src_path: str) -> Optional[str]:
    """
    Post-process TTS with gentle tempo + dynamics so it feels less robotic.
    Returns a new path on success, else the original path.
    """
    if not src_path or not os.path.isfile(src_path):
        return src_path
    dest = os.path.join(
        tempfile.gettempdir(),
        "tts_human_%d_%d.mp3" % (int(time.time()), os.getpid()),
    )
    # Slightly slower + gentle dynamics; keeps pitch natural (no chipmunk).
    cmd = [
        "ffmpeg", "-y", "-i", src_path,
        "-af",
        "atempo=0.96,dynaudnorm=f=75:g=15:p=0.95,"
        "highpass=f=80,lowpass=f=12000,volume=1.05",
        "-c:a", "libmp3lame", "-q:a", "3",
        dest,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
        if proc.returncode == 0 and os.path.isfile(dest) and os.path.getsize(dest) > 100:
            return dest
    except Exception:
        pass
    return src_path


def _synthesize_elevenlabs(text: str, voice_id: str) -> Optional[str]:
    """Synthesize with ElevenLabs API using human voice settings."""
    key = _elevenlabs_key()
    spoken = _humanize_script(text)
    if not key or not spoken:
        return None
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=key)
        out_path = os.path.join(tempfile.gettempdir(), f"tts_el_{int(time.time())}_{os.getpid()}.mp3")
        # Prefer convert kwargs that include voice_settings when the SDK supports them.
        try:
            audio = client.text_to_speech.convert(
                voice_id=voice_id,
                text=spoken,
                model_id=_DEFAULT_MODEL,
                voice_settings=_HUMAN_VOICE_SETTINGS,
            )
        except TypeError:
            audio = client.text_to_speech.convert(
                voice_id=voice_id,
                text=spoken,
                model_id=_DEFAULT_MODEL,
            )
        with open(out_path, "wb") as f:
            if hasattr(audio, "__iter__") and not isinstance(audio, (bytes, bytearray)):
                for chunk in audio:
                    if chunk:
                        f.write(chunk)
            else:
                f.write(audio)
        if os.path.isfile(out_path) and os.path.getsize(out_path) > 100:
            return _humanize_audio_file(out_path)
    except Exception:
        pass
    # Direct REST fallback with explicit human voice_settings.
    try:
        import json
        import urllib.request
        payload = json.dumps({
            "text": spoken,
            "model_id": _DEFAULT_MODEL,
            "voice_settings": _HUMAN_VOICE_SETTINGS,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.elevenlabs.io/v1/text-to-speech/%s" % voice_id,
            data=payload,
            headers={
                "xi-api-key": key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        out_path = os.path.join(tempfile.gettempdir(), f"tts_el_rest_{int(time.time())}_{os.getpid()}.mp3")
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read()
        if len(data) > 100:
            with open(out_path, "wb") as handle:
                handle.write(data)
            return _humanize_audio_file(out_path)
    except Exception:
        pass
    return None


def _piper_model_path() -> Optional[str]:
    """Return path to Piper .onnx model if configured and file exists."""
    path = (os.environ.get("PIPER_MODEL_PATH") or "").strip()
    if path and os.path.isfile(path):
        return path
    # Optional default under project
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for name in ("en_US-lessac-medium.onnx", "en_US-lessac-low.onnx"):
        candidate = os.path.join(base, "piper_voices", name)
        if os.path.isfile(candidate):
            return candidate
    return None


def _generate_piper(text: str, dest_path: str, lang: str = "en") -> bool:
    """Generate audio using Piper TTS (free, local). Output WAV; convert to MP3 if needed."""
    model_path = _piper_model_path()
    if not model_path or not text.strip():
        return False
    wav_path = dest_path if dest_path.lower().endswith(".wav") else dest_path.replace(".mp3", ".wav")

    # 1) Try Piper CLI (piper --model ... --output_file ...)
    try:
        proc = subprocess.run(
            ["piper", "--model", model_path, "--output_file", wav_path],
            input=text.strip()[:5000].encode("utf-8"),
            capture_output=True,
            timeout=120,
            cwd=os.path.dirname(model_path) or ".",
        )
        if proc.returncode == 0 and os.path.isfile(wav_path) and os.path.getsize(wav_path) > 100:
            return _piper_wav_to_mp3_if_needed(wav_path, dest_path)
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass

    # 2) Try Piper Python API (PiperVoice)
    try:
        from piper import PiperVoice
        config_path = model_path.replace(".onnx", ".onnx.json")
        kwargs = {"config_path": config_path} if os.path.isfile(config_path) else {}
        voice = PiperVoice.load(model_path, **kwargs)
        with wave.open(wav_path, "wb") as wav_file:
            if hasattr(voice, "synthesize_wav"):
                voice.synthesize_wav(text.strip()[:5000], wav_file)
            else:
                voice.synthesize(text.strip()[:5000], wav_file)
        if os.path.isfile(wav_path) and os.path.getsize(wav_path) > 100:
            return _piper_wav_to_mp3_if_needed(wav_path, dest_path)
    except Exception:
        pass
    return False


def _piper_wav_to_mp3_if_needed(wav_path: str, dest_path: str) -> bool:
    """If dest_path is .mp3, convert wav to mp3 with ffmpeg; then return True if dest exists."""
    if not dest_path.lower().endswith(".mp3"):
        return True
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-acodec", "libmp3lame", "-q:a", "4", dest_path],
            check=True, capture_output=True, timeout=60
        )
        try:
            os.unlink(wav_path)
        except Exception:
            pass
        return os.path.isfile(dest_path) and os.path.getsize(dest_path) > 100
    except Exception:
        return os.path.isfile(wav_path) and os.path.getsize(wav_path) > 100


def is_available() -> bool:
    """Check if any TTS engine is available."""
    if _elevenlabs_key():
        return True
    if _piper_model_path():
        return True
    try:
        from gtts import gTTS
        return True
    except ImportError:
        pass
    try:
        import pyttsx3
        return True
    except ImportError:
        pass
    return False


def _generate_gtts(text: str, dest_path: str, lang: str = "en", slow: bool = False) -> bool:
    """Generate audio using Google TTS (slightly slower = less robotic)."""
    try:
        from gtts import gTTS
        spoken = _humanize_script(text)
        tts = gTTS(text=spoken, lang=lang, slow=True if slow else False)
        # Prefer a mild slow pass for warmth when short enough.
        if not slow and len(spoken) < 600:
            tts = gTTS(text=spoken, lang=lang, slow=True)
        tts.save(dest_path)
        return os.path.isfile(dest_path) and os.path.getsize(dest_path) > 100
    except Exception:
        return False


def _generate_pyttsx3(text: str, dest_path: str) -> bool:
    """Generate audio using pyttsx3 (offline)."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 128)
        engine.setProperty("volume", 0.9)
        try:
            voices = engine.getProperty("voices") or []
            # Prefer a non-default voice when available (often less metallic).
            for voice in voices:
                name = ("%s %s" % (getattr(voice, "name", ""), getattr(voice, "id", ""))).lower()
                if any(token in name for token in ("zira", "samantha", "female", "english")):
                    engine.setProperty("voice", voice.id)
                    break
        except Exception:
            pass
        engine.save_to_file(_humanize_script(text), dest_path)
        engine.runAndWait()
        return os.path.isfile(dest_path) and os.path.getsize(dest_path) > 100
    except Exception:
        return False


def generate_speech(text: str, dest_path: Optional[str] = None, lang: str = "en") -> Optional[str]:
    """
    Generate speech audio from text.
    Returns path to audio file (MP3 or WAV), or None on failure.
    Order: ElevenLabs (human settings) -> Piper -> gTTS -> pyttsx3.
    """
    if not text or not text.strip():
        return None

    if dest_path is None:
        videos_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
        dest_path = os.path.join(videos_dir, f"tts_{int(time.time())}_{os.getpid()}.mp3")

    text = _humanize_script(text)

    # 0) ElevenLabs with human voice settings when keyed
    if _elevenlabs_key():
        # George — warm storyteller (fallback Jessica)
        voice_id = (
            (os.environ.get("ELEVENLABS_VOICE_ID") or "").strip()
            or "JBFqnCBsd6RMkjVDRZzb"
        )
        el_path = _synthesize_elevenlabs(text, voice_id=voice_id)
        if el_path and os.path.isfile(el_path):
            try:
                import shutil
                shutil.copyfile(el_path, dest_path)
                return dest_path
            except Exception:
                return el_path

    # 1) Piper (free, local, no API key)
    if _generate_piper(text, dest_path, lang=lang):
        path = dest_path if os.path.isfile(dest_path) else dest_path.replace(".mp3", ".wav")
        return _humanize_audio_file(path) or path

    # 2) gTTS
    if _generate_gtts(text, dest_path, lang=lang):
        return _humanize_audio_file(dest_path) or dest_path

    # 3) pyttsx3 (offline)
    wav_path = dest_path.replace(".mp3", ".wav")
    if _generate_pyttsx3(text, wav_path):
        return _humanize_audio_file(wav_path) or wav_path

    return None


def generate_narration_for_segments(
    segments: List[Dict],
    pause_sec: float = 0.6,
) -> Optional[str]:
    """
    Generate a single narration audio track from segment descriptions.
    Joins all segment texts with pauses between them.
    Returns path to the combined audio file, or None.
    """
    texts = []
    for seg in segments:
        title = (seg.get("title") or "").strip()
        desc = (seg.get("description") or "").strip()
        combined = f"{title}. {desc}" if title and desc else title or desc
        if combined:
            texts.append(combined[:300])

    if not texts:
        return None

    full_script = ". . . ".join(texts)
    full_script = full_script[:8000]

    return generate_speech(full_script)


def _segment_narration_text(seg: Dict) -> str:
    title = (seg.get("title") or "").strip()
    desc = (seg.get("description") or "").strip()
    if title and desc:
        return f"{title}. {desc}"[:320]
    return (title or desc)[:320]


def generate_timed_narration_for_segments(
    segments: List[Dict],
    total_duration: Optional[float] = None,
    voice_key: str = "rachel",
) -> Optional[str]:
    """
    Per-segment TTS aligned to segment start times (E5).
    Returns path to combined narration audio or None.
    """
    if not segments or not is_available():
        return None

    try:
        from moviepy import AudioFileClip, CompositeAudioClip
    except ImportError:
        try:
            from moviepy.editor import AudioFileClip, CompositeAudioClip
        except ImportError:
            return generate_narration_for_segments(segments)

    pieces = []
    temp_paths: List[str] = []
    cursor = 0.0
    el_key = _elevenlabs_key()

    for seg in segments:
        seg_dur = max(1.2, min(30.0, float(seg.get("duration", 4) or 4)))
        text = _segment_narration_text(seg)
        if not text.strip():
            cursor += seg_dur
            continue

        audio_path = None
        if el_key:
            audio_path = synthesize(text, voice_key=voice_key)
        if not audio_path:
            audio_path = generate_speech(text)
        if not audio_path or not os.path.isfile(audio_path):
            cursor += seg_dur
            continue

        temp_paths.append(audio_path)
        try:
            clip = AudioFileClip(audio_path)
            max_d = max(0.5, seg_dur * 0.92)
            if clip.duration > max_d:
                clip = clip.subclipped(0, max_d)
            clip = clip.with_start(cursor)
            pieces.append(clip)
        except Exception:
            pass
        cursor += seg_dur

    if not pieces:
        for p in temp_paths:
            try:
                os.unlink(p)
            except Exception:
                pass
        return None

    total_d = max(cursor, float(total_duration or 0) or cursor)
    out_path = os.path.join(tempfile.gettempdir(), f"narr_timed_{int(time.time())}_{os.getpid()}.mp3")
    result_path = None
    try:
        comp = CompositeAudioClip(pieces)
        comp = comp.with_duration(total_d)
        comp.write_audiofile(out_path, logger=None)
        for c in pieces:
            try:
                if hasattr(c, "close"):
                    c.close()
            except Exception:
                pass
        result_path = out_path if os.path.isfile(out_path) else None
        if not result_path:
            result_path = generate_narration_for_segments(segments)
        return result_path
    except Exception:
        return generate_narration_for_segments(segments)
    finally:
        for p in temp_paths:
            try:
                if p and p != result_path and os.path.isfile(p):
                    os.unlink(p)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Voice catalogue
# ---------------------------------------------------------------------------

# Current ElevenLabs premade IDs (Nov 2026) — storytelling / conversational first.
VOICES = {
    "george":   {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George",   "style": "warm storyteller"},
    "jessica":  {"id": "cgSgspJ2msm6clMCkdW9", "name": "Jessica",  "style": "playful, bright, warm"},
    "sarah":    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah",    "style": "mature, reassuring"},
    "bella":    {"id": "hpp4J3VqNfWAUOO0d1Us", "name": "Bella",    "style": "professional, warm"},
    "river":    {"id": "SAz9YHcvj6GT2YYXdXww", "name": "River",    "style": "relaxed, calm"},
    "will":     {"id": "bIHbv24MWmeRgasZH58o", "name": "Will",     "style": "relaxed optimist"},
    "alice":    {"id": "Xb7hH8MSUJpSbSDYk0k2", "name": "Alice",    "style": "clear educator"},
    "matilda":  {"id": "XrExE9yKIg1WjnnlVkGX", "name": "Matilda",  "style": "knowledgeable, upbeat"},
    # Legacy aliases map onto warm voices so old callers stay human.
    "rachel":   {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George",   "style": "warm storyteller"},
    "antoni":   {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George",   "style": "warm storyteller"},
    "adam":     {"id": "cjVigY5qzO86Huf0OWal", "name": "Eric",     "style": "smooth, trustworthy"},
    "josh":     {"id": "bIHbv24MWmeRgasZH58o", "name": "Will",     "style": "relaxed optimist"},
    "domi":     {"id": "cgSgspJ2msm6clMCkdW9", "name": "Jessica",  "style": "playful, bright, warm"},
    "sam":      {"id": "cjVigY5qzO86Huf0OWal", "name": "Eric",     "style": "smooth, trustworthy"},
}


def list_voices() -> list:
    """Return all available TTS voices."""
    return [{"voice_key": k, **v} for k, v in VOICES.items()]


def get_status() -> dict:
    """Return TTS provider status for debugger."""
    el_key = _elevenlabs_key()
    # find_spec does not execute the module. Importing pyttsx3 can sit on the
    # audio device and stall Mission Control.
    import importlib.util
    gtts_ok = importlib.util.find_spec("gtts") is not None
    pyttsx3_ok = importlib.util.find_spec("pyttsx3") is not None

    piper_ok = _piper_model_path() is not None
    return {
        "elevenlabs": {
            "configured": bool(el_key),
            "key_hint":   (el_key[:8] + "...") if el_key else None,
            "voices":     len(VOICES),
            "model":      _DEFAULT_MODEL,
            "note":       "Free tier: 10,000 chars/month — elevenlabs.io",
        },
        "piper": {
            "available": piper_ok,
            "model_path": ((p := _piper_model_path()) and (p[:80] + ("..." if len(p) > 80 else ""))) or "",
            "note":      "Free, local, no API key — set PIPER_MODEL_PATH or add piper_voices/*.onnx",
        },
        "gtts": {
            "available": gtts_ok,
            "note":      "Free, no key required",
        },
        "pyttsx3": {
            "available": pyttsx3_ok,
            "note":      "Offline fallback",
        },
        "active_provider": (
            "elevenlabs" if el_key else
            "piper"      if piper_ok else
            "gtts"       if gtts_ok else
            "pyttsx3"    if pyttsx3_ok else "none"
        ),
    }


def synthesize(text: str, voice_key: str = "george", lang: str = "en") -> Optional[str]:
    """
    Synthesize speech with the best available provider.
    voice_key: one of the keys in VOICES dict (defaults to warm storyteller George).
    Returns path to audio file or None.
    """
    key = (voice_key or "george").strip().lower()
    voice_id = VOICES.get(key, VOICES["george"])["id"]
    spoken = _humanize_script(text)

    # 1. Try ElevenLabs with human settings
    path = _synthesize_elevenlabs(spoken, voice_id=voice_id)
    if path:
        return path

    # 2. Try gTTS + humanize filter
    dest = os.path.join(tempfile.gettempdir(), f"tts_{int(time.time())}.mp3")
    if _generate_gtts(spoken, dest, lang=lang):
        return _humanize_audio_file(dest) or dest

    # 3. Try pyttsx3
    wav = dest.replace(".mp3", ".wav")
    if _generate_pyttsx3(spoken, wav):
        return _humanize_audio_file(wav) or wav

    return None
