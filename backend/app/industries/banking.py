"""Financial Services & Banking — American Express, global payment networks, digital fintechs."""
from app.industries.base import Agent, AgentDecision, CopilotAction, Industry, KPI
from app.industries.utils import avg, count_where, top_by

SEED_TRANSACTIONS = [
    {"id": "TXN-88012", "customer_name": "Alicia Gomez", "account_id": "ACC-4471", "amount": 4820.00, "merchant": "Electronics Bazaar", "channel": "card-not-present", "country": "RO", "home_country": "US", "velocity_last_hour": 5, "credit_utilization_pct": 41},
    {"id": "TXN-88013", "customer_name": "Ben Torres", "account_id": "ACC-5502", "amount": 62.40, "merchant": "Corner Cafe", "channel": "chip", "country": "US", "home_country": "US", "velocity_last_hour": 1, "credit_utilization_pct": 22},
    {"id": "TXN-88014", "customer_name": "Chidi Obi", "account_id": "ACC-6113", "amount": 1899.00, "merchant": "QuickGold Exchange", "channel": "card-not-present", "country": "US", "home_country": "US", "velocity_last_hour": 4, "credit_utilization_pct": 88},
    {"id": "TXN-88015", "customer_name": "Dana Whitfield", "account_id": "ACC-2290", "amount": 215.00, "merchant": "Riverside Grocers", "channel": "chip", "country": "US", "home_country": "US", "velocity_last_hour": 1, "credit_utilization_pct": 15},
    {"id": "TXN-88016", "customer_name": "Elif Kaya", "account_id": "ACC-7788", "amount": 3120.00, "merchant": "LuxTravel Booking", "channel": "card-not-present", "country": "TR", "home_country": "DE", "velocity_last_hour": 3, "credit_utilization_pct": 55},
    {"id": "TXN-88017", "customer_name": "Frank Delgado", "account_id": "ACC-3345", "amount": 48.00, "merchant": "Metro Transit", "channel": "contactless", "country": "US", "home_country": "US", "velocity_last_hour": 1, "credit_utilization_pct": 30},
    {"id": "TXN-88018", "customer_name": "Grace Lindqvist", "account_id": "ACC-9012", "amount": 990.00, "merchant": "PrimeStay Hotels", "channel": "card-not-present", "country": "US", "home_country": "SE", "velocity_last_hour": 2, "credit_utilization_pct": 67},
    {"id": "TXN-88019", "customer_name": "Hassan Malik", "account_id": "ACC-1187", "amount": 7300.00, "merchant": "RapidCoin ATM", "channel": "card-not-present", "country": "NG", "home_country": "US", "velocity_last_hour": 6, "credit_utilization_pct": 93},
]


def _fraud_agent(entity: dict, all_entities: list) -> AgentDecision:
    signals = []
    score = 0
    if entity["country"] != entity["home_country"]:
        signals.append("cross-border, off-home-country merchant")
        score += 35
    if entity["velocity_last_hour"] >= 4:
        signals.append(f"{entity['velocity_last_hour']} transactions in the last hour")
        score += 30
    if entity["amount"] >= 2000:
        signals.append(f"${entity['amount']:,.2f} is a high-value transaction")
        score += 25
    if entity["channel"] == "card-not-present":
        signals.append("card-not-present channel")
        score += 10
    score = min(score, 99)
    if score >= 60:
        rec, sev = "Hold and step up to customer verification before settling", "critical"
    elif score >= 30:
        rec, sev = "Flag for analyst review, allow to settle for now", "warning"
    else:
        rec, sev = "No fraud signal — settle normally", "positive"
    fallback = f"Fraud score {score}/99 on {', '.join(signals) if signals else 'no notable signals'}."
    return AgentDecision(rec, fallback, min(0.6 + score / 200, 0.98), "Fraud score", f"{score}/99", {"signals": signals, "score": score}, sev)


def _risk_agent(entity: dict, all_entities: list) -> AgentDecision:
    util = entity["credit_utilization_pct"]
    if util >= 85:
        rec, sev = "Proactive credit-line review — utilization is near the ceiling", "critical"
        fallback = f"Account {entity['account_id']} is at {util}% credit utilization — recommend a proactive review before the next statement."
    elif util >= 60:
        rec, sev = "Monitor — utilization trending high", "warning"
        fallback = f"Account {entity['account_id']} is at {util}% utilization, above the 60% watch threshold."
    else:
        rec, sev = "Healthy utilization — no action", "positive"
        fallback = f"Account {entity['account_id']} is at {util}% utilization, within the healthy range."
    return AgentDecision(rec, fallback, 0.85, "Credit utilization", f"{util}%", {"credit_utilization_pct": util, "account_id": entity["account_id"]}, sev)


INDUSTRY = Industry(
    id="banking",
    name="Financial Services & Banking",
    tagline="Real-time fraud detection and risk management on a governed AI data plane.",
    icon="🏦",
    examples=["American Express", "global payment networks", "digital financial tech providers"],
    entity_label="Transaction",
    entity_label_plural="Transactions",
    entity_title_field="id",
    entity_subtitle_field="customer_name",
    kpis=[
        KPI("transactions_today", "Transactions Reviewed", lambda es: len(es)),
        KPI("high_risk", "High Fraud-Score Transactions", lambda es: count_where(es, lambda e: e["velocity_last_hour"] >= 4 or e["amount"] >= 2000)),
        KPI("avg_amount", "Avg Transaction Amount", lambda es: round(avg(es, lambda e: e["amount"]), 2), "currency"),
        KPI("near_limit", "Accounts Near Credit Limit", lambda es: count_where(es, lambda e: e["credit_utilization_pct"] >= 85)),
    ],
    agents=[
        Agent("fraud-detection", "Fraud Detection Agent", "Scores each transaction on velocity, geography, amount, and channel signals.", _fraud_agent, lambda e: f"flag fraud transaction {e['id']}"),
        Agent("risk-management", "Risk Management Agent", "Flags accounts approaching credit-utilization risk thresholds.", _risk_agent, lambda e: f"get account risk profile for {e['account_id']}"),
    ],
    copilot_actions=[
        CopilotAction("priority", "My priority", lambda e, es: f"Highest fraud score: {top_by(es, lambda x: x['velocity_last_hour']*30 + (35 if x['country']!=x['home_country'] else 0) + (25 if x['amount']>=2000 else 0))['id']}."),
        CopilotAction("compliance-check", "Compliance check", lambda e, es: f"Transaction {e['id']} — {e['channel']}, {e['country']} vs. home {e['home_country']}, amount ${e['amount']:,.2f}." if e else "Select a transaction first.", lambda e: f"flag fraud transaction {e['id']}" if e else "flag fraud transaction"),
        CopilotAction("account-profile", "Account risk profile", lambda e, es: f"Account {e['account_id']} is at {e['credit_utilization_pct']}% utilization." if e else "Select a transaction first."),
    ],
    mcp_namespace="banking",
    seed_entities=SEED_TRANSACTIONS,
    roadmap=[
        "Payment processing gateways — this demo scores transactions already captured, not the live authorization path.",
        "Digital wallet transactions — wallet-specific signals (device binding, tokenization) aren't modeled here.",
        "Secure customer account portals — self-service account access isn't part of this demo's surface.",
    ],
    color="#0f766e",
)
