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


def _elevenlabs_key() -> Optional[str]:
    """Return ELEVENLABS_API_KEY if set."""
    return (os.environ.get("ELEVENLABS_API_KEY") or "").strip() or None


def _synthesize_elevenlabs(text: str, voice_id: str) -> Optional[str]:
    """Synthesize with ElevenLabs API. Returns path to temp file or None."""
    key = _elevenlabs_key()
    if not key or not text.strip():
        return None
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=key)
        out_path = os.path.join(tempfile.gettempdir(), f"tts_el_{int(time.time())}_{os.getpid()}.mp3")
        # API: text_to_speech.convert returns bytes or stream
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text.strip()[:5000],
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
            return out_path
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
    """Generate audio using Google TTS."""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=lang, slow=slow)
        tts.save(dest_path)
        return os.path.isfile(dest_path) and os.path.getsize(dest_path) > 100
    except Exception:
        return False


def _generate_pyttsx3(text: str, dest_path: str) -> bool:
    """Generate audio using pyttsx3 (offline)."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 145)
        engine.setProperty("volume", 0.9)
        engine.save_to_file(text, dest_path)
        engine.runAndWait()
        return os.path.isfile(dest_path) and os.path.getsize(dest_path) > 100
    except Exception:
        return False


def generate_speech(text: str, dest_path: Optional[str] = None, lang: str = "en") -> Optional[str]:
    """
    Generate speech audio from text.
    Returns path to audio file (MP3 or WAV), or None on failure.
    Order: Piper (free, local) -> gTTS -> pyttsx3.
    """
    if not text or not text.strip():
        return None

    if dest_path is None:
        videos_dir = os.environ.get("VIDEOS_DIR", tempfile.gettempdir())
        dest_path = os.path.join(videos_dir, f"tts_{int(time.time())}_{os.getpid()}.mp3")

    text = text.strip()[:5000]

    # 1) Piper (free, local, no API key)
    if _generate_piper(text, dest_path, lang=lang):
        return dest_path if os.path.isfile(dest_path) else dest_path.replace(".mp3", ".wav")

    # 2) gTTS
    if _generate_gtts(text, dest_path, lang=lang):
        return dest_path

    # 3) pyttsx3 (offline)
    wav_path = dest_path.replace(".mp3", ".wav")
    if _generate_pyttsx3(text, wav_path):
        return wav_path

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


# ---------------------------------------------------------------------------
# Voice catalogue
# ---------------------------------------------------------------------------

VOICES = {
    "rachel":   {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel",   "style": "neutral, clear"},
    "domi":     {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi",     "style": "confident, strong"},
    "bella":    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella",    "style": "warm, friendly"},
    "adam":     {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam",     "style": "deep, authoritative"},
    "antoni":   {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni",   "style": "narrator, storytelling"},
    "josh":     {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh",     "style": "young, energetic"},
    "sam":      {"id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam",      "style": "sharp, professional"},
}


def list_voices() -> list:
    """Return all available TTS voices."""
    return [{"voice_key": k, **v} for k, v in VOICES.items()]


def get_status() -> dict:
    """Return TTS provider status for debugger."""
    el_key = _elevenlabs_key()
    gtts_ok = False
    try:
        import gtts as _gtts
        gtts_ok = True
    except ImportError:
        pass
    pyttsx3_ok = False
    try:
        import pyttsx3 as _p
        pyttsx3_ok = True
    except ImportError:
        pass

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


def synthesize(text: str, voice_key: str = "rachel", lang: str = "en") -> Optional[str]:
    """
    Synthesize speech with the best available provider.
    voice_key: one of the keys in VOICES dict.
    Returns path to audio file or None.
    """
    voice_id = VOICES.get(voice_key, VOICES["rachel"])["id"]

    # 1. Try ElevenLabs
    path = _synthesize_elevenlabs(text, voice_id=voice_id)
    if path:
        return path

    # 2. Try gTTS
    dest = os.path.join(tempfile.gettempdir(), f"tts_{int(time.time())}.mp3")
    if _generate_gtts(text, dest, lang=lang):
        return dest

    # 3. Try pyttsx3
    wav = dest.replace(".mp3", ".wav")
    if _generate_pyttsx3(text, wav):
        return wav

    return None
