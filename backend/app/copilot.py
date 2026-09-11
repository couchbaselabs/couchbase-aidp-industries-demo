"""
Generic, industry-agnostic AI copilot: quick-action chips plus a freeform
fallback, both grounded in real rule-based facts about the entity in
scope and then phrased by AOM's cached completion endpoint — the same
"facts stay deterministic, only the phrasing is the model's" split
app/decisions.py uses for agent rationales, generalized from the
reference app's copilot.js.
"""
import json
from typing import Any, Dict, Optional

from app import aom_gateway
from app.industries.base import Industry


def list_actions(industry: Industry) -> list:
    return [{"id": a.id, "label": a.label} for a in industry.copilot_actions]


def chat(industry: Industry, action_id: Optional[str], message: Optional[str], entity_id: Optional[str], session_id: str) -> Dict[str, Any]:
    entity = industry.find_entity(entity_id) if entity_id else None

    action = next((a for a in industry.copilot_actions if a.id == action_id), None) if action_id else None

    if action is not None:
        facts_text = action.build_facts(entity, industry.seed_entities)
        cross_check = None
        if action.mcp_tool_query is not None:
            cross_check = aom_gateway.discover_and_invoke(action.mcp_tool_query(entity), session_id=session_id)
            if cross_check.get("ok"):
                facts_text += f"\n\nLive cross-check via AOM/MCP: {json.dumps(cross_check['result'], default=str)}"
        prompt = (
            f"You are the {industry.name} operations copilot. A user tapped the '{action.label}' quick "
            f"action{' for ' + industry.entity_label.lower() + ' ' + entity_id if entity_id else ''}. "
            f"Answer in 2-4 concise sentences, using ONLY the facts below — never invent a number or name "
            f"not present here.\n\nFacts:\n{facts_text}"
        )
        fallback_text = facts_text
    elif message:
        prompt = (
            f"You are the {industry.name} operations copilot embedded in a Couchbase AI Data Plane demo app. "
            f"Answer the user's question helpfully and concisely (2-4 sentences). If it's about this app's own "
            f"architecture, you may describe: a shared Couchbase cluster acting as the operational store and "
            f"context cache, agent decisions cached per entity, and every LLM/MCP call routed through the "
            f"Couchbase Agent Operations Manager for RBAC, auditing, and response caching.\n\n"
            f"User question: {message}"
        )
        fallback_text = (
            "I can answer that once a live model is reachable through the Couchbase Agent Operations "
            "Manager — for now, try one of the quick actions above for a fact-grounded answer."
        )
        cross_check = None
    else:
        return {"reply": "Ask a question or pick a quick action.", "source": "fallback", "mcp_cross_check": None}

    narration = aom_gateway.narrate(prompt, namespace=f"aidp-{industry.id}-copilot", session_id=session_id)
    reply = narration["text"] or fallback_text
    aom_gateway.add_memory(
        session_id or "anonymous",
        f"Asked the {industry.name} copilot: {action.label if action else message}",
        session_id=session_id,
    )
    return {
        "reply": reply,
        "source": "aom" if narration["text"] else "fallback",
        "cache_status": narration.get("cache_status"),
        "mcp_cross_check": cross_check,
    }
