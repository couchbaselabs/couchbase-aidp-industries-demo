"""Healthcare & Life Sciences — HCA Healthcare, Signify Health, Maccabi Healthcare Services.

All patient data below is entirely fictional demo data (names, visit
reasons, schedules) generated for this app, in the same spirit as the
reference app's mocked ERP data — never real patient information. Visit
reasons are kept to routine, non-sensitive categories (wellness visits,
screenings, follow-ups) rather than specific diagnoses.
"""
from app.industries.base import Agent, AgentDecision, CopilotAction, Industry, KPI
from app.industries.utils import count_where, top_by

SEED_PATIENTS = [
    {"id": "PAT-5501", "name": "Isabella Cruz", "visit_reason": "Annual wellness visit", "provider": "Dr. Osei", "last_visit_days_ago": 410, "next_appointment": "Unscheduled", "no_show_count": 1, "care_gap": "Annual wellness visit overdue"},
    {"id": "PAT-5502", "name": "William Foster", "visit_reason": "Physical therapy follow-up", "provider": "Dr. Lindgren", "last_visit_days_ago": 14, "next_appointment": "2026-09-25", "no_show_count": 0, "care_gap": None},
    {"id": "PAT-5503", "name": "Aiko Sato", "visit_reason": "Preventive screening due", "provider": "Dr. Osei", "last_visit_days_ago": 380, "next_appointment": "Unscheduled", "no_show_count": 2, "care_gap": "Preventive screening overdue"},
    {"id": "PAT-5504", "name": "Samuel Berg", "visit_reason": "Post-op follow-up", "provider": "Dr. Reyes", "last_visit_days_ago": 21, "next_appointment": "2026-09-18", "no_show_count": 0, "care_gap": None},
    {"id": "PAT-5505", "name": "Nadia Hussain", "visit_reason": "Chronic-care check-in", "provider": "Dr. Lindgren", "last_visit_days_ago": 95, "next_appointment": "Unscheduled", "no_show_count": 1, "care_gap": "Quarterly check-in overdue"},
    {"id": "PAT-5506", "name": "Tobias Klein", "visit_reason": "Annual wellness visit", "provider": "Dr. Reyes", "last_visit_days_ago": 40, "next_appointment": "2026-10-02", "no_show_count": 0, "care_gap": None},
    {"id": "PAT-5507", "name": "Grace Mensah", "visit_reason": "Preventive screening due", "provider": "Dr. Osei", "last_visit_days_ago": 400, "next_appointment": "Unscheduled", "no_show_count": 3, "care_gap": "Preventive screening overdue"},
    {"id": "PAT-5508", "name": "Ethan Walsh", "visit_reason": "Physical therapy follow-up", "provider": "Dr. Reyes", "last_visit_days_ago": 8, "next_appointment": "2026-09-16", "no_show_count": 0, "care_gap": None},
]


def _care_gap_agent(entity: dict, all_entities: list) -> AgentDecision:
    if entity["care_gap"]:
        rec, sev = "Trigger outreach (call/portal message) to schedule", "critical" if entity["last_visit_days_ago"] > 365 else "warning"
        fallback = f"{entity['name']}'s last visit was {entity['last_visit_days_ago']} days ago and shows an open care gap: {entity['care_gap']}. Recommend outreach to schedule."
        confidence = 0.9
    else:
        rec, sev = "No open care gap — no action needed", "positive"
        fallback = f"{entity['name']} has no open care gap; last visit was {entity['last_visit_days_ago']} days ago."
        confidence = 0.85
    return AgentDecision(rec, fallback, confidence, "Days since last visit", str(entity["last_visit_days_ago"]), {"care_gap": entity["care_gap"], "last_visit_days_ago": entity["last_visit_days_ago"]}, sev)


def _appointment_agent(entity: dict, all_entities: list) -> AgentDecision:
    if entity["next_appointment"] != "Unscheduled":
        rec, sev = f"Already scheduled for {entity['next_appointment']} — send a reminder 48h prior", "positive"
        fallback = f"{entity['name']} has an appointment on {entity['next_appointment']} with {entity['provider']}."
        confidence = 0.8
    elif entity["no_show_count"] >= 2:
        rec, sev = "Offer a same-week slot with a reminder call, not just SMS (no-show risk)", "warning"
        fallback = f"{entity['name']} has {entity['no_show_count']} prior no-shows and no appointment on the books — recommend a higher-touch scheduling outreach."
        confidence = 0.75
    else:
        rec, sev = f"Offer the next open slot with {entity['provider']}", "info"
        fallback = f"{entity['name']} has no appointment scheduled — recommend the next open slot with {entity['provider']}."
        confidence = 0.7
    return AgentDecision(rec, fallback, confidence, "No-show count", str(entity["no_show_count"]), {"next_appointment": entity["next_appointment"], "no_show_count": entity["no_show_count"]}, sev)


INDUSTRY = Industry(
    id="healthcare",
    name="Healthcare & Life Sciences",
    tagline="Unified patient records and appointment management on a governed AI data plane.",
    icon="🩺",
    examples=["HCA Healthcare", "Signify Health", "Maccabi Healthcare Services"],
    entity_label="Patient",
    entity_label_plural="Patients",
    entity_title_field="id",
    entity_subtitle_field="name",
    kpis=[
        KPI("patients", "Patients Monitored", lambda es: len(es)),
        KPI("open_care_gaps", "Open Care Gaps", lambda es: count_where(es, lambda e: e["care_gap"])),
        KPI("unscheduled", "Unscheduled Follow-ups", lambda es: count_where(es, lambda e: e["next_appointment"] == "Unscheduled")),
        KPI("no_show_risk", "No-Show Risk (2+)", lambda es: count_where(es, lambda e: e["no_show_count"] >= 2)),
    ],
    agents=[
        Agent("care-gap", "Care Gap Agent", "Flags overdue preventive/follow-up care and recommends outreach.", _care_gap_agent, lambda e: f"check care gaps for patient {e['id']}"),
        Agent("appointment-optimization", "Appointment Optimization Agent", "Recommends the next scheduling action, weighting no-show risk.", _appointment_agent, lambda e: f"schedule appointment for patient {e['id']}"),
    ],
    copilot_actions=[
        CopilotAction("priority", "My priority", lambda e, es: f"Most overdue care gap: {top_by(es, lambda x: x['last_visit_days_ago'] if x['care_gap'] else -1)['id']}."),
        CopilotAction("patient-summary", "Patient summary", lambda e, es: f"{e['name']}, provider {e['provider']}, last visit {e['last_visit_days_ago']} days ago, care gap: {e['care_gap'] or 'none'}." if e else "Select a patient first.", lambda e: f"get patient summary for {e['id']}" if e else "get patient summary"),
        CopilotAction("appointment-suggestion", "Appointment suggestion", lambda e, es: f"{e['name']} next appointment: {e['next_appointment']}." if e else "Select a patient first."),
    ],
    mcp_namespace="healthcare",
    seed_entities=SEED_PATIENTS,
    roadmap=[
        "Offline-first mobile health tracking — device/wearable sync isn't modeled in this demo.",
        "Clinical trials — trial matching/eligibility workflows aren't part of this demo's surface.",
        "Secure multi-region data syncing — this demo runs one Couchbase cluster, not a cross-region XDCR topology.",
    ],
    color="#0284c7",
)
