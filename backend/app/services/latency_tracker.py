"""Latency tracker for recording stage times and computing p50/p95 percentiles."""

from collections import deque
import threading
from typing import Any, Dict, List, Optional


class LatencyTracker:
    """Thread-safe ring buffer storing up to `maxlen` requests with percentile computation."""

    def __init__(self, maxlen: int = 50):
        self._maxlen = maxlen
        self._history: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def record(self, stage_times_ms: Dict[str, float]):
        """Records a single request's stage timings dictionary."""
        if not stage_times_ms:
            return
        with self._lock:
            self._history.append(dict(stage_times_ms))

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns median (p50) and 95th percentile (p95) per stage for the last recorded requests.
        """
        with self._lock:
            records = list(self._history)

        count = len(records)
        stages = [
            "convert",
            "clean",
            "quality_gates",
            "stt",
            "intent",
            "queue_action",
            "reply_choice",
            "tts_or_cache",
            "response_build",
            "total",
        ]

        stage_stats = {}
        median_dict = {}
        p95_dict = {}

        if count == 0:
            for s in stages:
                stage_stats[s] = {"median_ms": 0.0, "p95_ms": 0.0, "median": 0.0, "p95": 0.0}
                median_dict[s] = 0.0
                p95_dict[s] = 0.0
            return {
                "count": 0,
                "stages": stage_stats,
                "median": median_dict,
                "p95": p95_dict,
            }

        for s in stages:
            vals = [float(r[s]) for r in records if s in r and r[s] is not None]
            if not vals:
                vals = [0.0]
            vals.sort()
            n = len(vals)

            # Median (50th percentile)
            if n % 2 == 1:
                med = float(vals[n // 2])
            else:
                med = float((vals[n // 2 - 1] + vals[n // 2]) / 2.0)

            # 95th percentile
            p95_idx = max(0, int(round(0.95 * n)) - 1)
            p95 = float(vals[min(p95_idx, n - 1)])

            med_r = round(med, 2)
            p95_r = round(p95, 2)

            stage_stats[s] = {
                "median_ms": med_r,
                "p95_ms": p95_r,
                "median": med_r,
                "p95": p95_r,
            }
            median_dict[s] = med_r
            p95_dict[s] = p95_r

        return {
            "count": count,
            "stages": stage_stats,
            "median": median_dict,
            "p95": p95_dict,
        }

    def clear(self):
        """Clears all recorded latency entries."""
        with self._lock:
            self._history.clear()


latency_tracker = LatencyTracker(maxlen=50)

