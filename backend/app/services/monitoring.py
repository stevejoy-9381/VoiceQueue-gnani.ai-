"""Structured JSON Logging & System Monitoring Service (P3-3).

Guarantees:
- Structured JSON logs for every request: request_id, route, status, duration_ms, error_code
- Absolute privacy: NEVER logs secrets, API keys, audio bytes, or unmasked transcripts
- Real-time error counter by error_code
- System uptime and health tracking
"""

from collections import Counter, deque
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, Dict, Optional
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.services.privacy import mask_text

APP_START_TIME: float = time.time()

# In-memory error counter for dev mode (?dev=1) and monitoring
_ERROR_COUNTS: Counter = Counter()

# In-memory circular buffer of the last 50 structured logs for verification / tests
_RECENT_LOGS: deque = deque(maxlen=50)

logger = logging.getLogger("voicequeue.monitoring")


def get_uptime_seconds() -> float:
    """Returns application uptime in seconds."""
    return round(time.time() - APP_START_TIME, 1)


def get_uptime_str() -> str:
    """Returns application uptime as a human-readable string."""
    return f"{get_uptime_seconds()}s"


def record_error(error_code: Optional[str]) -> None:
    """Increments the error counter for a specific error_code."""
    if error_code and str(error_code).strip():
        _ERROR_COUNTS[str(error_code).strip()] += 1


def get_error_counts() -> Dict[str, int]:
    """Returns a dictionary of all recorded error counts by error_code."""
    return dict(_ERROR_COUNTS)


def reset_error_counts() -> None:
    """Clears the error counters (used in tests)."""
    _ERROR_COUNTS.clear()


def get_recent_logs() -> list[Dict[str, Any]]:
    """Returns the most recent structured JSON logs (last 50)."""
    return list(_RECENT_LOGS)


def clear_recent_logs() -> None:
    """Clears the in-memory recent logs buffer."""
    _RECENT_LOGS.clear()


def build_structured_log(
    request_id: str,
    method: str,
    route: str,
    status_code: int,
    duration_ms: float,
    error_code: Optional[str] = None,
    client_ip: Optional[str] = None,
    masked_detail: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Builds a privacy-safe, structured JSON log object.
    Never includes secrets, API keys, raw audio bytes, or unmasked transcripts.
    """
    safe_masked = mask_text(masked_detail) if masked_detail else None

    # Sanitize route to avoid leaking sensitive query params
    clean_route = route.split("?")[0] if route else "/"

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "method": method,
        "route": clean_route,
        "status": status_code,
        "duration_ms": duration_ms,
        "error_code": error_code,
    }

    if client_ip:
        log_entry["client_ip"] = client_ip
    if safe_masked:
        log_entry["detail"] = safe_masked

    return log_entry


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware capturing request_id, route, status, duration, and error_code.
    Emits structured single-line JSON logs for every HTTP request.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract or generate request_id
        req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:10]}"
        request.state.request_id = req_id
        request.state.error_code = None

        start_time = time.perf_counter()
        status_code = 500
        error_code = None

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            status_code = 500
            error_code = getattr(exc, "error_code", "internal_server_error")
            request.state.error_code = error_code
            record_error(error_code)
            raise exc from None
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

            # Check if error_code was set in request state or response header
            resp_err = response.headers.get("X-Error-Code") if "response" in locals() else None
            state_err = getattr(request.state, "error_code", None)
            error_code = state_err or resp_err

            # Fallback error code for non-2xx status codes
            if not error_code and status_code >= 400:
                if status_code == 404:
                    error_code = "not_found"
                elif status_code == 401:
                    error_code = "unauthorized"
                elif status_code == 403:
                    error_code = "forbidden"
                elif status_code == 429:
                    error_code = "rate_limit"
                else:
                    error_code = f"http_{status_code}"

            if error_code:
                record_error(error_code)

            # Extract client IP safely
            client_ip = request.client.host if request.client else None

            log_entry = build_structured_log(
                request_id=req_id,
                method=request.method,
                route=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                error_code=error_code,
                client_ip=client_ip,
            )

            # Store in circular buffer
            _RECENT_LOGS.append(log_entry)

            # Print single-line structured JSON log
            log_line = json.dumps(log_entry)
            print(log_line)

            if "response" in locals():
                response.headers["X-Request-ID"] = req_id
                if error_code:
                    response.headers["X-Error-Code"] = str(error_code)

        return response

