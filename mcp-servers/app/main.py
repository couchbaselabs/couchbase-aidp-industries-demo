"""
Bundled MCP tool servers for the Couchbase AIDP Industries Demo — one
FastMCP endpoint per industry vertical, each reachable at its own path
(mirroring the reference Couchbase Agent Operations Manager repo's
`sample-mcp-servers/app/main.py` almost exactly), so an operator running
`scripts/register_with_aom.py` can register all ten with AOM as real,
independent MCP servers. AOM proxies every discover()/invoke() call
through to whichever of these a caller's role is authorized for — that's
what makes this app's agent -> MCP-tool traffic show up on AOM's own
Dashboard "Live topology" and Agent Tool Audit pages.

None of this touches a real inventory system, core banking ledger, EHR,
etc. — every handler returns small, representative mock data, exactly the
posture the reference sample servers use, so nothing here needs external
credentials.

  /retail/mcp          - inventory, customer 360, recommendations
  /banking/mcp         - fraud flagging, account risk, account freeze (admin-only in spirit)
  /telecom/mcp         - subscriber usage, network status, retention offers
  /healthcare/mcp      - patient summary, care gaps, appointment scheduling
  /travel/mcp          - booking details, loyalty status, rebooking
  /media/mcp           - viewer profile, stream health, content recommendations
  /saas/mcp            - tenant usage, multi-tenant health, cost estimation
  /manufacturing/mcp   - shipment status, IoT sensor checks, supply risk
  /energy/mcp          - grid telemetry, field-team dispatch, load forecasting
  /public_sector/mcp   - citizen case lookup, identity verification, request routing
"""
import contextlib
import logging
import os
import random

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("aidp-mcp-servers")

# Same rationale as the reference sample-mcp-servers: these are same-
# Docker-network demo fixtures reached by Compose service name
# (aidp-mcp-servers:8500), not internet-facing servers a client dials by
# IP/hostname config, so FastMCP's default DNS-rebinding Host-header check
# (which only allowlists 127.0.0.1/localhost) would otherwise 421 every
# call AOM's operations-manager container makes.
NO_HOST_CHECK = TransportSecuritySettings(enable_dns_rebinding_protection=False)


def _mcp(name: str, instructions: str) -> FastMCP:
    return FastMCP(name, instructions=instructions, stateless_http=True, transport_security=NO_HOST_CHECK)


# ---------------------------------------------------------------------------
# retail
# ---------------------------------------------------------------------------
retail = _mcp("retail", "Retail & e-commerce: inventory, customer 360, and product recommendations.")


@retail.tool()
def check_inventory(store_id: str) -> dict:
    """Check current stock-on-hand for a store, including nearby-store transfer candidates."""
    return {"store_id": store_id, "stock_on_hand": random.randint(0, 20), "nearby_stores_with_stock": ["STL-002", "STL-031"]}


@retail.tool()
def get_customer_360(customer_name: str) -> dict:
    """Retrieve a customer's cross-channel profile: loyalty tier, channel mix, and purchase categories."""
    return {"customer_name": customer_name, "loyalty_tier": random.choice(["Bronze", "Silver", "Gold", "Platinum"]), "channels": ["web", "app", "store"]}


@retail.tool()
def recommend_products(customer_id: str) -> dict:
    """Return personalized product recommendations for a customer."""
    return {"customer_id": customer_id, "recommendations": ["USB-C hub", "Monitor arm", "Desk organizer"]}


# ---------------------------------------------------------------------------
# banking
# ---------------------------------------------------------------------------
banking = _mcp("banking", "Financial services: fraud flagging, account risk profiles, and account actions.")


@banking.tool()
def flag_fraud_transaction(transaction_id: str) -> dict:
    """Run an independent fraud check on a transaction and return the verdict."""
    return {"transaction_id": transaction_id, "verdict": random.choice(["clear", "review", "hold"]), "checked_at": "live"}


@banking.tool()
def get_account_risk_profile(account_id: str) -> dict:
    """Retrieve an account's current credit utilization and risk tier."""
    return {"account_id": account_id, "credit_utilization_pct": random.randint(10, 95), "risk_tier": random.choice(["low", "medium", "high"])}


@banking.tool()
def freeze_account(account_id: str, reason: str = "") -> dict:
    """ADMIN ONLY. Freeze an account pending fraud review."""
    return {"account_id": account_id, "frozen": True, "reason": reason, "risk": "high"}


# ---------------------------------------------------------------------------
# telecom
# ---------------------------------------------------------------------------
telecom = _mcp("telecom", "Telecommunications: subscriber usage, network status, and retention offers.")


@telecom.tool()
def get_subscriber_usage(subscriber_id: str) -> dict:
    """Retrieve a subscriber's current-cycle data usage against their plan limit."""
    return {"subscriber_id": subscriber_id, "usage_gb": random.randint(10, 120), "plan_limit_gb": random.choice([20, 50, 100])}


@telecom.tool()
def check_network_status(region: str) -> dict:
    """Check current network health for a region."""
    return {"region": region, "status": random.choice(["nominal", "degraded"]), "open_incidents": random.randint(0, 2)}


@telecom.tool()
def apply_retention_offer(subscriber_id: str) -> dict:
    """Apply a retention credit/offer to a subscriber account."""
    return {"subscriber_id": subscriber_id, "offer_applied": "one-time loyalty credit", "applied": True}


# ---------------------------------------------------------------------------
# healthcare
# ---------------------------------------------------------------------------
healthcare = _mcp("healthcare", "Healthcare: patient summaries, care-gap checks, and appointment scheduling.")


@healthcare.tool()
def get_patient_summary(patient_id: str) -> dict:
    """Retrieve a patient's provider, last-visit date, and open care gaps (mock, non-clinical demo data)."""
    return {"patient_id": patient_id, "provider": "Dr. Osei", "last_visit_days_ago": random.randint(1, 400)}


@healthcare.tool()
def check_care_gaps(patient_id: str) -> dict:
    """Check for overdue preventive-care or follow-up gaps for a patient."""
    return {"patient_id": patient_id, "open_gaps": random.choice([[], ["Annual wellness visit overdue"]])}


@healthcare.tool()
def schedule_appointment(patient_id: str, slot: str = "next available") -> dict:
    """Schedule the next appointment slot for a patient."""
    return {"patient_id": patient_id, "slot": slot, "scheduled": True}


# ---------------------------------------------------------------------------
# travel
# ---------------------------------------------------------------------------
travel = _mcp("travel", "Travel & hospitality: booking details, loyalty status, and rebooking.")


@travel.tool()
def get_booking_details(booking_id: str) -> dict:
    """Retrieve itinerary, connection times, and cabin/seat status for a booking."""
    return {"booking_id": booking_id, "connection_minutes": random.randint(30, 240), "cabin_waitlist": random.choice([True, False])}


@travel.tool()
def check_loyalty_status(traveler_id: str) -> dict:
    """Retrieve a traveler's loyalty tier and available upgrade offers."""
    return {"traveler_id": traveler_id, "tier": random.choice(["Bronze", "Silver", "Gold", "Platinum"]), "upgrade_available": random.choice([True, False])}


@travel.tool()
def rebook_reservation(booking_id: str) -> dict:
    """Rebook a reservation onto the next viable itinerary."""
    return {"booking_id": booking_id, "rebooked": True, "new_itinerary": "next available connection"}


# ---------------------------------------------------------------------------
# media
# ---------------------------------------------------------------------------
media = _mcp("media", "Media & entertainment: viewer profiles, stream health, and content recommendations.")


@media.tool()
def get_viewer_profile(viewer_id: str) -> dict:
    """Retrieve a viewer's tier and recent-genre watch history."""
    return {"viewer_id": viewer_id, "tier": random.choice(["free", "premium"]), "top_genre": random.choice(["sci-fi thriller", "cooking", "documentary"])}


@media.tool()
def check_stream_health(session_id: str) -> dict:
    """Check current playback health (buffering, bitrate) for a session."""
    return {"session_id": session_id, "buffering_events": random.randint(0, 10), "current_bitrate_mbps": round(random.uniform(2.0, 15.0), 1)}


@media.tool()
def recommend_content(viewer_id: str) -> dict:
    """Return the next recommended title for a viewer."""
    return {"viewer_id": viewer_id, "recommendation": "Deep Field Docs"}


# ---------------------------------------------------------------------------
# saas
# ---------------------------------------------------------------------------
saas = _mcp("saas", "SaaS / IT services: tenant usage, multi-tenant health, and cost estimation.")


@saas.tool()
def get_tenant_usage(tenant_id: str) -> dict:
    """Retrieve a tenant's current API call volume and active-user count."""
    return {"tenant_id": tenant_id, "api_calls_today": random.randint(1000, 5000000), "active_users": random.randint(5, 2500)}


@saas.tool()
def check_multi_tenant_health(tenant_id: str) -> dict:
    """Check a tenant's current API error rate and infra pool health."""
    return {"tenant_id": tenant_id, "error_rate_pct": round(random.uniform(0.0, 5.0), 2)}


@saas.tool()
def estimate_cost_savings(tenant_id: str) -> dict:
    """Estimate cost savings from right-sizing a tenant's plan tier."""
    return {"tenant_id": tenant_id, "estimated_monthly_savings_usd": random.randint(50, 4000)}


# ---------------------------------------------------------------------------
# manufacturing
# ---------------------------------------------------------------------------
manufacturing = _mcp("manufacturing", "Manufacturing & supply chain: shipment status, IoT sensors, and supply risk.")


@manufacturing.tool()
def get_shipment_status(shipment_id: str) -> dict:
    """Retrieve current ETA and delay status for a shipment."""
    return {"shipment_id": shipment_id, "delay_days": random.randint(0, 5), "eta_days": random.randint(1, 7)}


@manufacturing.tool()
def check_iot_sensor(asset_id: str) -> dict:
    """Check current in-transit sensor telemetry (temperature/shock) for a shipment or asset."""
    return {"asset_id": asset_id, "sensor_temp_c": random.randint(15, 45), "status": random.choice(["normal", "alert"])}


@manufacturing.tool()
def flag_supply_risk(supplier_id: str) -> dict:
    """Flag a supplier as at-risk and suggest alternate qualified suppliers."""
    return {"supplier_id": supplier_id, "alternate_suppliers": ["Ridgeline Fasteners", "Norwood Alloys"], "risk": random.choice(["low", "medium", "high"])}


# ---------------------------------------------------------------------------
# energy
# ---------------------------------------------------------------------------
energy = _mcp("energy", "Energy & utilities: grid telemetry, field-team dispatch, and load forecasting.")


@energy.tool()
def get_grid_telemetry(feeder_id: str) -> dict:
    """Retrieve current load vs. capacity for a grid feeder."""
    return {"feeder_id": feeder_id, "load_mw": round(random.uniform(15, 60), 1), "capacity_mw": round(random.uniform(35, 65), 1)}


@energy.tool()
def dispatch_field_team(incident_id: str) -> dict:
    """Dispatch the nearest available field crew to an incident or feeder."""
    return {"incident_id": incident_id, "crew_dispatched": "Crew 4 (12 min ETA)", "dispatched": True}


@energy.tool()
def forecast_load(region: str) -> dict:
    """Forecast peak load for a region over the next 24 hours."""
    return {"region": region, "forecast_peak_mw": round(random.uniform(30, 70), 1)}


# ---------------------------------------------------------------------------
# public_sector
# ---------------------------------------------------------------------------
public_sector = _mcp("public_sector", "Public sector & education: citizen case lookup, identity verification, and routing.")


@public_sector.tool()
def get_citizen_case(case_id: str) -> dict:
    """Retrieve a citizen service case's status and SLA clock."""
    return {"case_id": case_id, "days_open": random.randint(1, 60), "priority": random.choice(["standard", "high"])}


@public_sector.tool()
def verify_identity(citizen_id: str) -> dict:
    """Run identity verification for a citizen against the identity provider."""
    return {"citizen_id": citizen_id, "verified": random.choice([True, False])}


@public_sector.tool()
def route_service_request(case_id: str) -> dict:
    """Route a service request to the appropriate department queue."""
    return {"case_id": case_id, "routed_to": random.choice(["Benefits", "Permits", "Records", "Research Data Services"])}


SERVERS: dict[str, FastMCP] = {
    "retail": retail,
    "banking": banking,
    "telecom": telecom,
    "healthcare": healthcare,
    "travel": travel,
    "media": media,
    "saas": saas,
    "manufacturing": manufacturing,
    "energy": energy,
    "public_sector": public_sector,
}


async def healthz(request):
    return JSONResponse({"status": "ok", "servers": list(SERVERS.keys())})


async def list_servers(request):
    """Convenience listing so scripts/register_with_aom.py (or a curious
    operator) can see what's bundled here without reading this file."""
    return JSONResponse(
        {
            "servers": [
                {"id": server_id, "mcp_url": f"/{server_id}/mcp", "instructions": mcp.instructions}
                for server_id, mcp in SERVERS.items()
            ]
        }
    )


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with contextlib.AsyncExitStack() as stack:
        for server_id, mcp in SERVERS.items():
            await stack.enter_async_context(mcp.session_manager.run())
            logger.info("MCP server '%s' ready at /%s/mcp", server_id, server_id)
        yield


routes = [
    Route("/healthz", healthz),
    Route("/servers", list_servers),
]
for server_id, mcp in SERVERS.items():
    routes.append(Mount(f"/{server_id}", app=mcp.streamable_http_app()))

app = Starlette(debug=False, routes=routes, lifespan=lifespan)
