"""Tests for Clinic Dashboard API endpoints, voice activity logs, and WebSocket manager."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db import Base
from backend.app.models import Token, VoiceLog
from backend.app.routers.turn_router import get_voice_logs
from backend.app.services.connection_manager import ConnectionManager, broadcast_queue_change

# Test Database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_get_voice_logs_empty(db_session):
    logs = get_voice_logs(limit=20, db=db_session)
    assert logs == []


def test_get_voice_logs_with_data(db_session):
    now = datetime.now(timezone.utc)
    tok = Token(number=1, date="2026-11-02", label="Demo Patient 1", language="te-IN", status="waiting")
    db_session.add(tok)
    db_session.commit()
    db_session.refresh(tok)

    vlog1 = VoiceLog(
        token_id=tok.id,
        transcript="Naaku repu token kavali",
        detected_language="te-IN",
        intent="BOOK",
        noise_label="clean",
        ok=True,
        created_at=now - timedelta(seconds=10),
    )
    vlog2 = VoiceLog(
        token_id=None,
        transcript="What is my queue status",
        detected_language="en-IN",
        intent="STATUS",
        noise_label=None,
        ok=True,
        created_at=now,
    )
    db_session.add_all([vlog1, vlog2])
    db_session.commit()

    logs = get_voice_logs(limit=10, db=db_session)
    assert len(logs) == 2

    # Most recent first
    assert logs[0].intent == "STATUS"
    assert logs[0].token_number is None

    assert logs[1].intent == "BOOK"
    assert logs[1].token_number == 1
    assert logs[1].transcript == "Naaku repu token kavali"
    assert logs[1].ok is True


def test_voice_logs_limit(db_session):
    for i in range(25):
        vlog = VoiceLog(
            token_id=None,
            transcript=f"Test query {i}",
            detected_language="te-IN",
            intent="UNKNOWN",
            ok=True,
        )
        db_session.add(vlog)
    db_session.commit()

    logs = get_voice_logs(limit=5, db=db_session)
    assert len(logs) == 5


def test_connection_manager_logic():
    cm = ConnectionManager()

    class MockWebSocket:
        def __init__(self):
            self.accepted = False
            self.sent_messages = []

        async def accept(self):
            self.accepted = True

        async def send_json(self, data):
            self.sent_messages.append(data)

    ws1 = MockWebSocket()

    # Step 1: Connect
    coro_connect = cm.connect(ws1)
    try:
        coro_connect.send(None)
    except StopIteration:
        pass

    assert ws1 in cm.active_connections
    assert ws1.accepted is True

    # Step 2: Broadcast
    test_msg = {"type": "queue_changed", "date": "2026-11-02"}
    coro_broadcast = cm.broadcast(test_msg)
    try:
        coro_broadcast.send(None)
    except StopIteration:
        pass

    assert ws1.sent_messages == [test_msg]

    # Step 3: Disconnect
    cm.disconnect(ws1)
    assert ws1 not in cm.active_connections

    # Step 4: Broadcast Hook safe execution
    broadcast_queue_change("2026-11-02")
