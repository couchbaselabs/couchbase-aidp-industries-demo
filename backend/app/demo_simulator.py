"""
"Simulate N operators" background demo, generalized from the reference
app's Settings -> Demo panel (backend/src/services/demo.js): repeatedly
runs real decide_for_entity() / copilot chat calls across a small pool of
entities and quick actions for the selected industry, so Couchbase's
context-cache hit rate and AOM's LLM-cache hit rate climb the way they
would under real concurrent usage — nothing about the traffic is faked,
only the "operators" issuing it. Watch it on this app's own Settings ->
Demo panel or directly on AOM's own LLM Caching dashboard.
"""
import random
import threading
import time
from collections import deque
from typing import Deque, Dict, Optional, Tuple

from app import copilot, decisions
from app.industries import get_industry


class DemoSimulator:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._industry_id: Optional[str] = None
        self._recent: Deque[Tuple[float, bool]] = deque(maxlen=500)  # (timestamp, was_hit)
        self._total_calls = 0
        self._started_at: Optional[float] = None

    def start(self, industry_id: str, operators: int = 25, interval_seconds: float = 1.0) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                self.stop()
            self._industry_id = industry_id
            self._recent.clear()
            self._total_calls = 0
            self._started_at = time.time()
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run, args=(industry_id, operators, interval_seconds), daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None

    def status(self) -> Dict:
        running = bool(self._thread and self._thread.is_alive())
        now = time.time()
        window = [hit for ts, hit in self._recent if now - ts <= 60]
        hit_rate = round(100 * sum(window) / len(window), 1) if window else None
        return {
            "running": running,
            "industry_id": self._industry_id,
            "total_calls": self._total_calls,
            "trailing_60s_hit_rate_pct": hit_rate,
            "trailing_60s_sample_size": len(window),
            "started_at": self._started_at,
        }

    def _run(self, industry_id: str, operators: int, interval_seconds: float) -> None:
        industry = get_industry(industry_id)
        entity_pool = [e["id"] for e in industry.seed_entities]
        action_pool = [a.id for a in industry.copilot_actions] or [None]
        session_ids = [f"sim-operator-{i}" for i in range(max(1, operators))]

        while not self._stop.is_set():
            session_id = random.choice(session_ids)
            entity_id = random.choice(entity_pool) if entity_pool else None
            try:
                if entity_id and random.random() < 0.6:
                    result = decisions.decide_for_entity(industry, entity_id, session_id=session_id)
                    was_hit = result["cache"]["status"] == "hit"
                else:
                    action_id = random.choice(action_pool)
                    reply = copilot.chat(industry, action_id, None, entity_id, session_id)
                    was_hit = reply.get("cache_status") in ("hit_exact", "hit_semantic")
                self._total_calls += 1
                self._recent.append((time.time(), bool(was_hit)))
            except Exception:  # noqa: BLE001 - a simulated call failing should never kill the loop
                pass
            self._stop.wait(interval_seconds)


simulator = DemoSimulator()
