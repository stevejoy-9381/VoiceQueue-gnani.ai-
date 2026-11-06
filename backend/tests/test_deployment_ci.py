"""
Unit Tests for Deployment, Dockerfile, Autoseed, and Smoke Scripts (P2-8)

Guarantees zero Gnani calls during tests.
"""

from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models import Base, Token
from backend.app.services.queue_service import auto_seed_if_empty, list_queue
from backend.app.config import Settings
import scripts.smoke_deployed as smoke


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_auto_seed_if_empty_seeds_4_tokens(test_db):
    """When the queue is empty, auto_seed_if_empty creates 4 fake tokens."""
    tokens = auto_seed_if_empty(test_db, count=4, day="today")
    assert len(tokens) == 4
    assert tokens[0].label == "Demo Patient 1"
    assert tokens[0].status == "in_consult"
    assert tokens[1].status == "waiting"
    assert tokens[2].status == "waiting"
    assert tokens[3].status == "waiting"

    # Queue query reflects 4 tokens
    queue_today = list_queue(test_db, target_date_str="today")
    assert len(queue_today) == 4


def test_auto_seed_if_empty_does_not_overwrite_existing_queue(test_db):
    """If tokens already exist for the day, auto_seed_if_empty does nothing."""
    # Create an initial token
    token = Token(
        number=101,
        date=list_queue(test_db, "today") and "today" or "2026-11-06",
        label="Real Patient",
        language="te-IN",
        status="waiting",
    )
    test_db.add(token)
    test_db.commit()

    # Call auto_seed_if_empty
    result = auto_seed_if_empty(test_db, count=4, day="2026-11-06")
    assert len(result) == 0

    # Ensure still only 1 token
    queue = list_queue(test_db, target_date_str="2026-11-06")
    assert len(queue) == 1
    assert queue[0].label == "Real Patient"


def test_config_port_and_autoseed_defaults():
    """Verify settings attributes for PORT and DEMO_AUTOSEED exist."""
    assert hasattr(Settings, "PORT")
    assert hasattr(Settings, "DEMO_AUTOSEED")


def test_smoke_deployed_ws_url_conversion():
    """Verify conversion of http(s) URLs to ws(s) URLs."""
    assert smoke.get_ws_url("http://localhost:8000") == "ws://localhost:8000/ws/queue"
    assert smoke.get_ws_url("https://voicequeue.onrender.com") == "wss://voicequeue.onrender.com/ws/queue"
    assert smoke.get_ws_url("https://api.clinic.com/api/") == "wss://api.clinic.com/ws/queue"


def test_smoke_deployed_mock_client():
    """Verify smoke test helper methods with a mock HTTP client."""
    class DummyResponse:
        def __init__(self, status_code, json_data=None, text=""):
            self.status_code = status_code
            self._json = json_data or {}
            self.text = text

        def json(self):
            return self._json

    class DummyClient:
        def __init__(self, responses):
            self.responses = responses

        def get(self, url, **kwargs):
            return self.responses.get(url, DummyResponse(404, text="Not Found"))

    client = DummyClient({
        "http://test-backend/health": DummyResponse(200, {"status": "ok"}),
        "http://test-backend/queue": DummyResponse(200, {"queue": [{"id": 1}]}),
        "http://test-frontend": DummyResponse(200, text="<!DOCTYPE html><html><div id='root'></div></html>"),
    })

    assert smoke.check_health(client, "http://test-backend", timeout=5.0) is True
    assert smoke.check_queue(client, "http://test-backend", timeout=5.0) is True
    assert smoke.check_frontend(client, "http://test-frontend", timeout=5.0) is True

    # Negative checks
    bad_client = DummyClient({})
    assert smoke.check_health(bad_client, "http://test-backend", timeout=5.0) is False
    assert smoke.check_queue(bad_client, "http://test-backend", timeout=5.0) is False
    assert smoke.check_frontend(bad_client, "http://test-frontend", timeout=5.0) is False


def test_dockerfile_and_deployment_configs_exist():
    """Verify that required deployment config files exist in the repository."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    dockerfile = repo_root / "Dockerfile"
    render_yaml = repo_root / "render.yaml"
    frontend_vercel = repo_root / "frontend" / "vercel.json"

    assert dockerfile.exists(), "Dockerfile must exist at repository root"
    content = dockerfile.read_text(encoding="utf-8")
    assert "FROM python:3.11-slim" in content
    assert "ffmpeg" in content
    assert "PORT" in content
    assert "/health" in content

    assert render_yaml.exists(), "render.yaml must exist at repository root"
    render_content = render_yaml.read_text(encoding="utf-8")
    assert "/health" in render_content

    assert frontend_vercel.exists(), "frontend/vercel.json must exist"
    vercel_content = frontend_vercel.read_text(encoding="utf-8")
    assert "npm run build" in vercel_content
    assert "rewrites" in vercel_content
