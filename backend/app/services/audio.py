"""Audio conversion, cleaning, quality gates, and cached audio service for VoiceQueue."""

from datetime import datetime
import io
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time
from typing import Dict, Optional, Tuple
import wave

from backend.app.config import settings

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Cache directory for fixed audio prompts
AUDIO_CACHE_DIR = BASE_DIR / "cache" / "audio"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Debug audio directory (git-ignored, cleared at startup, holds last 20 files)
DEBUG_AUDIO_DIR = BASE_DIR / "backend" / "debug_audio"

MAX_AUDIO_DURATION_SECONDS = 30.0
MIN_AUDIO_DURATION_SECONDS = 0.5
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB maximum audio upload size
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".wave", ".webm", ".ogg", ".oga", ".m4a", ".mp4", ".mp3"}


class AudioQualityGateError(Exception):
    """Exception raised when an audio quality gate is violated before calling Gnani."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def get_friendly_gate_message(error_code: str, lang: str = "te-IN") -> str:
    """Returns a friendly message in the user's selected language for a quality gate error."""
    is_te = lang.startswith("te")
    if error_code == "too_quiet":
        return (
            "మీ మాట చాలా తక్కువగా వినిపించింది. దయచేసి కొంచెం గట్టిగా మాట్లాడండి."
            if is_te
            else "I can hardly hear you. Speak louder or move the microphone closer."
        )
    elif error_code == "no_speech":
        return (
            "ఎటువంటి మాటలు వినిపించలేదు. దయచేసి మైక్రోఫోన్ దగ్గరగా మళ్లీ మాట్లాడండి."
            if is_te
            else "No speech detected. Please speak clearly into the microphone."
        )
    elif error_code == "too_short":
        return (
            "ఆడియో చాలా తక్కువగా ఉంది, దయచేసి బటన్ పట్టుకుని కొంచెం సేపు మాట్లాడండి."
            if is_te
            else "Too short, hold the key a little longer."
        )
    elif error_code == "too_long":
        return (
            "ఆడియో చాలా పెద్దదిగా ఉంది (గరిష్టంగా 30 సెకన్లు). దయచేసి క్లుప్తంగా చెప్పండి."
            if is_te
            else "Audio is too long (maximum 30 seconds). Please speak briefly."
        )
    elif error_code == "corrupt_file":
        return (
            "ఆడియో ఫైల్ స్పష్టంగా లేదు. దయచేసి మళ్లీ మాట్లాడండి."
            if is_te
            else "Audio file is corrupt or unreadable. Please try again."
        )
    return (
        "క్షమించండి, మీ మాట స్పష్టంగా వినిపించలేదు. దయచేసి మళ్లీ చెప్పండి."
        if is_te
        else "Sorry, could not understand clearly. Please say it again."
    )


def compute_audio_stats(wav_bytes: bytes) -> Dict[str, float]:
    """Computes duration in seconds, peak amplitude (0.0-1.0), and RMS (0.0-1.0) of 16-bit PCM WAV."""
    if not wav_bytes or len(wav_bytes) <= 44:
        return {"duration": 0.0, "peak": 0.0, "rms": 0.0}

    try:
        with io.BytesIO(wav_bytes) as buf, wave.open(buf, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate) if rate > 0 else 0.0
            raw_data = wf.readframes(frames)
    except Exception:
        return {"duration": 0.0, "peak": 0.0, "rms": 0.0}

    num_samples = len(raw_data) // 2
    if num_samples == 0:
        return {"duration": duration, "peak": 0.0, "rms": 0.0}

    samples = struct.unpack(f"<{num_samples}h", raw_data)
    max_peak = max(abs(s) for s in samples) / 32768.0
    sum_sq = sum((s / 32768.0) ** 2 for s in samples)
    rms = math.sqrt(sum_sq / num_samples)
    return {"duration": duration, "peak": round(max_peak, 4), "rms": round(rms, 4)}


def detect_audio_extension(raw_bytes: bytes, filename: str) -> str:
    """Validates audio file type and size, prioritizing WAV, WebM, OGG, M4A, MP3."""
    if len(raw_bytes) > MAX_AUDIO_BYTES:
        raise AudioQualityGateError("too_large", f"Audio size {len(raw_bytes)} bytes exceeds 10MB limit.")

    # Check magic bytes first
    if raw_bytes.startswith(b"RIFF"):
        return ".wav"
    if raw_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    if raw_bytes.startswith(b"OggS"):
        return ".ogg"
    if len(raw_bytes) >= 8 and raw_bytes[4:8] in (b"ftyp", b"moov", b"mdat"):
        return ".m4a"
    if raw_bytes.startswith((b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
        return ".mp3"

    ext = Path(filename).suffix.lower() if filename else ""
    if ext in ALLOWED_AUDIO_EXTENSIONS:
        return ext
    if not ext or ext in (".tmp", ".bin"):
        return ".wav"

    raise AudioQualityGateError("unsupported_format", f"Unsupported audio file extension: '{ext}'")


_LAST_DEBUG_FILES: tuple[Optional[str], Optional[str]] = (None, None)


def get_last_debug_files() -> tuple[Optional[str], Optional[str]]:
    """Returns the most recent (raw_filename, cleaned_filename) saved during debug."""
    global _LAST_DEBUG_FILES
    return _LAST_DEBUG_FILES


def clear_debug_audio_dir():
    """Clears all clips in backend/debug_audio/ at startup if debug mode is enabled."""
    global _LAST_DEBUG_FILES
    _LAST_DEBUG_FILES = (None, None)
    if DEBUG_AUDIO_DIR.exists():
        for f in DEBUG_AUDIO_DIR.glob("*"):
            try:
                f.unlink()
            except OSError:
                pass


def save_debug_audio_clip(
    raw_bytes: bytes,
    cleaned_bytes: bytes,
    ext: str = ".wav",
) -> tuple[Optional[str], Optional[str]]:
    """Saves raw and cleaned audio clips with timestamps, maintaining at most 20 clips."""
    global _LAST_DEBUG_FILES
    if not settings.DEBUG_SAVE_AUDIO:
        _LAST_DEBUG_FILES = (None, None)
        return None, None

    DEBUG_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    raw_filename = f"{ts}_raw{ext}"
    clean_filename = f"{ts}_cleaned.wav"
    raw_path = DEBUG_AUDIO_DIR / raw_filename
    clean_path = DEBUG_AUDIO_DIR / clean_filename

    try:
        raw_path.write_bytes(raw_bytes)
        clean_path.write_bytes(cleaned_bytes)
        _LAST_DEBUG_FILES = (raw_filename, clean_filename)
    except Exception as e:
        print(f"[Debug Audio] Failed to write debug clip: {e}")
        _LAST_DEBUG_FILES = (None, None)
        return None, None

    # Keep only the last 20 files
    try:
        all_files = sorted(DEBUG_AUDIO_DIR.glob("*"), key=lambda p: p.stat().st_mtime)
        if len(all_files) > 20:
            for old_file in all_files[:-20]:
                try:
                    old_file.unlink()
                except OSError:
                    pass
    except Exception:
        pass

    return raw_filename, clean_filename


def is_wav16k_mono(raw_bytes: bytes) -> bool:
    """Checks if raw bytes are already valid 16kHz mono 16-bit PCM WAV (avoids re-encoding)."""
    if not raw_bytes or len(raw_bytes) < 44 or not raw_bytes.startswith(b"RIFF"):
        return False
    if len(raw_bytes) >= 12 and raw_bytes[8:12] != b"WAVE":
        return False
    try:
        with io.BytesIO(raw_bytes) as buf, wave.open(buf, "rb") as wf:
            return wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() == 16000
    except Exception:
        return False


def is_audio_level_good(stats: Dict[str, float]) -> bool:
    """Returns True if audio volume and SNR are already in a good range (skip cleaning)."""
    peak = stats.get("peak", 0.0)
    rms = stats.get("rms", 0.0)
    return 0.15 <= peak <= 0.88 and rms >= 0.03


def process_voice_audio_timed(
    raw_bytes: bytes,
    filename: str = "input.wav",
    clean: bool = True,
) -> Tuple[bytes, Dict[str, float], bool, Dict[str, float]]:
    """
    Timed audio pipeline measuring convert, quality_gates, and clean with monotonic clock:
    1. convert: Ingests 16kHz mono WAV directly or runs ffmpeg to convert.
    2. quality_gates: Checks raw duration and amplitude metrics.
    3. clean: Skips cleaning if audio level is already good, otherwise runs filter chain.
    Returns: (wav_bytes, cleaned_stats, cleaning_ran, stage_times_ms)
    """
    if not raw_bytes or len(raw_bytes.strip()) == 0:
        raise AudioQualityGateError("no_speech", "Audio recording is empty.")

    ext = detect_audio_extension(raw_bytes, filename)
    t_convert_start = time.perf_counter()

    # Quick Win: Avoid decoding and re-encoding if already standard 16kHz mono 16-bit PCM WAV
    already_16k_mono = is_wav16k_mono(raw_bytes)

    in_path = None
    raw_wav_path = None
    cleaned_wav_path = None

    try:
        if already_16k_mono:
            raw_wav_bytes = raw_bytes
            convert_ms = (time.perf_counter() - t_convert_start) * 1000.0
        else:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as in_file:
                in_file.write(raw_bytes)
                in_path = in_file.name
            raw_wav_path = in_path + ".raw16k.wav"

            cmd_raw = [
                "ffmpeg",
                "-y",
                "-i",
                in_path,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-acodec",
                "pcm_s16le",
                raw_wav_path,
            ]
            res_raw = subprocess.run(
                cmd_raw,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                check=False,
            )
            if res_raw.returncode != 0:
                err = res_raw.stderr.decode("utf-8", errors="ignore")
                raise AudioQualityGateError("corrupt_file", f"Failed to decode audio: {err[:200]}")

            with open(raw_wav_path, "rb") as rf:
                raw_wav_bytes = rf.read()
            convert_ms = (time.perf_counter() - t_convert_start) * 1000.0

        # Stage: quality_gates (initial check)
        t_gate1_start = time.perf_counter()
        raw_stats = compute_audio_stats(raw_wav_bytes)
        raw_dur = raw_stats["duration"]
        raw_peak = raw_stats["peak"]
        raw_rms = raw_stats["rms"]

        if raw_dur < MIN_AUDIO_DURATION_SECONDS:
            raise AudioQualityGateError(
                "too_short",
                f"Audio recording is {raw_dur:.2f}s, which is shorter than {MIN_AUDIO_DURATION_SECONDS}s.",
            )
        if raw_dur > MAX_AUDIO_DURATION_SECONDS:
            raise AudioQualityGateError(
                "too_long",
                f"Audio recording is {raw_dur:.1f}s, which exceeds {MAX_AUDIO_DURATION_SECONDS}s.",
            )
        if not clean and raw_peak >= 0.999:
            raise AudioQualityGateError(
                "too_loud",
                f"Audio recording is clipped or too loud (peak={raw_peak:.3f}).",
            )
        gate_ms = (time.perf_counter() - t_gate1_start) * 1000.0

        # Stage: clean
        # Quick Win: Skip cleaning when audio level is already good
        t_clean_start = time.perf_counter()
        level_good = is_audio_level_good(raw_stats)
        cleaning_ran = False

        if settings.AUDIO_CLEAN and clean and not level_good:
            # Need cleaning filter chain
            if not raw_wav_path:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as raw_f:
                    raw_f.write(raw_wav_bytes)
                    raw_wav_path = raw_f.name
            cleaned_wav_path = raw_wav_path + ".cleaned.wav"

            filter_chain = (
                "highpass=f=80,"
                "lowpass=f=7500,"
                "afftdn=nr=10,"
                "dynaudnorm,"
                "silenceremove=start_periods=1:start_duration=0.15:start_threshold=-45dB:"
                "stop_periods=-1:stop_duration=0.15:stop_threshold=-45dB:detection=peak"
            )
            cmd_clean = [
                "ffmpeg",
                "-y",
                "-i",
                raw_wav_path,
                "-af",
                filter_chain,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-acodec",
                "pcm_s16le",
                cleaned_wav_path,
            ]
            res_clean = subprocess.run(
                cmd_clean,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                check=False,
            )
            if res_clean.returncode == 0 and os.path.exists(cleaned_wav_path):
                with open(cleaned_wav_path, "rb") as cf:
                    cleaned_bytes = cf.read()
                cleaning_ran = True
            else:
                cleaned_bytes = raw_wav_bytes
        else:
            cleaned_bytes = raw_wav_bytes

        clean_ms = (time.perf_counter() - t_clean_start) * 1000.0

        # Stage: quality_gates (post-cleaning check)
        t_gate2_start = time.perf_counter()
        cleaned_stats = compute_audio_stats(cleaned_bytes)
        cleaned_dur = cleaned_stats["duration"]
        cleaned_peak = cleaned_stats["peak"]
        cleaned_rms = cleaned_stats["rms"]

        if cleaning_ran and cleaned_dur < 0.25:
            raise AudioQualityGateError(
                "no_speech",
                f"No speech detected after trimming (duration={cleaned_dur:.2f}s).",
            )
        if cleaned_peak < 0.015 or cleaned_rms < 0.005:
            raise AudioQualityGateError(
                "too_quiet",
                f"Audio is too quiet after cleaning (peak={cleaned_peak:.3f}, rms={cleaned_rms:.3f}).",
            )
        gate_ms += (time.perf_counter() - t_gate2_start) * 1000.0

        # Save debug clips if enabled
        save_debug_audio_clip(raw_bytes, cleaned_bytes, ext=ext)

        stage_times = {
            "convert": round(convert_ms, 2),
            "clean": round(clean_ms, 2),
            "quality_gates": round(gate_ms, 2),
        }
        return cleaned_bytes, cleaned_stats, cleaning_ran, stage_times

    finally:
        for temp_p in [in_path, raw_wav_path, cleaned_wav_path]:
            if temp_p and os.path.exists(temp_p):
                try:
                    os.remove(temp_p)
                except OSError:
                    pass


def process_audio_with_gates(
    raw_bytes: bytes,
    filename: str = "input.wav",
    clean: bool = True,
) -> bytes:
    """
    Accepts raw audio bytes (WAV first, webm/ogg/m4a fallback), converts to 16kHz mono 16-bit WAV,
    evaluates quality gates before returning. Backwards-compatible wrapper.
    """
    wav_bytes, _, _, _ = process_voice_audio_timed(raw_bytes, filename=filename, clean=clean)
    return wav_bytes


def to_wav16k_mono(raw_bytes: bytes, filename: str = "input.wav") -> bytes:
    """Wrapper backwards-compatible with previous phases."""
    return process_audio_with_gates(raw_bytes, filename=filename)


def get_cached_audio(cache_key: str) -> Optional[bytes]:
    """Retrieves cached audio bytes for a given cache key, or None if not found or invalid."""
    if not cache_key:
        return None
    file_path = AUDIO_CACHE_DIR / f"{cache_key}.wav"
    if file_path.exists():
        try:
            data = file_path.read_bytes()
            fixed = fix_wav_header(data)
            validate_wav(fixed)
            return fixed
        except Exception as e:
            print(f"[Audio Cache] Cached audio '{cache_key}.wav' failed validation: {e}. Removing.")
            try:
                file_path.unlink()
            except Exception:
                pass
            return None
    return None


def save_cached_audio(cache_key: str, audio_bytes: bytes, text: Optional[str] = None) -> Optional[Path]:
    """Saves synthesized audio to the local cache directory after fixing header and validating."""
    if not cache_key or not audio_bytes:
        return None
    fixed = fix_wav_header(audio_bytes)
    try:
        validate_wav(fixed, text=text)
    except Exception as e:
        print(f"[Audio Cache] Refusing to cache invalid audio for '{cache_key}': {e}")
        return None

    AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = AUDIO_CACHE_DIR / f"{cache_key}.wav"
    with open(file_path, "wb") as f:
        f.write(fixed)
    return file_path


class WavInfo(dict):
    """Holds parsed and validated WAV metadata with dict, attribute, and tuple access."""

    def __init__(
        self,
        sample_rate: int,
        channels: int,
        bits: int,
        data_bytes: int,
        duration_seconds: float,
    ):
        super().__init__(
            sample_rate=sample_rate,
            channels=channels,
            bits=bits,
            data_bytes=data_bytes,
            real_data_length=data_bytes,
            duration=duration_seconds,
            duration_seconds=duration_seconds,
        )
        self.sample_rate = sample_rate
        self.channels = channels
        self.bits = bits
        self.data_bytes = data_bytes
        self.real_data_length = data_bytes
        self.duration = duration_seconds
        self.duration_seconds = duration_seconds

    def __iter__(self):
        yield self.sample_rate
        yield self.channels
        yield self.bits
        yield self.data_bytes
        yield self.duration_seconds


def repair_wav_header(raw_bytes: bytes) -> bytes:
    """
    Fix WAV headers: if the header's data size or RIFF size is 0, 0xFFFFFFFF, 0x7FFFFFFF
    or does not match the real byte length, rewrite the header using the real length.
    """
    if not raw_bytes or len(raw_bytes) < 44:
        return raw_bytes
    if not (raw_bytes.startswith(b"RIFF") and raw_bytes[8:12] == b"WAVE"):
        return raw_bytes

    total_len = len(raw_bytes)
    offset = 12
    data_chunk_offset = None
    data_chunk_size = None

    while offset + 8 <= total_len:
        chunk_id = raw_bytes[offset : offset + 4]
        chunk_sz = struct.unpack("<I", raw_bytes[offset + 4 : offset + 8])[0]
        if chunk_id == b"data":
            data_chunk_offset = offset
            data_chunk_size = chunk_sz
            break
        offset += 8 + chunk_sz
        if chunk_sz % 2 != 0:
            offset += 1

    if data_chunk_offset is None:
        return raw_bytes

    real_data_bytes = total_len - (data_chunk_offset + 8)
    real_riff_size = total_len - 8
    curr_riff_size = struct.unpack("<I", raw_bytes[4:8])[0]

    needs_fix = (
        data_chunk_size in (0, 0xFFFFFFFF, 0x7FFFFFFF)
        or curr_riff_size in (0, 0xFFFFFFFF, 0x7FFFFFFF)
        or data_chunk_size != real_data_bytes
        or curr_riff_size != real_riff_size
    )

    if not needs_fix:
        return raw_bytes

    b = bytearray(raw_bytes)
    struct.pack_into("<I", b, 4, max(0, real_riff_size))
    struct.pack_into("<I", b, data_chunk_offset + 4, max(0, real_data_bytes))
    return bytes(b)


fix_wav_header = repair_wav_header


def validate_wav(wav_bytes: bytes, text: Optional[str] = None) -> WavInfo:
    """
    Parses the RIFF/WAVE header and returns sample_rate, channels, bits, data_bytes and duration_seconds.
    Rejects audio that is empty, not WAV, shorter than 0.3 s, or much shorter than expected
    for the text length (use roughly 0.05 s per character as a loose minimum).
    Raises ValueError on invalid audio.
    """
    if not wav_bytes:
        raise ValueError("Audio is empty.")
    if len(wav_bytes) < 44:
        raise ValueError("Audio is too short to be a valid WAV file (< 44 bytes).")
    if not wav_bytes.startswith(b"RIFF") or wav_bytes[8:12] != b"WAVE":
        raise ValueError("Not a valid RIFF/WAVE file.")

    total_len = len(wav_bytes)
    offset = 12
    fmt_found = False
    data_found = False

    sample_rate = 0
    channels = 0
    bits = 0
    data_bytes = 0
    data_start = 0

    while offset + 8 <= total_len:
        chunk_id = wav_bytes[offset : offset + 4]
        chunk_sz = struct.unpack("<I", wav_bytes[offset + 4 : offset + 8])[0]
        if chunk_id == b"fmt ":
            fmt_found = True
            if chunk_sz >= 16 and offset + 8 + 16 <= total_len:
                audio_fmt, channels, sample_rate, byte_rate, block_align, bits = struct.unpack(
                    "<HHIIHH", wav_bytes[offset + 8 : offset + 24]
                )
        elif chunk_id == b"data":
            data_found = True
            data_bytes = chunk_sz
            data_start = offset + 8
            break
        offset += 8 + chunk_sz
        if chunk_sz % 2 != 0:
            offset += 1

    if not fmt_found or not data_found:
        raise ValueError("WAV file missing required 'fmt ' or 'data' chunk.")

    if sample_rate <= 0 or channels <= 0 or bits <= 0:
        raise ValueError(
            f"Invalid WAV parameters: sample_rate={sample_rate}, channels={channels}, bits={bits}"
        )

    if data_bytes == 0:
        raise ValueError("WAV data chunk size in header is 0.")

    actual_data_len = total_len - data_start
    if actual_data_len < data_bytes:
        raise ValueError(
            f"WAV audio is truncated: header declared {data_bytes} bytes, found {actual_data_len}."
        )

    bytes_per_sec = sample_rate * channels * (bits // 8)
    if bytes_per_sec <= 0:
        raise ValueError("Invalid WAV byte rate.")

    duration_seconds = round(data_bytes / float(bytes_per_sec), 3)

    if duration_seconds < 0.3:
        raise ValueError(
            f"WAV audio duration {duration_seconds:.2f}s is shorter than minimum 0.3s."
        )

    # Check against text length minimum if text is supplied (allow natural neural speech cadence up to ~28 chars/sec)
    if text and text.strip():
        char_count = len(text.strip())
        min_expected_duration = max(0.3, char_count * 0.035)
        if duration_seconds < min_expected_duration:
            raise ValueError(
                f"WAV audio duration {duration_seconds:.2f}s is much shorter than expected minimum "
                f"{min_expected_duration:.2f}s for text length {char_count} chars."
            )

    return WavInfo(
        sample_rate=sample_rate,
        channels=channels,
        bits=bits,
        data_bytes=data_bytes,
        duration_seconds=duration_seconds,
    )


def get_expected_cache_text(cache_key: str) -> Optional[str]:
    """Retrieves the expected text phrase for a known cache key."""
    try:
        from backend.app.services.replies import FIXED_PHRASE_GENERATORS

        for gen in FIXED_PHRASE_GENERATORS.values():
            for lang_code in ("te", "en"):
                text, k = gen(lang_code)
                if k == cache_key:
                    return text
    except Exception:
        pass
    return None


def scan_and_clean_audio_cache() -> list[str]:
    """
    Scans backend/cache/audio at startup.
    Fixes headers with 0 or 0xFFFFFFFF if the underlying audio is valid.
    Deletes any file that fails validate_wav (e.g. truncated, < 0.3s, or much shorter than expected).
    Returns list of deleted filenames.
    """
    deleted_files = []
    if not AUDIO_CACHE_DIR.exists():
        return deleted_files

    for wav_file in sorted(AUDIO_CACHE_DIR.glob("*.wav")):
        try:
            raw_bytes = wav_file.read_bytes()
            fixed_bytes = fix_wav_header(raw_bytes)
            if fixed_bytes != raw_bytes:
                wav_file.write_bytes(fixed_bytes)
                raw_bytes = fixed_bytes

            expected_text = get_expected_cache_text(wav_file.stem)
            validate_wav(raw_bytes, text=expected_text)
        except Exception as e:
            try:
                wav_file.unlink()
                deleted_files.append(wav_file.name)
                print(f"[Audio Cache] Deleted invalid cache file '{wav_file.name}': {e}")
            except Exception as del_err:
                print(f"[Audio Cache] Failed to delete invalid cache file '{wav_file.name}': {del_err}")

    if deleted_files:
        print(f"[Audio Cache] Removed {len(deleted_files)} invalid files from cache: {', '.join(deleted_files)}")
        print("[Audio Cache] Rebuild cache command: python scripts/build_cache.py")

    return deleted_files
