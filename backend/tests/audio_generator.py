"""Audio clip generator for test cases.

Generates 8 specific WAV/data files under backend/tests/audio:
1. silence.wav - 2.0s pure silence (zero amplitude)
2. tone_0_2s.wav - 0.2s tone (too short, < 0.5s)
3. speech_1s.wav - 1.0s speech-like dual-tone audio (valid)
4. quiet_tone.wav - 2.0s very low amplitude tone (too quiet)
5. loud_clipped.wav - 2.0s maximum amplitude saturated tone
6. long_35s.wav - 35.0s tone (too long, > 30.0s)
7. corrupt.wav - Corrupted/invalid non-audio bytes
8. empty.wav - 0-byte file
"""

from pathlib import Path
import wave
import numpy as np

AUDIO_DIR = Path(__file__).resolve().parent / "audio"
SAMPLE_RATE = 16000


def _write_wav(path: Path, samples: np.ndarray, rate: int = SAMPLE_RATE):
    samples = np.clip(samples, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(samples.tobytes())


def ensure_test_audio_files() -> dict[str, Path]:
    """Generates test audio files if they don't already exist and returns their paths."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    # 1. silence (2.0s)
    silence_path = AUDIO_DIR / "silence.wav"
    t_2 = np.linspace(0, 2.0, int(SAMPLE_RATE * 2.0), endpoint=False)
    _write_wav(silence_path, np.zeros_like(t_2))
    paths["silence"] = silence_path

    # 2. tone_0_2s (0.2s - shorter than 0.5s gate)
    tone_02_path = AUDIO_DIR / "tone_0_2s.wav"
    t_02 = np.linspace(0, 0.2, int(SAMPLE_RATE * 0.2), endpoint=False)
    _write_wav(tone_02_path, 10000 * np.sin(2 * np.pi * 440 * t_02))
    paths["tone_0_2s"] = tone_02_path

    # 3. speech_1s (1.0s speech-like format with formants)
    speech_path = AUDIO_DIR / "speech_1s.wav"
    t_1 = np.linspace(0, 1.0, int(SAMPLE_RATE * 1.0), endpoint=False)
    formant = 8000 * np.sin(2 * np.pi * 300 * t_1) + 6000 * np.sin(2 * np.pi * 1200 * t_1)
    _write_wav(speech_path, formant)
    paths["speech_1s"] = speech_path

    # 4. quiet_tone (2.0s amplitude 100 -> peak < 0.015, rms < 0.005)
    quiet_path = AUDIO_DIR / "quiet_tone.wav"
    _write_wav(quiet_path, 100 * np.sin(2 * np.pi * 440 * t_2))
    paths["quiet_tone"] = quiet_path

    # 5. loud_clipped (2.0s saturated tone)
    loud_path = AUDIO_DIR / "loud_clipped.wav"
    _write_wav(loud_path, 40000 * np.sin(2 * np.pi * 440 * t_2))
    paths["loud_clipped"] = loud_path

    # 6. long_35s (35.0s - longer than 30.0s gate)
    long_path = AUDIO_DIR / "long_35s.wav"
    t_35 = np.linspace(0, 35.0, int(SAMPLE_RATE * 35.0), endpoint=False)
    _write_wav(long_path, 5000 * np.sin(2 * np.pi * 440 * t_35))
    paths["long_35s"] = long_path

    # 7. corrupt (invalid header and data)
    corrupt_path = AUDIO_DIR / "corrupt.wav"
    corrupt_path.write_bytes(b"CORRUPT_NOT_A_WAV_FILE_GARBAGE_PAYLOAD_1234567890")
    paths["corrupt"] = corrupt_path

    # 8. empty (0 bytes)
    empty_path = AUDIO_DIR / "empty.wav"
    empty_path.write_bytes(b"")
    paths["empty"] = empty_path

    return paths


if __name__ == "__main__":
    generated = ensure_test_audio_files()
    print(f"Generated {len(generated)} audio clips in {AUDIO_DIR}")

