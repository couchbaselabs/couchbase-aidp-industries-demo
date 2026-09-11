"""Software & IT Services (SaaS) — software development platforms, global IT consulting/SI firms."""
from app.industries.base import Agent, AgentDecision, CopilotAction, Industry, KPI
from app.industries.utils import count_where, top_by

SEED_TENANTS = [
    {"id": "TEN-2201", "tenant_name": "BrightPath Logistics", "plan_tier": "Growth", "active_users": 340, "api_calls_today": 812000, "error_rate_pct": 2.9, "storage_gb": 210, "region": "us-east"},
    {"id": "TEN-2202", "tenant_name": "Kestrel Analytics", "plan_tier": "Starter", "active_users": 18, "api_calls_today": 4100, "error_rate_pct": 0.1, "storage_gb": 6, "region": "eu-west"},
    {"id": "TEN-2203", "tenant_name": "Union Robotics", "plan_tier": "Enterprise", "active_users": 1250, "api_calls_today": 3400000, "error_rate_pct": 4.6, "storage_gb": 890, "region": "us-east"},
    {"id": "TEN-2204", "tenant_name": "Fernwood Legal", "plan_tier": "Growth", "active_users": 95, "api_calls_today": 61000, "error_rate_pct": 0.3, "storage_gb": 44, "region": "us-west"},
    {"id": "TEN-2205", "tenant_name": "Solstice Retailers", "plan_tier": "Enterprise", "active_users": 2100, "api_calls_today": 5100000, "error_rate_pct": 1.1, "storage_gb": 1400, "region": "eu-west"},
    {"id": "TEN-2206", "tenant_name": "Harmony Health IT", "plan_tier": "Starter", "active_users": 12, "api_calls_today": 2200, "error_rate_pct": 0.0, "storage_gb": 3, "region": "us-east"},
    {"id": "TEN-2207", "tenant_name": "Ridgeline Manufacturing", "plan_tier": "Growth", "active_users": 410, "api_calls_today": 990000, "error_rate_pct": 3.8, "storage_gb": 330, "region": "us-west"},
    {"id": "TEN-2208", "tenant_name": "Atlas Media Group", "plan_tier": "Enterprise", "active_users": 640, "api_calls_today": 1800000, "error_rate_pct": 0.6, "storage_gb": 720, "region": "eu-west"},
]


def _tenant_health_agent(entity: dict, all_entities: list) -> AgentDecision:
    rate = entity["error_rate_pct"]
    if rate >= 4.0:
        rec, sev = "Page on-call and scale out this tenant's isolated pool", "critical"
        fallback = f"{entity['tenant_name']} is at a {rate}% API error rate — recommend paging on-call and scaling its pool."
        confidence = 0.92
    elif rate >= 2.0:
        rec, sev = "Add capacity headroom before it trips the alerting threshold", "warning"
        fallback = f"{entity['tenant_name']} is at a {rate}% error rate — above the 2% watch line."
        confidence = 0.78
    else:
        rec, sev = "Healthy — no action", "positive"
        fallback = f"{entity['tenant_name']} is at a {rate}% error rate — within healthy range."
        confidence = 0.85
    return AgentDecision(rec, fallback, confidence, "API error rate", f"{rate}%", {"error_rate_pct": rate, "region": entity["region"]}, sev)


def _cost_agent(entity: dict, all_entities: list) -> AgentDecision:
    calls_per_user = entity["api_calls_today"] / max(entity["active_users"], 1)
    if entity["plan_tier"] == "Starter" and calls_per_user > 500:
        rec, sev = "Recommend upgrading to Growth — usage exceeds Starter's efficient range", "warning"
        fallback = f"{entity['tenant_name']} is on Starter but averaging {calls_per_user:,.0f} calls/user — an upgrade would be more cost-efficient for them."
        confidence = 0.75
    elif entity["plan_tier"] == "Enterprise" and calls_per_user < 500:
        rec, sev = "Flag for a right-sizing conversation at renewal", "info"
        fallback = f"{entity['tenant_name']} is on Enterprise but averaging only {calls_per_user:,.0f} calls/user — worth a right-sizing check at renewal."
        confidence = 0.6
    else:
        rec, sev = "Plan tier matches usage — no action", "positive"
        fallback = f"{entity['tenant_name']}'s {entity['plan_tier']} tier matches its usage pattern."
        confidence = 0.7
    return AgentDecision(rec, fallback, confidence, "Calls per active user", f"{calls_per_user:,.0f}", {"plan_tier": entity["plan_tier"], "calls_per_user": round(calls_per_user)}, sev)


INDUSTRY = Industry(
    id="saas",
    name="Software & IT Services (SaaS)",
    tagline="Multi-tenant health and cost optimization on a shared AI data plane.",
    icon="☁️",
    examples=["software development platforms", "global IT consulting and systems integrators"],
    entity_label="Tenant",
    entity_label_plural="Tenants",
    entity_title_field="id",
    entity_subtitle_field="tenant_name",
    kpis=[
        KPI("tenants", "Tenants Monitored", lambda es: len(es)),
        KPI("degraded", "Degraded Tenants", lambda es: count_where(es, lambda e: e["error_rate_pct"] >= 2.0)),
        KPI("total_users", "Total Active Users", lambda es: sum(e["active_users"] for e in es)),
        KPI("enterprise_tenants", "Enterprise-Tier Tenants", lambda es: count_where(es, lambda e: e["plan_tier"] == "Enterprise")),
    ],
    agents=[
        Agent("tenant-health", "Tenant Health Agent", "Flags degraded tenants by API error rate and recommends a scaling action.", _tenant_health_agent, lambda e: f"check multi-tenant health for {e['id']}"),
        Agent("cost-optimization", "Cost Optimization Agent", "Flags plan-tier/usage mismatches and recommends a right-sizing action.", _cost_agent, lambda e: f"get tenant usage for {e['id']}"),
    ],
    copilot_actions=[
        CopilotAction("priority", "My priority", lambda e, es: f"Least healthy tenant: {top_by(es, lambda x: x['error_rate_pct'])['id']}."),
        CopilotAction("tenant-usage", "Tenant usage", lambda e, es: f"{e['tenant_name']}: {e['api_calls_today']:,} API calls today, {e['active_users']} active users." if e else "Select a tenant first.", lambda e: f"get tenant usage for {e['id']}" if e else "get tenant usage"),
        CopilotAction("cost-recommendation", "Cost recommendation", lambda e, es: f"{e['tenant_name']} is on {e['plan_tier']} tier." if e else "Select a tenant first."),
    ],
    mcp_namespace="saas",
    seed_entities=SEED_TENANTS,
    roadmap=[
        "High-performance DBaaS integration — this demo doesn't provision or monitor a real downstream database service.",
        "Metadata indexing — schema/catalog indexing across tenants isn't modeled here.",
        "Broader multi-tenant backend governance — only health and cost scoring are implemented.",
    ],
    color="#2563eb",
)
