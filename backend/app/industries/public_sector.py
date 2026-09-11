"""Public Sector & Education — university research labs (e.g. Northwestern), public agency systems."""
from app.industries.base import Agent, AgentDecision, CopilotAction, Industry, KPI
from app.industries.utils import count_where, top_by

SEED_CASES = [
    {"id": "CASE-3101", "citizen_name": "R. Almeida", "service_type": "Benefits renewal", "days_open": 21, "priority": "standard", "identity_verified": True},
    {"id": "CASE-3102", "citizen_name": "J. Whitfield", "service_type": "Permit application", "days_open": 4, "priority": "standard", "identity_verified": True},
    {"id": "CASE-3103", "citizen_name": "S. Okonkwo", "service_type": "Records request", "days_open": 45, "priority": "high", "identity_verified": False},
    {"id": "CASE-3104", "citizen_name": "T. Nakamura", "service_type": "Benefits renewal", "days_open": 2, "priority": "standard", "identity_verified": True},
    {"id": "CASE-3105", "citizen_name": "M. Kowalski", "service_type": "Research data access request", "days_open": 60, "priority": "high", "identity_verified": False},
    {"id": "CASE-3106", "citizen_name": "A. Reyes", "service_type": "Permit application", "days_open": 12, "priority": "standard", "identity_verified": True},
    {"id": "CASE-3107", "citizen_name": "D. Larsen", "service_type": "Records request", "days_open": 8, "priority": "standard", "identity_verified": True},
    {"id": "CASE-3108", "citizen_name": "P. Duncan", "service_type": "Benefits renewal", "days_open": 33, "priority": "high", "identity_verified": False},
]

_SLA_DAYS = {"Benefits renewal": 30, "Permit application": 15, "Records request": 20, "Research data access request": 45}


def _routing_agent(entity: dict, all_entities: list) -> AgentDecision:
    sla = _SLA_DAYS.get(entity["service_type"], 30)
    over = entity["days_open"] - sla
    if over > 0:
        rec, sev = "Escalate to a senior caseworker — SLA breached", "critical"
        fallback = f"{entity['id']} ({entity['service_type']}) is {over} days past its {sla}-day SLA — recommend escalation."
        confidence = 0.9
    elif entity["days_open"] >= sla * 0.75:
        rec, sev = "Route to the front of the standard queue", "warning"
        fallback = f"{entity['id']} is at {entity['days_open']} of {sla} SLA days — approaching the deadline."
        confidence = 0.75
    else:
        rec, sev = "On track — standard queue", "positive"
        fallback = f"{entity['id']} is at {entity['days_open']} of {sla} SLA days — on track."
        confidence = 0.8
    return AgentDecision(rec, fallback, confidence, "Days open / SLA", f"{entity['days_open']}/{sla}", {"days_open": entity["days_open"], "sla_days": sla, "service_type": entity["service_type"]}, sev)


def _identity_agent(entity: dict, all_entities: list) -> AgentDecision:
    if not entity["identity_verified"]:
        rec, sev = "Route to identity re-verification before further processing", "critical"
        fallback = f"{entity['id']} for {entity['citizen_name']} has not completed identity verification — required before this case can proceed."
        confidence = 0.93
    else:
        rec, sev = "Identity verified — no action", "positive"
        fallback = f"{entity['id']} for {entity['citizen_name']} has a verified identity on file."
        confidence = 0.85
    return AgentDecision(rec, fallback, confidence, "Identity verified", "Yes" if entity["identity_verified"] else "No", {"identity_verified": entity["identity_verified"]}, sev)


INDUSTRY = Industry(
    id="public_sector",
    name="Public Sector & Education",
    tagline="Citizen case routing and identity verification on a governed AI data plane.",
    icon="🏛️",
    examples=["university research labs (e.g. Northwestern)", "public agency systems"],
    entity_label="Case",
    entity_label_plural="Cases",
    entity_title_field="id",
    entity_subtitle_field="citizen_name",
    kpis=[
        KPI("open_cases", "Open Cases", lambda es: len(es)),
        KPI("sla_risk", "SLA At-Risk / Breached", lambda es: count_where(es, lambda e: e["days_open"] >= _SLA_DAYS.get(e["service_type"], 30) * 0.75)),
        KPI("unverified", "Pending Identity Verification", lambda es: count_where(es, lambda e: not e["identity_verified"])),
        KPI("high_priority", "High-Priority Cases", lambda es: count_where(es, lambda e: e["priority"] == "high")),
    ],
    agents=[
        Agent("case-routing", "Case Routing Agent", "Flags SLA risk and recommends the right queue/escalation.", _routing_agent, lambda e: f"route service request {e['id']}"),
        Agent("identity-verification", "Identity Verification Agent", "Flags cases needing identity re-verification before processing.", _identity_agent, lambda e: f"verify identity for {e['citizen_name']}"),
    ],
    copilot_actions=[
        CopilotAction("priority", "My priority", lambda e, es: f"Most at-risk case: {top_by(es, lambda x: x['days_open'] - _SLA_DAYS.get(x['service_type'], 30))['id']}."),
        CopilotAction("verification-status", "Verification status", lambda e, es: f"{e['id']} identity verified: {e['identity_verified']}." if e else "Select a case first.", lambda e: f"verify identity for {e['citizen_name']}" if e else "verify identity"),
        CopilotAction("case-lookup", "Case lookup", lambda e, es: f"{e['id']}: {e['service_type']}, open {e['days_open']} days, priority {e['priority']}." if e else "Select a case first."),
    ],
    mcp_namespace="public_sector",
    seed_entities=SEED_CASES,
    roadmap=[
        "Large-scale research data processing — bulk research-dataset workflows aren't modeled here.",
        "Edge-ready government applications — offline/edge deployment isn't demonstrated by this stack.",
        "Broader citizen engagement portal — only case routing and identity checks are implemented.",
    ],
    color="#4338ca",
)
