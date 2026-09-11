"""
Thin wrapper around the real `aom_sdk.AOMClient` (vendored at
backend/vendor/aom-sdk — see that folder's VENDORED.md) that gives every
caller in this app one resilience posture: if AOM isn't configured, isn't
reachable, or a call fails for any reason, every helper here returns a
labelled fallback instead of raising — the same "the app works fully with
no AOM running at all" posture the reference Procurement Command Center
app's `aomClient.js` uses. The UI's "via AOM" / "rule-based fallback"
badges read straight off the `source` field these helpers return.

Every real call this module makes — `complete()` for LLM narration,
`discover()` + `invoke()` for MCP tool cross-checks, `add_memory()` /
`search_memory()` for the copilot's cross-session recall — shows up in
AOM's own dashboards (Traces, LLM Caching, Agent Tool Audit, Dashboard
"Live topology") exactly as it would for any other agent calling through
the SDK, which is the whole point of routing through AOM instead of
calling a model or a tool directly.
"""
import logging
from typing import Any, Dict, List, Optional

from app.config import (
    AOM_AGENT_ID,
    AOM_API_KEY,
    AOM_BASE_URL,
    AOM_MODEL,
    AOM_PROVIDER,
    AOM_REQUEST_TIMEOUT_SECONDS,
    AOM_VERIFY_SSL,
)

logger = logging.getLogger("aidp.aom")

try:
    from aom_sdk import (
        AOMClient,
        AOMAuthenticationError,
        AOMAuthorizationError,
        AOMConnectionError,
        AOMError,
        AOMGuardrailError,
        AOMNotFoundError,
        AOMRateLimitError,
    )

    _SDK_IMPORT_ERROR: Optional[Exception] = None
except Exception as exc:  # noqa: BLE001 - the app must still boot without the SDK installed
    AOMClient = None  # type: ignore[assignment]
    _SDK_IMPORT_ERROR = exc


def _client(session_id: Optional[str] = None) -> Optional["AOMClient"]:
    if AOMClient is None or not AOM_API_KEY:
        return None
    return AOMClient(
        base_url=AOM_BASE_URL,
        api_key=AOM_API_KEY,
        verify=AOM_VERIFY_SSL,
        agent_id=AOM_AGENT_ID,
        session_id=session_id,
        timeout=AOM_REQUEST_TIMEOUT_SECONDS,
    )


def sdk_available() -> bool:
    return AOMClient is not None


def status() -> Dict[str, Any]:
    """A small self-check used by /api/health and the frontend's connection
    badge — never raises."""
    if AOMClient is None:
        return {"configured": False, "reachable": False, "detail": f"aom_sdk not importable: {_SDK_IMPORT_ERROR}"}
    if not AOM_API_KEY:
        return {"configured": False, "reachable": False, "detail": "AOM_API_KEY not set"}
    client = _client()
    try:
        health = client.health()
        return {"configured": True, "reachable": True, "detail": health.get("status", "ok"), "base_url": AOM_BASE_URL}
    except Exception as exc:  # noqa: BLE001
        return {"configured": True, "reachable": False, "detail": str(exc), "base_url": AOM_BASE_URL}


def narrate(prompt: str, *, namespace: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Route a narration prompt through AOM's cached `/v1/llm/complete`.
    Returns {"text", "source": "aom"|"fallback", "cache_status", "model",
    "error"}. Callers always have deterministic fallback text ready and use
    it when `source == "fallback"`."""
    client = _client(session_id=session_id)
    if client is None:
        return {"text": None, "source": "fallback", "error": "AOM not configured"}
    try:
        result = client.complete(
            prompt,
            provider=AOM_PROVIDER or None,
            model=AOM_MODEL or None,
            namespace=namespace,
        )
        return {
            "text": (result.get("response") or "").strip() or None,
            "source": "aom",
            "cache_status": (result.get("cache") or {}).get("status"),
            "model": result.get("model"),
        }
    except Exception as exc:  # noqa: BLE001 - narration must never break the request it's decorating
        logger.warning("AOM complete() failed, falling back to rule-based text: %s", exc)
        return {"text": None, "source": "fallback", "error": str(exc)}


def discover_and_invoke(query: str, arguments: Optional[dict] = None, *, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Best-effort discover+invoke against one of this app's bundled
    industry MCP tool servers, proxied through AOM. Returns
    {"ok", "result"|"error", "tool_id"}. Never raises — a failed or skipped
    lookup just means the caller adds no cross-check note, the same
    fallback posture `narrate()` has."""
    client = _client(session_id=session_id)
    if client is None:
        return {"ok": False, "error": "AOM not configured"}
    try:
        discovered = client.discover(query, top_k=1)
        tools = discovered.get("tools") or []
        if not tools:
            return {"ok": False, "error": f"no tool matched: {query!r}"}
        tool_id = tools[0]["tool_id"]
        result = client.invoke(tool_id, arguments=arguments or {})
        if result.get("status") == "pending_approval":
            return {"ok": False, "error": "tool call is pending human approval", "tool_id": tool_id}
        return {"ok": True, "result": result.get("result"), "tool_id": tool_id, "hijack_warning": result.get("hijack_warning")}
    except Exception as exc:  # noqa: BLE001
        logger.info("AOM discover/invoke skipped (%s): %s", query, exc)
        return {"ok": False, "error": str(exc)}


def add_memory(user_id: str, content: str, *, memory_type: str = "conversational", session_id: Optional[str] = None) -> bool:
    client = _client(session_id=session_id)
    if client is None:
        return False
    try:
        client.add_memory(user_id, content, memory_type=memory_type, session_id=session_id)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.info("AOM add_memory skipped: %s", exc)
        return False


def search_memory(user_id: str, query: str, *, top_k: int = 3) -> List[dict]:
    client = _client()
    if client is None:
        return []
    try:
        return client.search_memory(user_id, query, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        logger.info("AOM search_memory skipped: %s", exc)
        return []


def run(name: str, session_id: Optional[str] = None):
    """Context manager grouping every AOM call inside a request into one
    traced run on AOM's Traces page, when AOM is configured. Yields the
    client (usable for discover/invoke/complete) or None."""
    client = _client(session_id=session_id)
    if client is None:
        return _NullRun()
    return client.run(name=name)


class _NullRun:
    """Stand-in for `AOMClient.run()` when AOM isn't configured, so calling
    code can always use `with aom_gateway.run(...) as run:` uniformly."""

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False
