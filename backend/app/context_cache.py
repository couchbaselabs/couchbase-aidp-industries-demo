"""
The Couchbase-backed "AI data plane" context cache, generalized across all
ten industries from the pattern in the reference Procurement Command
Center app's `backend/src/services/contextCache.js`.

Every agent decision for one entity (an order, a claim, a booking, a
subscriber ticket — whatever that industry's flagship entity is) is
computed once against that industry's (simulated) system of record, then
cached in Couchbase under `context_cache::<industry>::<entity_id>`. The
first look is a "cache miss" — this simulates the latency of fanning out
to a core system (ERP, ledger, EHR, OSS/BSS, PMS, ...) — and every
subsequent look (a different operator, or a re-opened record) is a
near-instant cache hit. The UI shows which happened on every card, which
is what makes the caching benefit real rather than just asserted.
"""
import time
from typing import Any, Callable, Dict

from app.config import CONTEXT_CACHE_MISS_LATENCY_MS, CONTEXT_CACHE_TTL_SECONDS
from app.couchbase_client import couchbase


def _cache_key(industry: str, entity_id: str) -> str:
    return f"context_cache::{industry}::decision::{entity_id}"


def get_or_compute(industry: str, entity_id: str, compute_fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """Return `{decision, cache: {status, latency_ms}}`. `status` is "hit"
    when a fresh cached decision existed, "miss" when `compute_fn` had to
    run (and its simulated system-of-record latency was paid)."""
    key = _cache_key(industry, entity_id)
    started = time.monotonic()

    cached = couchbase.get(key)
    if cached is not None:
        cached_at = cached.get("cached_at", 0)
        if time.time() - cached_at < CONTEXT_CACHE_TTL_SECONDS:
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            return {"decision": cached["decision"], "cache": {"status": "hit", "latency_ms": latency_ms}}

    # Cache miss: simulate the fan-out to the mocked system(s) of record
    # this industry's agents read from, then compute and cache the result.
    time.sleep(CONTEXT_CACHE_MISS_LATENCY_MS / 1000.0)
    decision = compute_fn()
    couchbase.upsert(
        key,
        {
            "type": "context_cache",
            "industry": industry,
            "entity_id": entity_id,
            "decision": decision,
            "cached_at": time.time(),
        },
    )
    latency_ms = round((time.monotonic() - started) * 1000, 1)
    return {"decision": decision, "cache": {"status": "miss", "latency_ms": latency_ms}}


def invalidate(industry: str, entity_id: str) -> None:
    couchbase.remove(_cache_key(industry, entity_id))
