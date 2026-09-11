"""Telecommunications — Comcast, British Telecommunications (BT)."""
from app.industries.base import Agent, AgentDecision, CopilotAction, Industry, KPI
from app.industries.utils import count_where, top_by

SEED_SUBSCRIBERS = [
    {"id": "SUB-3301", "name": "Anya Petrova", "plan": "Unlimited 5G", "monthly_usage_gb": 61, "plan_limit_gb": 50, "tenure_months": 4, "support_tickets_30d": 3, "city": "Austin"},
    {"id": "SUB-3302", "name": "Marcus Lee", "plan": "Family 100GB", "monthly_usage_gb": 38, "plan_limit_gb": 100, "tenure_months": 27, "support_tickets_30d": 0, "city": "Denver"},
    {"id": "SUB-3303", "name": "Rosa Delgado", "plan": "Basic 20GB", "monthly_usage_gb": 24, "plan_limit_gb": 20, "tenure_months": 9, "support_tickets_30d": 2, "city": "Miami"},
    {"id": "SUB-3304", "name": "Tomas Novak", "plan": "Unlimited 5G", "monthly_usage_gb": 44, "plan_limit_gb": 50, "tenure_months": 58, "support_tickets_30d": 0, "city": "Chicago"},
    {"id": "SUB-3305", "name": "Yuki Tanaka", "plan": "Family 100GB", "monthly_usage_gb": 112, "plan_limit_gb": 100, "tenure_months": 3, "support_tickets_30d": 4, "city": "Seattle"},
    {"id": "SUB-3306", "name": "Omar Haddad", "plan": "Basic 20GB", "monthly_usage_gb": 12, "plan_limit_gb": 20, "tenure_months": 61, "support_tickets_30d": 0, "city": "Phoenix"},
    {"id": "SUB-3307", "name": "Lena Fischer", "plan": "Unlimited 5G", "monthly_usage_gb": 55, "plan_limit_gb": 50, "tenure_months": 2, "support_tickets_30d": 3, "city": "Boston"},
    {"id": "SUB-3308", "name": "Carlos Mendez", "plan": "Family 100GB", "monthly_usage_gb": 71, "plan_limit_gb": 100, "tenure_months": 15, "support_tickets_30d": 1, "city": "Houston"},
]


def _billing_agent(entity: dict, all_entities: list) -> AgentDecision:
    over = entity["monthly_usage_gb"] - entity["plan_limit_gb"]
    if over > 0:
        rec, sev = f"Recommend upgrading to the next plan tier (overage would otherwise bill)", "warning"
        fallback = f"{entity['name']} used {entity['monthly_usage_gb']}GB against a {entity['plan_limit_gb']}GB limit — {over}GB over. A plan upgrade avoids an overage charge."
    else:
        headroom = entity["plan_limit_gb"] - entity["monthly_usage_gb"]
        rec, sev = "No billing action needed", "positive"
        fallback = f"{entity['name']} used {entity['monthly_usage_gb']}GB of a {entity['plan_limit_gb']}GB plan — {headroom}GB of headroom remaining."
    return AgentDecision(rec, fallback, 0.88, "GB over/under limit", f"{over:+d}GB", {"usage_gb": entity["monthly_usage_gb"], "limit_gb": entity["plan_limit_gb"]}, sev)


def _churn_agent(entity: dict, all_entities: list) -> AgentDecision:
    score = 0
    reasons = []
    if entity["support_tickets_30d"] >= 3:
        score += 40
        reasons.append(f"{entity['support_tickets_30d']} support tickets in 30 days")
    if entity["tenure_months"] < 6:
        score += 30
        reasons.append(f"only {entity['tenure_months']} months tenure")
    if entity["monthly_usage_gb"] > entity["plan_limit_gb"]:
        score += 15
        reasons.append("recent overage")
    score = min(score, 95)
    if score >= 50:
        rec, sev = "Proactively offer a loyalty credit or plan review", "critical"
    elif score >= 25:
        rec, sev = "Monitor — schedule a satisfaction check-in", "warning"
    else:
        rec, sev = "Low churn risk — no action", "positive"
    fallback = f"Churn risk {score}/95 driven by {', '.join(reasons) if reasons else 'no notable signals'}."
    return AgentDecision(rec, fallback, min(0.55 + score / 200, 0.95), "Churn risk score", f"{score}/95", {"score": score, "reasons": reasons}, sev)


INDUSTRY = Industry(
    id="telecom",
    name="Telecommunications",
    tagline="Real-time billing and churn reduction across a subscriber base, on one AI data plane.",
    icon="📡",
    examples=["Comcast", "British Telecommunications (BT)"],
    entity_label="Subscriber",
    entity_label_plural="Subscribers",
    entity_title_field="id",
    entity_subtitle_field="name",
    kpis=[
        KPI("subscribers", "Subscribers Monitored", lambda es: len(es)),
        KPI("over_limit", "Over Plan Limit", lambda es: count_where(es, lambda e: e["monthly_usage_gb"] > e["plan_limit_gb"])),
        KPI("high_churn_risk", "High Churn-Risk", lambda es: count_where(es, lambda e: e["support_tickets_30d"] >= 3 or e["tenure_months"] < 6)),
        KPI("avg_tenure", "Avg Tenure (months)", lambda es: round(sum(e["tenure_months"] for e in es) / len(es), 1) if es else 0),
    ],
    agents=[
        Agent("billing-anomaly", "Billing Anomaly Agent", "Flags plan overages and recommends the right-sized plan tier.", _billing_agent, lambda e: f"get subscriber usage for {e['id']}"),
        Agent("churn-risk", "Churn Risk Agent", "Scores churn risk from support-ticket volume, tenure, and usage patterns, recommends a retention action.", _churn_agent, lambda e: f"apply retention offer for {e['id']}"),
    ],
    copilot_actions=[
        CopilotAction("priority", "My priority", lambda e, es: f"Highest churn risk: {top_by(es, lambda x: x['support_tickets_30d']*40 + (30 if x['tenure_months']<6 else 0))['id']}."),
        CopilotAction("retention-offer", "Retention offer", lambda e, es: f"{e['name']} has {e['support_tickets_30d']} tickets in 30 days and {e['tenure_months']} months tenure." if e else "Select a subscriber first.", lambda e: f"apply retention offer for {e['id']}" if e else "apply retention offer"),
        CopilotAction("network-status", "Network status check", lambda e, es: f"Checking network status near {e['city']}." if e else "Select a subscriber first.", lambda e: f"check network status near {e['city']}" if e else "check network status"),
    ],
    mcp_namespace="telecom",
    seed_entities=SEED_SUBSCRIBERS,
    roadmap=[
        "Full subscriber data management — this demo reads a slice of usage/tenure, not a full OSS/BSS subscriber record.",
        "High-throughput network service provisioning — provisioning workflows aren't modeled here.",
        "Multi-channel customer service coordination — ticket data is summarized, not a live omni-channel case view.",
    ],
    color="#7c3aed",
)
