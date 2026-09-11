"""
Generic decision engine: runs every agent in an industry against one
entity, caches the result in Couchbase (app/context_cache.py), and narrates
each agent's already-computed facts through AOM (app/aom_gateway.py) —
the same "facts stay deterministic, only the phrasing is the model's"
split the reference app's agentNarration.js uses. This one module is what
every industry's two flagship agents run through.
"""
import json
import time
from typing import Any, Dict, List

from app import aom_gateway, context_cache
from app.industries.base import Industry


def _narration_prompt(industry: Industry, agent_name: str, decision, entity: dict) -> str:
    facts = {
        "entity": {k: v for k, v in entity.items() if k not in ("id",)},
        "recommendation": decision.recommendation,
        "impact": f"{decision.impact_label}: {decision.impact_value}",
        "confidence": decision.confidence,
        **decision.facts,
    }
    return (
        f"You are writing a one-to-two sentence explanation for a {industry.entity_label.lower()} "
        f"reviewer, from the '{agent_name}' agent in a {industry.name} operations app. "
        f"Use ONLY the facts given below — never invent a name, number, or detail not present here. "
        f"Be concise and concrete.\n\nFacts (JSON): {json.dumps(facts, default=str)}\n\n"
        f"Deterministic summary to phrase more naturally: {decision.fallback_rationale}"
    )


def decide_for_entity(industry: Industry, entity_id: str, session_id: str = "") -> Dict[str, Any]:
    entity = industry.find_entity(entity_id)
    if entity is None:
        raise KeyError(f"No such {industry.entity_label.lower()}: {entity_id}")

    def compute() -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        with aom_gateway.run(name=f"{industry.id}:{entity_id}", session_id=session_id):
            for agent in industry.agents:
                decision = agent.decide(entity, industry.seed_entities)

                cross_check = None
                if agent.mcp_tool_query is not None:
                    cross_check = aom_gateway.discover_and_invoke(
                        agent.mcp_tool_query(entity), {"entity_id": entity_id}, session_id=session_id
                    )

                prompt = _narration_prompt(industry, agent.name, decision, entity)
                narration = aom_gateway.narrate(prompt, namespace=f"aidp-{industry.id}", session_id=session_id)
                rationale_text = narration["text"] or decision.fallback_rationale
                rationale_source = "aom" if narration["text"] else "fallback"

                results.append(
                    {
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "recommendation": decision.recommendation,
                        "confidence": decision.confidence,
                        "impact_label": decision.impact_label,
                        "impact_value": decision.impact_value,
                        "severity": decision.severity,
                        "facts": decision.facts,
                        "rationale": rationale_text,
                        "rationale_source": rationale_source,
                        "cache_status_llm": narration.get("cache_status"),
                        "mcp_cross_check": cross_check,
                    }
                )
        return {"entity_id": entity_id, "agents": results, "computed_at": time.time()}

    return context_cache.get_or_compute(industry.id, entity_id, compute)
