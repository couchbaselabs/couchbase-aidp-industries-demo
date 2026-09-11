"""
Central configuration for the Couchbase AIDP Industries Demo backend.

Everything here is read from the environment (with sane local-demo
defaults) so the same image runs unmodified across a laptop demo, a booth
demo, or a customer's own Docker host — see .env.example at the repo root.
"""
import os


def _bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Couchbase — the operational store for every industry's seed data, the
# per-entity agent-decision context cache, and the buyer/operator action
# audit log. One cluster, one bucket, shared across all ten industries
# (each document is namespaced by industry — see app/couchbase_client.py) —
# simpler to run than one bucket per vertical, and it's exactly the kind of
# shared "AI data plane" the demo is arguing for in the first place.
# ---------------------------------------------------------------------------
COUCHBASE_MGMT_URL = os.environ.get("COUCHBASE_MGMT_URL", "http://couchbase:8091")
COUCHBASE_QUERY_URL = os.environ.get("COUCHBASE_QUERY_URL", "http://couchbase:8093")
COUCHBASE_USERNAME = os.environ.get("COUCHBASE_USERNAME", "Administrator")
COUCHBASE_PASSWORD = os.environ.get("COUCHBASE_PASSWORD", "password123")
COUCHBASE_BUCKET = os.environ.get("COUCHBASE_BUCKET", "aidp_industries")

# Simulated cache-miss latency for a "cold" lookup against a mocked
# system-of-record (an ERP, a core banking ledger, an EHR, ...) — see
# context_cache.py. A cache hit is always near-instant; this is what makes
# the caching benefit visible in the UI, the same device the reference
# Procurement Command Center app uses.
CONTEXT_CACHE_MISS_LATENCY_MS = int(os.environ.get("CONTEXT_CACHE_MISS_LATENCY_MS", "650"))
CONTEXT_CACHE_TTL_SECONDS = int(os.environ.get("CONTEXT_CACHE_TTL_SECONDS", "600"))

# ---------------------------------------------------------------------------
# Couchbase Agent Operations Manager (AOM) — a separate docker-compose
# stack on the same machine by default (see README "Running both stacks").
# This backend talks to it through the real aom_sdk Python client
# (vendored at backend/vendor/aom-sdk — see app/aom_gateway.py), never by
# holding a model-provider API key directly.
# ---------------------------------------------------------------------------
AOM_BASE_URL = os.environ.get("AOM_BASE_URL", "https://host.docker.internal:8090")
AOM_API_KEY = os.environ.get("AOM_API_KEY", os.environ.get("AOM_API_KEY_ADMIN", "demo-admin-4c56"))
AOM_VERIFY_SSL = _bool("AOM_VERIFY_SSL", False)
AOM_PROVIDER = os.environ.get("AOM_PROVIDER", "")  # empty = use AOM's own admin-configured default
AOM_MODEL = os.environ.get("AOM_MODEL", "")
AOM_AGENT_ID = os.environ.get("AOM_AGENT_ID", "aidp-industries-demo")
AOM_REQUEST_TIMEOUT_SECONDS = float(os.environ.get("AOM_REQUEST_TIMEOUT_SECONDS", "20"))

# Where this backend's own bundled MCP tool servers are reachable *from
# AOM's operations-manager container* — used only by
# scripts/register_with_aom.py when it registers them with AOM, not by the
# backend itself (the backend never calls the MCP servers directly; it
# always goes through AOM's discover/invoke gateway, the same governed
# path a real agent fleet would use).
INDUSTRY_MCP_SERVERS_URL_FOR_AOM = os.environ.get(
    "INDUSTRY_MCP_SERVERS_URL_FOR_AOM", "http://host.docker.internal:8500"
)

APP_NAME = os.environ.get("APP_NAME", "Couchbase AIDP Industries Demo")
PORT = int(os.environ.get("PORT", "4100"))
