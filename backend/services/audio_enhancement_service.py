"""
Optional audio enhancement for the encoder pipeline.
- DeepFilterNet: AI noise reduction (optional dependency).
- FFmpeg loudnorm/dynaudnorm: normalization and light mastering (no extra deps).

Enable with env: AUDIO_ENHANCE=1 or AUDIO_ENHANCE_NOISE=1 / AUDIO_ENHANCE_LOUDNORM=1.
"""
import os
import subprocess
import tempfile
from typing import Optional


def _env_enabled(name: str, default: bool = False) -> bool:
    v = (os.environ.get(name) or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


def is_noise_reduction_available() -> bool:
    """True if DeepFilterNet can be used (package installed)."""
    if not _env_enabled("AUDIO_ENHANCE_NOISE", _env_enabled("AUDIO_ENHANCE", False)):
        return False
    try:
        import deepfilternet  # noqa: F401
        return True
    except ImportError:
        return False


def is_loudnorm_available() -> bool:
    """True if FFmpeg loudnorm is desired and ffmpeg is on PATH."""
    if not _env_enabled("AUDIO_ENHANCE_LOUDNORM", _env_enabled("AUDIO_ENHANCE", False)):
        return False
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _enhance_noise_deepfilternet(input_path: str, output_path: str) -> bool:
    """Run DeepFilterNet on audio. Expects 48 kHz WAV; converts with ffmpeg if needed."""
    wav_48k = input_path
    if not input_path.lower().endswith(".wav"):
        wav_48k = tempfile.mktemp(suffix=".wav")
        try:
            r = subprocess.run(
                ["ffmpeg", "-y", "-i", input_path, "-ar", "48000", "-ac", "1", wav_48k],
                capture_output=True, timeout=30
            )
            if r.returncode != 0 or not os.path.isfile(wav_48k):
                return False
        except Exception:
            return False

    try:
        import soundfile as sf
        from deepfilternet import DeepFilterNet
        data, rate = sf.read(wav_48k)
        if rate != 48000:
            if wav_48k != input_path:
                try:
                    os.unlink(wav_48k)
                except Exception:
                    pass
            return False
        # API: model is callable with (audio_array, sample_rate) -> enhanced_array
        df = DeepFilterNet()
        out = df(data, rate)
        sf.write(output_path, out, 48000)
        if wav_48k != input_path:
            try:
                os.unlink(wav_48k)
            except Exception:
                pass
        return os.path.isfile(output_path) and os.path.getsize(output_path) > 100
    except Exception:
        if wav_48k != input_path and os.path.isfile(wav_48k):
            try:
                os.unlink(wav_48k)
            except Exception:
                pass
        return False


def _enhance_loudnorm_ffmpeg(input_path: str, output_path: str) -> bool:
    """Apply FFmpeg loudnorm (EBU R128) for consistent level. Preserves format."""
    try:
        # Two-pass loudnorm for proper normalization (optional; one-pass is faster)
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "44100",
            output_path,
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        if r.returncode != 0 or not os.path.isfile(output_path) or os.path.getsize(output_path) < 100:
            # Fallback: simple dynaudnorm
            cmd = ["ffmpeg", "-y", "-i", input_path, "-af", "dynaudnorm", output_path]
            r = subprocess.run(cmd, capture_output=True, timeout=60)
        return r.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 100
    except Exception:
        return False


def enhance_audio(
    input_path: str,
    apply_noise: Optional[bool] = None,
    apply_loudnorm: Optional[bool] = None,
) -> Optional[str]:
    """
    Optionally enhance an audio file (narration or mix).
    Returns path to enhanced file (may be a new temp file), or original path if disabled/failed.
    Caller should use the returned path and delete any temp file when done.
    """
    if not input_path or not os.path.isfile(input_path) or os.path.getsize(input_path) < 100:
        return None

    do_noise = apply_noise if apply_noise is not None else is_noise_reduction_available()
    do_loudnorm = apply_loudnorm if apply_loudnorm is not None else is_loudnorm_available()
    if not do_noise and not do_loudnorm:
        return input_path

    current = input_path
    try:
        if do_noise and is_noise_reduction_available():
            fd, out_noise = tempfile.mkstemp(suffix=".nr.wav")
            os.close(fd)
            try:
                if _enhance_noise_deepfilternet(current, out_noise):
                    if current != input_path:
                        try:
                            os.unlink(current)
                        except Exception:
                            pass
                    current = out_noise
            except Exception:
                if current != input_path and os.path.isfile(current):
                    try:
                        os.unlink(current)
                    except Exception:
                        pass
                current = input_path

        if do_loudnorm and is_loudnorm_available():
            ext = os.path.splitext(input_path)[1] or ".wav"
            fd, out_ln = tempfile.mkstemp(suffix=".ln" + ext)
            os.close(fd)
            try:
                if _enhance_loudnorm_ffmpeg(current, out_ln):
                    if current != input_path:
                        try:
                            os.unlink(current)
                        except Exception:
                            pass
                    return out_ln
            except Exception:
                pass
            if current != input_path:
                try:
                    os.unlink(out_ln)
                except Exception:
                    pass
        return current
    except Exception:
        return input_path


def get_status() -> dict:
    """Status for debugger: which enhancements are available."""
    return {
        "noise_reduction": {
            "available": is_noise_reduction_available(),
            "engine": "DeepFilterNet (pip install deepfilternet)",
            "env": "AUDIO_ENHANCE_NOISE=1 or AUDIO_ENHANCE=1",
        },
        "loudnorm": {
            "available": is_loudnorm_available(),
            "engine": "FFmpeg loudnorm/dynaudnorm",
            "env": "AUDIO_ENHANCE_LOUDNORM=1 or AUDIO_ENHANCE=1",
        },
    }
