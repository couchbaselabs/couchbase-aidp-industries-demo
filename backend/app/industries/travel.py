"""Travel & Hospitality — Carnival Cruise Line, American Express Global Business Travel."""
from app.industries.base import Agent, AgentDecision, CopilotAction, Industry, KPI
from app.industries.utils import avg, count_where, top_by

SEED_BOOKINGS = [
    {"id": "BKG-7701", "traveler_name": "Olivia Park", "itinerary": "Miami -> Cozumel, 7 nights", "loyalty_tier": "Gold", "booking_value": 2450.00, "days_to_departure": 12, "connection_minutes": 240, "cabin_waitlist": False},
    {"id": "BKG-7702", "traveler_name": "Ethan Brooks", "itinerary": "JFK -> LHR -> CDG", "loyalty_tier": "Silver", "booking_value": 980.00, "days_to_departure": 3, "connection_minutes": 38, "cabin_waitlist": False},
    {"id": "BKG-7703", "traveler_name": "Camila Torres", "itinerary": "Barcelona -> Rome, 5 nights", "loyalty_tier": "Platinum", "booking_value": 3900.00, "days_to_departure": 30, "connection_minutes": 0, "cabin_waitlist": True},
    {"id": "BKG-7704", "traveler_name": "Noah Williams", "itinerary": "LAX -> Tokyo Narita", "loyalty_tier": "Bronze", "booking_value": 1150.00, "days_to_departure": 45, "connection_minutes": 0, "cabin_waitlist": False},
    {"id": "BKG-7705", "traveler_name": "Ava Johansson", "itinerary": "Miami -> Bahamas, 3 nights", "loyalty_tier": "Gold", "booking_value": 890.00, "days_to_departure": 5, "connection_minutes": 0, "cabin_waitlist": False},
    {"id": "BKG-7706", "traveler_name": "Lucas Ferreira", "itinerary": "ORD -> Frankfurt -> Vienna", "loyalty_tier": "Silver", "booking_value": 1320.00, "days_to_departure": 8, "connection_minutes": 42, "cabin_waitlist": False},
    {"id": "BKG-7707", "traveler_name": "Mia Andersson", "itinerary": "Barcelona Mediterranean, 10 nights", "loyalty_tier": "Platinum", "booking_value": 5600.00, "days_to_departure": 60, "connection_minutes": 0, "cabin_waitlist": True},
    {"id": "BKG-7708", "traveler_name": "Daniel Osei", "itinerary": "ATL -> Amsterdam -> Prague", "loyalty_tier": "Bronze", "booking_value": 1040.00, "days_to_departure": 2, "connection_minutes": 51, "cabin_waitlist": False},
]


def _loyalty_agent(entity: dict, all_entities: list) -> AgentDecision:
    tier = entity["loyalty_tier"]
    if tier in ("Gold", "Platinum") and entity["booking_value"] > 2000:
        rec, sev = "Offer a complimentary cabin/seat upgrade to protect loyalty", "positive"
        fallback = f"{entity['traveler_name']} ({tier}) booked ${entity['booking_value']:,.2f} — recommend an upgrade offer to reinforce loyalty."
        confidence = 0.85
    elif tier in ("Bronze", "Silver"):
        rec, sev = "Offer a tier-appropriate add-on (lounge pass, seat selection)", "info"
        fallback = f"{entity['traveler_name']} ({tier}) — recommend a smaller, tier-appropriate upsell rather than a full upgrade."
        confidence = 0.65
    else:
        rec, sev = "No upsell action needed", "positive"
        fallback = f"{entity['traveler_name']} ({tier}) has no clear upsell opportunity on this booking."
        confidence = 0.6
    return AgentDecision(rec, fallback, confidence, "Loyalty tier", tier, {"loyalty_tier": tier, "booking_value": entity["booking_value"]}, sev)


def _risk_agent(entity: dict, all_entities: list) -> AgentDecision:
    reasons = []
    score = 0
    if 0 < entity["connection_minutes"] < 45:
        reasons.append(f"{entity['connection_minutes']}-minute connection is tight")
        score += 40
    if entity["cabin_waitlist"]:
        reasons.append("cabin category is waitlisted")
        score += 35
    if entity["days_to_departure"] <= 3:
        reasons.append(f"departs in {entity['days_to_departure']} days")
        score += 20
    score = min(score, 95)
    if score >= 50:
        rec, sev = "Proactively contact traveler with a rebooking/backup option", "critical"
    elif score >= 20:
        rec, sev = "Monitor — flag to the day-of-travel team", "warning"
    else:
        rec, sev = "Low risk — no action needed", "positive"
    fallback = f"Risk score {score}/95: {', '.join(reasons) if reasons else 'no notable risk signals'}."
    return AgentDecision(rec, fallback, min(0.6 + score / 200, 0.95), "Booking risk score", f"{score}/95", {"score": score, "reasons": reasons}, sev)


INDUSTRY = Industry(
    id="travel",
    name="Travel & Hospitality",
    tagline="Booking risk and loyalty tracking across the traveler journey, on one AI data plane.",
    icon="✈️",
    examples=["Carnival Cruise Line", "American Express Global Business Travel"],
    entity_label="Booking",
    entity_label_plural="Bookings",
    entity_title_field="id",
    entity_subtitle_field="traveler_name",
    kpis=[
        KPI("bookings", "Active Bookings", lambda es: len(es)),
        KPI("at_risk", "At-Risk Bookings", lambda es: count_where(es, lambda e: e["cabin_waitlist"] or (0 < e["connection_minutes"] < 45))),
        KPI("avg_value", "Avg Booking Value", lambda es: round(avg(es, lambda e: e["booking_value"]), 2), "currency"),
        KPI("gold_plus", "Gold+ Travelers", lambda es: count_where(es, lambda e: e["loyalty_tier"] in ("Gold", "Platinum"))),
    ],
    agents=[
        Agent("loyalty-upsell", "Loyalty Upsell Agent", "Recommends a tier-appropriate upgrade or add-on offer.", _loyalty_agent, lambda e: f"check loyalty status for {e['traveler_name']}"),
        Agent("booking-risk", "Booking Risk Agent", "Flags tight connections, waitlisted cabins, and near-departure risk.", _risk_agent, lambda e: f"get booking details for {e['id']}"),
    ],
    copilot_actions=[
        CopilotAction("priority", "My priority", lambda e, es: f"Highest booking risk: {top_by(es, lambda x: (40 if 0<x['connection_minutes']<45 else 0) + (35 if x['cabin_waitlist'] else 0))['id']}."),
        CopilotAction("loyalty-offer", "Loyalty offer", lambda e, es: f"{e['traveler_name']} is {e['loyalty_tier']} tier on a ${e['booking_value']:,.2f} booking." if e else "Select a booking first.", lambda e: f"check loyalty status for {e['traveler_name']}" if e else "check loyalty status"),
        CopilotAction("booking-lookup", "Booking lookup", lambda e, es: f"{e['id']}: {e['itinerary']}, departs in {e['days_to_departure']} days." if e else "Select a booking first."),
    ],
    mcp_namespace="travel",
    seed_entities=SEED_BOOKINGS,
    roadmap=[
        "Passenger pre-flight checklists — day-of-departure checklist workflows aren't modeled here.",
        "Onboard mobile-to-cloud applications — this demo doesn't model in-flight/onboard connectivity sync.",
        "Full booking and reservation engine breadth — only risk/loyalty scoring is implemented, not search/booking itself.",
    ],
    color="#0891b2",
)
