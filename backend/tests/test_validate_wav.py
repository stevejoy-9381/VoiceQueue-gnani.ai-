"""Tests for WAV validation, header repair, and minimum duration enforcement."""

import io
import struct
import wave
import pytest

from backend.app.services.audio import (
    WavInfo,
    fix_wav_header,
    repair_wav_header,
    validate_wav,
)


def _create_wav(duration_s: float = 1.0, sample_rate: int = 16000, channels: int = 1, bits: int = 16) -> bytes:
    """Helper to generate a valid PCM WAV byte sequence."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(bits // 8)
        wf.setframerate(sample_rate)
        num_frames = int(duration_s * sample_rate)
        # 16-bit silence
        data = b"\x00" * (num_frames * channels * (bits // 8))
        wf.writeframes(data)
    return buf.getvalue()


def test_validate_wav_good_file():
    """Good 1.0s WAV passes and returns sample_rate, channels, bits, data_bytes, duration_seconds."""
    good_bytes = _create_wav(duration_s=1.0, sample_rate=16000, channels=1, bits=16)
    info = validate_wav(good_bytes)

    assert isinstance(info, WavInfo)
    assert info.sample_rate == 16000
    assert info.channels == 1
    assert info.bits == 16
    assert info.data_bytes == 32000
    assert info.duration_seconds == 1.0

    # Test dict-like access
    assert info["sample_rate"] == 16000
    assert info["duration_seconds"] == 1.0

    # Test tuple unpacking
    sr, ch, b, db, dur = validate_wav(good_bytes)
    assert sr == 16000
    assert ch == 1
    assert b == 16
    assert db == 32000
    assert dur == 1.0


def test_validate_wav_header_size_zero():
    """Header with data chunk size 0 is rejected."""
    good_bytes = _create_wav(duration_s=1.0)
    # Mutate data size (bytes 40..44) to 0
    corrupted = bytearray(good_bytes)
    struct.pack_into("<I", corrupted, 40, 0)

    with pytest.raises(ValueError, match="data chunk size in header is 0"):
        validate_wav(bytes(corrupted))


def test_validate_wav_truncated_file():
    """Truncated file with fewer bytes than declared in header is rejected."""
    good_bytes = _create_wav(duration_s=1.0)
    # Cut off all but 200 bytes
    truncated = good_bytes[:200]

    with pytest.raises(ValueError, match="truncated"):
        validate_wav(truncated)


def test_validate_wav_empty_file():
    """Empty or near-empty bytes are rejected."""
    with pytest.raises(ValueError, match="empty"):
        validate_wav(b"")

    with pytest.raises(ValueError, match="too short"):
        validate_wav(b"RIFF1234WAVE")


def test_validate_wav_shorter_than_minimum():
    """Valid WAV shorter than 0.3s is rejected."""
    short_bytes = _create_wav(duration_s=0.2)
    with pytest.raises(ValueError, match="shorter than minimum 0.3s"):
        validate_wav(short_bytes)


def test_validate_wav_text_length_heuristic():
    """Audio much shorter than expected for text length is rejected."""
    # 0.5s audio
    audio_05s = _create_wav(duration_s=0.5)

    # 40 character text requires roughly 40 * 0.05 = 2.0s
    long_text = "నమస్కారం! డెమో క్లినిక్ వాయిస్ క్యూకి స్వాగతం"
    with pytest.raises(ValueError, match="much shorter than expected minimum"):
        validate_wav(audio_05s, text=long_text)

    # Short 4-char text requires max(0.3, 0.20s) = 0.3s -> 0.5s passes
    info = validate_wav(audio_05s, text="హలో")
    assert info.duration_seconds == 0.5


def test_fix_wav_header_rewrites_invalid_sizes():
    """fix_wav_header repairs 0xFFFFFFFF, 0x7FFFFFFF, and size mismatches from Timbre."""
    raw_bytes = _create_wav(duration_s=1.5)
    total_len = len(raw_bytes)
    # Corrupt RIFF size and data size to 0xFFFFFFFF
    corrupted = bytearray(raw_bytes)
    struct.pack_into("<I", corrupted, 4, 0xFFFFFFFF)
    struct.pack_into("<I", corrupted, 40, 0xFFFFFFFF)

    fixed = repair_wav_header(bytes(corrupted))
    assert fixed != bytes(corrupted)

    # Verify fixed header
    riff_sz = struct.unpack("<I", fixed[4:8])[0]
    data_sz = struct.unpack("<I", fixed[40:44])[0]
    assert riff_sz == total_len - 8
    assert data_sz == total_len - 44

    # Validate that the fixed audio passes validate_wav cleanly
    info = validate_wav(fixed)
    assert info.duration_seconds == 1.5


def test_repair_wav_header_size_zero():
    """repair_wav_header repairs headers where data size or RIFF size is 0."""
    raw_bytes = _create_wav(duration_s=0.8)
    total_len = len(raw_bytes)

    corrupted = bytearray(raw_bytes)
    struct.pack_into("<I", corrupted, 4, 0)
    struct.pack_into("<I", corrupted, 40, 0)

    repaired = repair_wav_header(bytes(corrupted))
    assert repaired != bytes(corrupted)

    riff_sz = struct.unpack("<I", repaired[4:8])[0]
    data_sz = struct.unpack("<I", repaired[40:44])[0]
    assert riff_sz == total_len - 8
    assert data_sz == total_len - 44

    info = validate_wav(repaired)
    assert info.duration == 0.8
    assert info.real_data_length == total_len - 44


def test_repair_wav_header_size_mismatch():
    """repair_wav_header fixes declared size that does not match real byte length."""
    raw_bytes = _create_wav(duration_s=1.0)
    total_len = len(raw_bytes)

    # Set declared data size to 999999
    corrupted = bytearray(raw_bytes)
    struct.pack_into("<I", corrupted, 40, 999999)

    repaired = repair_wav_header(bytes(corrupted))
    data_sz = struct.unpack("<I", repaired[40:44])[0]
    assert data_sz == total_len - 44

    info = validate_wav(repaired)
    assert info.sample_rate == 16000
    assert info.channels == 1
    assert info.bits == 16
    assert info.real_data_length == 32000
    assert info.duration == 1.0


