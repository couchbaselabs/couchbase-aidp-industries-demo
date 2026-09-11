"""
The shared shape every industry module plugs into. One dashboard, one
detail drawer, one copilot, one context-cache pattern (see
app/decisions.py, app/copilot.py, frontend/public/app.js) is implemented
once and re-skinned per industry entirely from the data in these
dataclasses — that leverage is what makes ten verticals tractable in one
build instead of ten bespoke apps.

Each industry implements exactly two "flagship" agents end-to-end (real
seed data, real rule-based decision logic, real AOM narration + MCP
cross-check) — the rest of that industry's brief use-case list is named
in `roadmap` and surfaced in the UI's AI Architecture page, the same
honest "built vs. documented" split the reference Procurement Command
Center app used for its wider 56-rule catalog.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class KPI:
    id: str
    label: str
    compute: Callable[[List[dict]], Any]
    format: str = "number"  # "number" | "currency" | "percent" | "text"


@dataclass
class AgentDecision:
    """What one agent's `decide()` returns for one entity."""
    recommendation: str
    fallback_rationale: str
    confidence: float  # 0..1
    impact_label: str
    impact_value: str
    facts: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"  # "info" | "positive" | "warning" | "critical"


@dataclass
class Agent:
    id: str
    name: str
    description: str
    decide: Callable[[dict, List[dict]], AgentDecision]
    # A natural-language query used to `discover()` + `invoke()` a real MCP
    # tool through AOM as a cross-check before narration — None if this
    # agent doesn't do a live tool cross-check.
    mcp_tool_query: Optional[Callable[[dict], str]] = None


@dataclass
class CopilotAction:
    id: str
    label: str
    build_facts: Callable[[Optional[dict], List[dict]], str]
    mcp_tool_query: Optional[Callable[[Optional[dict]], str]] = None


@dataclass
class Industry:
    id: str
    name: str
    tagline: str
    icon: str
    examples: List[str]
    entity_label: str
    entity_label_plural: str
    entity_title_field: str
    entity_subtitle_field: str
    kpis: List[KPI]
    agents: List[Agent]
    copilot_actions: List[CopilotAction]
    mcp_namespace: str
    seed_entities: List[dict]
    roadmap: List[str]
    color: str

    def find_entity(self, entity_id: str) -> Optional[dict]:
        return next((e for e in self.seed_entities if e["id"] == entity_id), None)
