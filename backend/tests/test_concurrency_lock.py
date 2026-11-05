"""Tests for the one-request-at-a-time lock guarding Gnani AI calls."""

import concurrent.futures
import threading
import time
import pytest
from backend.app.services import gnani


def test_one_request_at_a_time_lock():
    """
    Fires 5 simultaneous requests through _execute_with_lock_and_retry with a slow function
    and confirms the critical section is never executed by more than one thread concurrently.
    """
    active_count = 0
    max_active_seen = 0
    counter_lock = threading.Lock()
    total_calls = 0

    class MockResponse:
        status_code = 200
        is_success = True
        text = "ok"

    def slow_task():
        nonlocal active_count, max_active_seen, total_calls
        with counter_lock:
            active_count += 1
            if active_count > max_active_seen:
                max_active_seen = active_count

        # Simulate slow network/model inference
        time.sleep(0.04)

        with counter_lock:
            active_count -= 1
            total_calls += 1

        return MockResponse()

    # Launch 5 parallel threads simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(gnani._execute_with_lock_and_retry, slow_task) for _ in range(5)]
        results = [f.result() for f in futures]

    assert len(results) == 5
    assert total_calls == 5
    # Strict assertion: Lock must ensure max concurrency is NEVER greater than 1
    assert max_active_seen == 1, f"Lock violated! Max concurrent executions observed: {max_active_seen}"

