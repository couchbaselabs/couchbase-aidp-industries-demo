"""Manufacturing & Supply Chain — General Electric (GE), industrial engineering firms."""
from app.industries.base import Agent, AgentDecision, CopilotAction, Industry, KPI
from app.industries.utils import count_where, top_by

SEED_SHIPMENTS = [
    {"id": "SHP-6601", "supplier": "Meridian Castings", "part_number": "MC-4471-B", "origin": "Pittsburgh, PA", "destination": "Toledo, OH", "eta_days": 2, "sensor_temp_c": 23, "sensor_status": "normal", "delay_days": 0},
    {"id": "SHP-6602", "supplier": "Norwood Alloys", "part_number": "NA-9012-A", "origin": "Gary, IN", "destination": "Toledo, OH", "eta_days": 5, "sensor_temp_c": 41, "sensor_status": "alert", "delay_days": 3},
    {"id": "SHP-6603", "supplier": "Ridgeline Fasteners", "part_number": "RF-2290-C", "origin": "Cleveland, OH", "destination": "Toledo, OH", "eta_days": 1, "sensor_temp_c": 21, "sensor_status": "normal", "delay_days": 0},
    {"id": "SHP-6604", "supplier": "Meridian Castings", "part_number": "MC-3305-D", "origin": "Pittsburgh, PA", "destination": "Dayton, OH", "eta_days": 4, "sensor_temp_c": 22, "sensor_status": "normal", "delay_days": 1},
    {"id": "SHP-6605", "supplier": "Blackstone Hydraulics", "part_number": "BH-7788-A", "origin": "Detroit, MI", "destination": "Dayton, OH", "eta_days": 6, "sensor_temp_c": 38, "sensor_status": "alert", "delay_days": 4},
    {"id": "SHP-6606", "supplier": "Norwood Alloys", "part_number": "NA-1187-B", "origin": "Gary, IN", "destination": "Dayton, OH", "eta_days": 2, "sensor_temp_c": 24, "sensor_status": "normal", "delay_days": 0},
    {"id": "SHP-6607", "supplier": "Ridgeline Fasteners", "part_number": "RF-5502-E", "origin": "Cleveland, OH", "destination": "Toledo, OH", "eta_days": 3, "sensor_temp_c": 19, "sensor_status": "normal", "delay_days": 0},
    {"id": "SHP-6608", "supplier": "Blackstone Hydraulics", "part_number": "BH-3345-C", "origin": "Detroit, MI", "destination": "Toledo, OH", "eta_days": 7, "sensor_temp_c": 20, "sensor_status": "normal", "delay_days": 5},
]


def _supply_risk_agent(entity: dict, all_entities: list) -> AgentDecision:
    if entity["delay_days"] >= 3:
        rec, sev = "Source an alternate qualified supplier for this part now", "critical"
        fallback = f"{entity['id']} ({entity['part_number']} from {entity['supplier']}) is running {entity['delay_days']} days late — recommend an alternate-supplier check."
        confidence = 0.88
    elif entity["delay_days"] >= 1:
        rec, sev = "Expedite — notify the receiving plant of a minor delay", "warning"
        fallback = f"{entity['id']} is running {entity['delay_days']} day(s) late — worth a heads-up to the receiving plant."
        confidence = 0.7
    else:
        rec, sev = "On schedule — no action", "positive"
        fallback = f"{entity['id']} is on schedule, ETA in {entity['eta_days']} days."
        confidence = 0.8
    return AgentDecision(rec, fallback, confidence, "Delay (days)", str(entity["delay_days"]), {"delay_days": entity["delay_days"], "supplier": entity["supplier"]}, sev)


def _iot_agent(entity: dict, all_entities: list) -> AgentDecision:
    temp = entity["sensor_temp_c"]
    if entity["sensor_status"] == "alert":
        rec, sev = "Place shipment on quality hold pending inspection", "critical"
        fallback = f"{entity['id']}'s in-transit sensor reads {temp}°C, outside the normal range — recommend a quality hold."
        confidence = 0.9
    else:
        rec, sev = "Sensor readings normal — no action", "positive"
        fallback = f"{entity['id']}'s sensor reads {temp}°C — within the normal range."
        confidence = 0.85
    return AgentDecision(rec, fallback, confidence, "Sensor temp", f"{temp}°C", {"sensor_temp_c": temp, "sensor_status": entity["sensor_status"]}, sev)


INDUSTRY = Industry(
    id="manufacturing",
    name="Manufacturing & Supply Chain",
    tagline="Supply chain visibility and IoT telemetry synced on one AI data plane.",
    icon="🏭",
    examples=["General Electric (GE)", "industrial engineering firms"],
    entity_label="Shipment",
    entity_label_plural="Shipments",
    entity_title_field="id",
    entity_subtitle_field="supplier",
    kpis=[
        KPI("shipments", "Shipments In Transit", lambda es: len(es)),
        KPI("delayed", "Delayed Shipments", lambda es: count_where(es, lambda e: e["delay_days"] > 0)),
        KPI("sensor_alerts", "Sensor Alerts", lambda es: count_where(es, lambda e: e["sensor_status"] == "alert")),
        KPI("avg_eta", "Avg ETA (days)", lambda es: round(sum(e["eta_days"] for e in es) / len(es), 1) if es else 0),
    ],
    agents=[
        Agent("supply-risk", "Supply Risk Agent", "Flags at-risk shipments by delay and recommends alternate sourcing or expediting.", _supply_risk_agent, lambda e: f"flag supply risk for {e['supplier']}"),
        Agent("iot-anomaly", "IoT Anomaly Agent", "Flags out-of-range in-transit sensor telemetry and recommends a quality hold.", _iot_agent, lambda e: f"check iot sensor for shipment {e['id']}"),
    ],
    copilot_actions=[
        CopilotAction("priority", "My priority", lambda e, es: f"Most at-risk shipment: {top_by(es, lambda x: x['delay_days'])['id']}."),
        CopilotAction("sensor-check", "Sensor check", lambda e, es: f"{e['id']} sensor reads {e['sensor_temp_c']}°C ({e['sensor_status']})." if e else "Select a shipment first.", lambda e: f"check iot sensor for shipment {e['id']}" if e else "check iot sensor"),
        CopilotAction("supplier-lookup", "Supplier lookup", lambda e, es: f"{e['id']} — {e['part_number']} from {e['supplier']}, {e['origin']} to {e['destination']}." if e else "Select a shipment first."),
    ],
    mcp_namespace="manufacturing",
    seed_entities=SEED_SHIPMENTS,
    roadmap=[
        "Smart factory logistics — in-plant routing/scheduling isn't modeled in this demo.",
        "Operational asset management — this demo tracks in-transit shipments, not installed-base asset health.",
        "Broader supply chain visibility — only two agent views into the chain are implemented here.",
    ],
    color="#b45309",
)
