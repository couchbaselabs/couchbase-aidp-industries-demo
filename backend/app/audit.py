"""
Operator accept/reject audit log and per-agent accuracy rollup — the
"Trust Layer" pattern from the reference app (buyer-behavior/agent-accuracy
logging), generalized across industries. An accept or reject on any
agent's recommendation is logged here; accuracy is accepts / (accepts +
rejects) per agent, computed live from this log rather than stored
separately, so it can never drift from what was actually recorded.
"""
import time
import uuid
from typing import Any, Dict, List

from app.couchbase_client import couchbase


def record_action(industry_id: str, entity_id: str, agent_id: str, action: str, operator: str = "demo-operator") -> None:
    if action not in ("accept", "reject"):
        raise ValueError("action must be 'accept' or 'reject'")
    key = f"audit::{industry_id}::{uuid.uuid4().hex}"
    couchbase.upsert(
        key,
        {
            "type": "audit_action",
            "industry": industry_id,
            "entity_id": entity_id,
            "agent_id": agent_id,
            "action": action,
            "operator": operator,
            "at": time.time(),
        },
    )


def agent_accuracy(industry_id: str) -> List[Dict[str, Any]]:
    rows = couchbase.select_by_type_and_industry("audit_action", industry_id)
    by_agent: Dict[str, Dict[str, int]] = {}
    for row in rows:
        agent_id = row.get("agent_id", "unknown")
        counts = by_agent.setdefault(agent_id, {"accept": 0, "reject": 0})
        if row.get("action") in counts:
            counts[row["action"]] += 1
    out = []
    for agent_id, counts in by_agent.items():
        total = counts["accept"] + counts["reject"]
        accuracy = round(counts["accept"] / total * 100, 1) if total else None
        out.append({"agent_id": agent_id, **counts, "total": total, "accuracy_pct": accuracy})
    return out
