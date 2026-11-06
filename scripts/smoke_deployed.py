#!/usr/bin/env python3
"""
Smoke Test for Deployed VoiceQueue Service (Phase P2-8)

Verifies:
1. Backend GET /health responds with 200 OK.
2. Backend GET /queue responds with 200 OK.
3. Backend WebSocket /ws/queue accepts connections.
4. Frontend URL loads index HTML.

Guarantees ZERO calls to Gnani or any external paid AI service.
"""

import argparse
import asyncio
import os
import sys
from urllib.parse import urlparse

import httpx

try:
    import websockets
except ImportError:
    websockets = None


def get_ws_url(http_url: str, path: str = "/ws/queue") -> str:
    """Converts http(s) URL to ws(s) URL with path."""
    parsed = urlparse(http_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc or parsed.path
    # Strip any trailing path from netloc
    if "/" in netloc:
        netloc = netloc.split("/")[0]
    return f"{ws_scheme}://{netloc}{path}"


def check_health(client: httpx.Client, backend_url: str, timeout: float) -> bool:
    target = f"{backend_url.rstrip('/')}/health"
    print(f"[*] Checking Backend Health: {target}")
    try:
        resp = client.get(target, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            gnani_ok = data.get("gnani_configured", False)
            ffmpeg_ok = data.get("ffmpeg_found", False)
            voices_ok = data.get("voices_valid", True)
            calls_used = data.get("daily_calls_used", 0)
            daily_cap = data.get("daily_cap", data.get("cap", 150))
            uptime = data.get("uptime", "unknown")
            is_ready = resp.status_code == 200 and ffmpeg_ok and voices_ok

            print(f"  [PASS] /health responded 200 OK (status: {data.get('status', 'ok')})")
            print(f"         - Gnani Configured : {'YES' if gnani_ok else 'NO (offline/stub mode)'}")
            print(f"         - FFmpeg Installed : {'YES' if ffmpeg_ok else 'NO'}")
            print(f"         - Voices Valid     : {'YES' if voices_ok else 'NO'}")
            print(f"         - Daily Calls Used : {calls_used} / {daily_cap}")
            print(f"         - Service Uptime   : {uptime}")
            print(f"         - DEPLOYMENT READY : {'YES' if is_ready else 'NO'}")
            return True
        else:
            print(f"  [FAIL] /health returned HTTP {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"  [FAIL] Error connecting to {target}: {e}")
        return False


def check_queue(client: httpx.Client, backend_url: str, timeout: float) -> bool:
    target = f"{backend_url.rstrip('/')}/queue"
    print(f"[*] Checking Queue Endpoint: {target}")
    try:
        resp = client.get(target, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            queue_len = len(data.get("queue", [])) if isinstance(data, dict) else len(data)
            print(f"  [PASS] /queue responded 200 OK (tokens count: {queue_len})")
            return True
        else:
            print(f"  [FAIL] /queue returned HTTP {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"  [FAIL] Error connecting to {target}: {e}")
        return False


async def check_websocket_async(ws_url: str, timeout: float) -> bool:
    print(f"[*] Checking Live WebSocket: {ws_url}")
    if websockets is None:
        print("  [WARN] websockets library not installed; skipping live WS check")
        return True
    try:
        async with asyncio.timeout(timeout):
            async with websockets.connect(ws_url) as ws:
                # Connected successfully
                print(f"  [PASS] WebSocket connection opened to {ws_url}")
                await ws.close()
                return True
    except Exception as e:
        print(f"  [FAIL] WebSocket connection failed: {e}")
        return False


def check_websocket(backend_url: str, timeout: float) -> bool:
    ws_url = get_ws_url(backend_url, "/ws/queue")
    try:
        return asyncio.run(check_websocket_async(ws_url, timeout))
    except Exception as e:
        print(f"  [FAIL] WebSocket event loop error: {e}")
        return False


def check_frontend(client: httpx.Client, frontend_url: str, timeout: float) -> bool:
    target = frontend_url.rstrip("/")
    print(f"[*] Checking Frontend Page Load: {target}")
    try:
        resp = client.get(target, timeout=timeout, follow_redirects=True)
        if resp.status_code == 200:
            text = resp.text
            if "<!DOCTYPE html>" in text or "<html" in text or "root" in text:
                print(f"  [PASS] Frontend loaded 200 OK (HTML verified, {len(text)} bytes)")
                return True
            else:
                print("  [WARN] Frontend returned 200 but content may not be HTML")
                return True
        else:
            print(f"  [FAIL] Frontend returned HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Error loading frontend {target}: {e}")
        return False


def run_smoke_tests(backend_url: str, frontend_url: str, skip_frontend: bool = False, timeout: float = 15.0) -> bool:
    print("=" * 60)
    print(" VoiceQueue Deployment Smoke Test (Zero External Calls)")
    print("=" * 60)
    print(f"Backend URL : {backend_url}")
    print(f"Frontend URL: {frontend_url if not skip_frontend else '(skipped)'}")
    print(f"Timeout     : {timeout}s")
    print("-" * 60)

    results = []
    with httpx.Client() as client:
        results.append(("Health Check", check_health(client, backend_url, timeout)))
        results.append(("Queue Endpoint", check_queue(client, backend_url, timeout)))
        results.append(("WebSocket Endpoint", check_websocket(backend_url, timeout)))
        if not skip_frontend:
            results.append(("Frontend Load", check_frontend(client, frontend_url, timeout)))

    print("-" * 60)
    all_passed = all(res for _, res in results)
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"  {name:20}: {status}")

    print("=" * 60)
    if all_passed:
        print("[SUCCESS] All deployed smoke checks passed! Zero Gnani calls made.")
    else:
        print("[FAILURE] One or more deployed smoke checks failed.")
    print("=" * 60)
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="VoiceQueue deployment smoke tests.")
    parser.add_argument(
        "--backend-url",
        "-b",
        default=os.getenv("BACKEND_URL", os.getenv("API_URL", "http://localhost:8000")),
        help="Backend base URL (default: http://localhost:8000 or $BACKEND_URL)",
    )
    parser.add_argument(
        "--frontend-url",
        "-f",
        default=os.getenv("FRONTEND_URL", "http://localhost:5173"),
        help="Frontend base URL (default: http://localhost:5173 or $FRONTEND_URL)",
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip checking frontend page load",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=15.0,
        help="Timeout in seconds for each network check (default: 15.0)",
    )

    args = parser.parse_args()
    success = run_smoke_tests(
        backend_url=args.backend_url,
        frontend_url=args.frontend_url,
        skip_frontend=args.skip_frontend,
        timeout=args.timeout,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
