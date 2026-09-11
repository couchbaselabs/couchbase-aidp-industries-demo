"""Energy & Utilities — Pacific Gas and Electric Company (PG&E)."""
from app.industries.base import Agent, AgentDecision, CopilotAction, Industry, KPI
from app.industries.utils import count_where, top_by

SEED_FEEDERS = [
    {"id": "FDR-4401", "region": "North Valley", "load_mw": 38.2, "capacity_mw": 42.0, "last_incident_days_ago": 210, "weather_flag": "none"},
    {"id": "FDR-4402", "region": "Coastal Ridge", "load_mw": 51.0, "capacity_mw": 55.0, "last_incident_days_ago": 4, "weather_flag": "high-wind advisory"},
    {"id": "FDR-4403", "region": "Foothill District", "load_mw": 22.5, "capacity_mw": 40.0, "last_incident_days_ago": 365, "weather_flag": "none"},
    {"id": "FDR-4404", "region": "Downtown Metro", "load_mw": 61.8, "capacity_mw": 65.0, "last_incident_days_ago": 30, "weather_flag": "none"},
    {"id": "FDR-4405", "region": "Coastal Ridge", "load_mw": 33.0, "capacity_mw": 50.0, "last_incident_days_ago": 4, "weather_flag": "high-wind advisory"},
    {"id": "FDR-4406", "region": "Lakeside", "load_mw": 44.9, "capacity_mw": 46.0, "last_incident_days_ago": 90, "weather_flag": "none"},
    {"id": "FDR-4407", "region": "North Valley", "load_mw": 19.0, "capacity_mw": 38.0, "last_incident_days_ago": 300, "weather_flag": "none"},
    {"id": "FDR-4408", "region": "Downtown Metro", "load_mw": 58.0, "capacity_mw": 60.0, "last_incident_days_ago": 2, "weather_flag": "heat advisory"},
]


def _grid_load_agent(entity: dict, all_entities: list) -> AgentDecision:
    pct = entity["load_mw"] / entity["capacity_mw"] * 100
    if pct >= 95:
        rec, sev = "Initiate load-shedding protocol for this feeder", "critical"
        fallback = f"{entity['id']} in {entity['region']} is at {pct:.0f}% of capacity — recommend load-shedding."
        confidence = 0.92
    elif pct >= 85:
        rec, sev = "Schedule reinforcement work before peak season", "warning"
        fallback = f"{entity['id']} is at {pct:.0f}% of capacity — above the 85% planning threshold."
        confidence = 0.78
    else:
        rec, sev = "Healthy headroom — no action", "positive"
        fallback = f"{entity['id']} is at {pct:.0f}% of capacity — healthy headroom remains."
        confidence = 0.8
    return AgentDecision(rec, fallback, confidence, "Load / capacity", f"{pct:.0f}%", {"load_mw": entity["load_mw"], "capacity_mw": entity["capacity_mw"]}, sev)


def _outage_risk_agent(entity: dict, all_entities: list) -> AgentDecision:
    score = 0
    reasons = []
    if entity["weather_flag"] != "none":
        score += 45
        reasons.append(entity["weather_flag"])
    if entity["last_incident_days_ago"] <= 14:
        score += 35
        reasons.append(f"incident {entity['last_incident_days_ago']} days ago")
    score = min(score, 90)
    if score >= 50:
        rec, sev = "Pre-position a field crew near this feeder", "critical"
    elif score >= 20:
        rec, sev = "Add to the watch list for this shift", "warning"
    else:
        rec, sev = "Low outage risk — no action", "positive"
    fallback = f"Outage risk {score}/90 in {entity['region']}: {', '.join(reasons) if reasons else 'no notable signals'}."
    return AgentDecision(rec, fallback, min(0.6 + score / 180, 0.95), "Outage risk score", f"{score}/90", {"score": score, "reasons": reasons}, sev)


INDUSTRY = Industry(
    id="energy",
    name="Energy & Utilities",
    tagline="Smart grid load and outage risk telemetry on one AI data plane.",
    icon="⚡",
    examples=["Pacific Gas and Electric Company (PG&E)"],
    entity_label="Feeder",
    entity_label_plural="Feeders",
    entity_title_field="id",
    entity_subtitle_field="region",
    kpis=[
        KPI("feeders", "Feeders Monitored", lambda es: len(es)),
        KPI("near_capacity", "Near-Capacity Feeders", lambda es: count_where(es, lambda e: e["load_mw"] / e["capacity_mw"] >= 0.85)),
        KPI("weather_flags", "Active Weather Advisories", lambda es: count_where(es, lambda e: e["weather_flag"] != "none")),
        KPI("recent_incidents", "Incidents in Last 14 Days", lambda es: count_where(es, lambda e: e["last_incident_days_ago"] <= 14)),
    ],
    agents=[
        Agent("grid-load", "Grid Load Agent", "Flags feeders nearing capacity and recommends load-shedding or reinforcement.", _grid_load_agent, lambda e: f"get grid telemetry for feeder {e['id']}"),
        Agent("outage-risk", "Outage Risk Agent", "Scores outage risk from weather advisories and recent incident history.", _outage_risk_agent, lambda e: f"forecast load for {e['region']}"),
    ],
    copilot_actions=[
        CopilotAction("priority", "My priority", lambda e, es: f"Highest outage risk: {top_by(es, lambda x: (45 if x['weather_flag']!='none' else 0) + (35 if x['last_incident_days_ago']<=14 else 0))['id']}."),
        CopilotAction("dispatch", "Dispatch recommendation", lambda e, es: f"{e['id']} in {e['region']}, weather: {e['weather_flag']}." if e else "Select a feeder first.", lambda e: f"dispatch field team near {e['region']}" if e else "dispatch field team"),
        CopilotAction("load-forecast", "Load forecast", lambda e, es: f"{e['id']} at {e['load_mw']}MW of {e['capacity_mw']}MW capacity." if e else "Select a feeder first."),
    ],
    mcp_namespace="energy",
    seed_entities=SEED_FEEDERS,
    roadmap=[
        "Field team coordination — dispatch/routing logistics beyond a single recommendation aren't modeled here.",
        "Rapid emergency service response applications — this demo scores risk, it doesn't run an incident-response workflow.",
        "Broader smart grid data management — only load and outage-risk scoring are implemented.",
    ],
    color="#ca8a04",
)
