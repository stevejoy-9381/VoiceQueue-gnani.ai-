from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.db import Base


class GnaniUsage(Base):
    """Logs every real call to Gnani AI models."""

    __tablename__ = "gnani_usage"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    kind = Column(String(10), nullable=False)  # 'stt' or 'tts'
    cached = Column(Boolean, default=False, nullable=False)
    ok = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Token(Base):
    """Clinic queue token model."""

    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    number = Column(Integer, nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    label = Column(String(50), nullable=False)
    language = Column(String(10), nullable=False, default="te-IN")
    status = Column(
        String(20),
        nullable=False,
        default="waiting",
        index=True,
    )  # waiting, in_consult, done, cancelled, no_show
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    voice_logs = relationship("VoiceLog", back_populates="token")


class VoiceLog(Base):
    """Voice interaction audit and telemetry log."""

    __tablename__ = "voice_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=True)
    transcript = Column(Text, nullable=False)
    detected_language = Column(String(10), nullable=False)
    intent = Column(String(50), nullable=False)
    noise_label = Column(String(50), nullable=True)
    ok = Column(Boolean, default=True, nullable=False)
    duration = Column(Float, nullable=True)
    peak = Column(Float, nullable=True)
    rms = Column(Float, nullable=True)
    cleaned = Column(Boolean, default=True, nullable=False)
    raw_audio_file = Column(String(100), nullable=True)
    cleaned_audio_file = Column(String(100), nullable=True)
    error = Column(Text, nullable=True)
    is_compare = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    token = relationship("Token", back_populates="voice_logs")


class AudioCompare(Base):
    """Manual audio comparison log comparing raw and cleaned audio turns."""

    __tablename__ = "audio_compare"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sentence = Column(Text, nullable=False)
    cleaned_transcript = Column(Text, nullable=True)
    raw_transcript = Column(Text, nullable=True)
    which_better = Column(String(50), nullable=True)  # 'cleaned', 'raw', 'same', or notes
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class VoiceTest(Base):
    """Voice test trial telemetry model for testing accuracy & noise resilience."""

    __tablename__ = "voice_tests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    language = Column(String(20), nullable=False)  # te, en, mix
    noise = Column(String(20), nullable=False)  # quiet, fan, street
    expected_intent = Column(String(20), nullable=False)
    got_intent = Column(String(20), nullable=False)
    transcript = Column(Text, nullable=False)
    intended_sentence = Column(Text, nullable=True)
    passed = Column(Boolean, nullable=False, default=True)
    note = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

