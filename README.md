# Couchbase AIDP Industries Demo

<img width="1728" height="961" alt="image" src="https://github.com/user-attachments/assets/40eb1f25-2560-45d4-b7f0-25695692be24" />
<img width="1728" height="963" alt="image" src="https://github.com/user-attachments/assets/170b783d-56d2-470d-b3c4-955d0d3f6918" />

A single Dockerized demo of Couchbase's AI data plane, generalized across
**ten industry verticals** a demo operator can switch between at runtime —
(Couchbase as the operational store + context cache, real LLM/MCP calls
routed through the [Couchbase Agent Operations Manager](../couchbase-agent-operations-manager)
so they show up in AOM's own dashboards), but as one switchable app instead
of one bespoke build per industry.

```
frontend (nginx, static JS SPA)  →  backend (FastAPI + aom_sdk)  →  couchbase (enterprise edition)
        :8081                              :4100                         :9191 / :9193
                                              │
                                              ▼
                          Couchbase Agent Operations Manager (separate stack)
                                        :8090 (API) / :443 (dashboard)
                                              │
                                              ▼
                     this app's own bundled industry MCP tool servers  (:8500)
```

## What this is

One dashboard shell — KPI cards, an AI Decision Feed, an entity detail
drawer with accept/reject, a Copilot chat panel, and an AI Architecture
page — implemented **once** and re-skinned per industry entirely from
backend data. Pick an industry on the landing screen and the whole app
becomes that industry: its own seed data, its own two working AI agents,
its own copilot quick actions, its own bundled MCP tools.

| # | Industry | Examples | Flagship agents (fully built) |
|---|----------|----------|-------------------------------|
| 1 | Retail & E-Commerce | Staples, Walmart, Tesco, Domino's | Inventory Rebalancing, Personalized Recommendation |
| 2 | Financial Services & Banking | American Express, global payment networks | Fraud Detection, Risk Management |
| 3 | Telecommunications | Comcast, BT | Billing Anomaly, Churn Risk |
| 4 | Healthcare & Life Sciences | HCA Healthcare, Signify Health, Maccabi | Care Gap, Appointment Optimization |
| 5 | Travel & Hospitality | Carnival Cruise Line, Amex GBT | Loyalty Upsell, Booking Risk |
| 6 | Media, Entertainment & Gaming | streaming platforms, betting/entertainment groups | Stream Quality, Content Recommendation |
| 7 | Software & IT Services (SaaS) | dev platforms, global SIs | Tenant Health, Cost Optimization |
| 8 | Manufacturing & Supply Chain | General Electric (GE) | Supply Risk, IoT Anomaly |
| 9 | Energy & Utilities | PG&E | Grid Load, Outage Risk |
| 10 | Public Sector & Education | university research labs, public agencies | Case Routing, Identity Verification |

Every industry's brief listed five use cases; this build implements two of
them end-to-end per industry (real seed data, real rule-based decision
logic, real AOM-narrated rationale, a real MCP tool cross-check) and names
the other three as roadmap on that industry's own **AI Architecture** tab
in the app — the same honest "built vs. documented" split the reference
Procurement Command Center app used for its wider 56-rule catalog, rather
than inventing depth that isn't really there. See each
`backend/app/industries/<name>.py` module's `roadmap` list, or the app
itself, for exactly what's marked as not-yet-built per industry.

## Why Couchbase, and why route through AOM

Same argument the reference app makes, generalized: Couchbase is the
"AI data plane" — one operational store shared across every vertical,
doubling as the context cache that makes repeat lookups near-instant
(watch the `⚡ cache hit` vs. `↻ live` badge on any entity's decision
panel). Routing every LLM narration and MCP tool call through AOM instead
of holding a provider key or dialing tool servers directly means this
app's traffic is authenticated, RBAC-checked, audited, and cached
centrally — and it's what makes this app's activity show up on AOM's own
**Dashboard** (Live topology), **Traces**, **LLM Caching**, and **Agent
Tool Audit** pages exactly as a real agent fleet's would. This backend
uses the actual `aom_sdk` Python client (vendored at
`backend/vendor/aom-sdk` — see that folder's `VENDORED.md`), not AOM's raw
REST API, per this build's brief.

**Resilience**: if AOM isn't configured or isn't reachable, every agent
decision and every copilot reply falls back to its own deterministic,
rule-based text — this app works fully with no AOM running at all. The
"via AOM" / "rule-based fallback" tag on every recommendation and the
`AOM: connected` / `AOM: fallback mode` badge in the header tell you which
happened.

## Running it

### 1. This app's own stack

```bash
docker compose up --build
```

First boot takes 30–90 seconds while Couchbase initializes — the backend
polls and reports `starting` on `/api/health` until it's ready.

- App: <http://localhost:8081>
- API directly: <http://localhost:4100/api/...>
- Couchbase admin console: <http://localhost:9191> (Administrator /
  password123 — change `COUCHBASE_PASSWORD` for anything beyond a local
  demo. Remapped from the usual 8091/8093 to 9191/9193 so this can run
  alongside both AOM's own Couchbase cluster and the reference Procurement
  Command Center demo's, on the same machine.)
- This app's bundled MCP tool servers: <http://localhost:8500/servers>

To stop and wipe all data (Couchbase volume included): `docker compose
down -v`.

### 2. The Couchbase Agent Operations Manager (separate stack, optional but recommended)

```bash
cd /path/to/couchbase-agent-operations-manager
docker compose up --build
```

- AOM's dashboard: <https://localhost> (self-signed cert — expect a
  browser warning)
- AOM's API: <https://localhost:8090>

### 3. Register this app's MCP tools with AOM, and mint its agent identity

One-time (or whenever you want a fresh API key):

```bash
pip install requests
python3 scripts/register_with_aom.py \
    --aom-url https://localhost:8090 \
    --admin-username admin --admin-password '<your AOM admin password>'
```

This logs into AOM's dashboard API (the same way its login page does —
server registration and agent-identity issuance are dashboard-session
endpoints, not bearer-key ones), registers all ten bundled industry MCP
servers (`aidp-retail`, `aidp-banking`, ... — visible afterward on AOM's
**Servers** page), creates a dedicated `aidp-industries-demo` agent
identity with the `admin` role (visible on **Agent Identities**), and
writes its one-time API key into this repo's `.env` as `AOM_API_KEY`.
Restart this app's stack afterward to pick it up:
`docker compose up --build`.

Skipping this step is fine for a quick look — the app defaults to AOM's
seeded `demo-admin-4c56` key, which already works against a freshly
started AOM appliance — but the dedicated identity is what makes this
app's activity legible as its own agent on AOM's pages instead of blending
into whatever else is using the generic seeded admin key.

### Corporate networks / TLS-inspecting proxies

Same three-part story as the reference apps (Alpine/apk over plain HTTP
just long enough to install `ca-certificates`, a corporate CA baked into
each build context, and the Docker Engine/daemon-level trust that no
Dockerfile can fix) — run `./scripts/setup-corporate-ca.sh` (macOS) before
`docker compose build` if you're behind one, or see the reference
Procurement Command Center app's README for the full breakdown of all
three failure modes and fixes; they apply here unchanged.

## Configuration

See `.env.example` for the full list. The important ones:

| Variable | Default | What it does |
|---|---|---|
| `AOM_BASE_URL` | `https://host.docker.internal:8090` | Where AOM's operations-manager API is reachable from this app's backend container. |
| `AOM_API_KEY` | `demo-admin-4c56` (AOM's seeded admin key) | Bearer credential for AOM. `register_with_aom.py` replaces this with a dedicated agent identity's key. |
| `AOM_VERIFY_SSL` | `false` | AOM serves HTTPS with a self-signed cert by default — set true once a real cert is installed. |
| `AOM_PROVIDER` / `AOM_MODEL` | empty (use AOM's own default) | Pin this app to a specific model regardless of AOM's admin-configured default. |
| `COUCHBASE_PASSWORD` | `password123` | This app's own Couchbase cluster admin password. |

## Architecture notes

- **`backend/app/industries/`** — one module per vertical: seed data
  (8 entities), two `Agent`s (pure decision functions), KPI definitions,
  copilot quick actions, and a `roadmap` list of the use cases from that
  industry's brief that aren't built. `backend/app/industries/base.py`
  defines the shared shape every module plugs into — that shared shape,
  plus one dashboard/copilot/context-cache implementation
  (`backend/app/decisions.py`, `copilot.py`, `context_cache.py`,
  `frontend/public/app.js`) reused across all ten, is what makes ten
  verticals tractable in one build instead of ten bespoke apps.
- **`backend/app/couchbase_client.py`** — REST/N1QL client and one-time
  cluster/bucket/index bootstrap, ported from the reference Procurement
  Command Center app's `backend/src/db/couchbase.js` (same reasoning: no
  native Couchbase SDK bindings, since everything needed — KV upserts,
  N1QL queries, cluster bootstrap — is reachable over plain HTTP). One
  shared bucket (`aidp_industries`) across all ten industries, documents
  namespaced by industry.
- **`backend/app/context_cache.py`** — the AI-data-plane cache: an agent
  decision for one entity is computed once (with a simulated fan-out
  latency to that industry's mocked system of record), then cached in
  Couchbase; a repeat look is a near-instant hit. Same visible-latency
  device the reference app uses.
- **`backend/app/aom_gateway.py`** — the only place this app calls
  `aom_sdk`. Every helper here (`narrate()`, `discover_and_invoke()`,
  `add_memory()`, ...) is fallback-safe: AOM being unset, unreachable, or
  erroring never breaks the request it's decorating.
- **`mcp-servers/`** — this app's own bundled MCP tool servers (FastMCP,
  same pattern as AOM's `sample-mcp-servers`), one namespace per industry,
  three mock tools each. Registered with AOM by `register_with_aom.py`.
- **`backend/app/demo_simulator.py`** — the Settings tab's "simulate N
  operators" background load generator, so Couchbase's context-cache hit
  rate and AOM's LLM-cache hit rate climb the way they would under real
  concurrent usage, for whichever industry is selected.
- **`backend/app/audit.py`** — the accept/reject log behind each
  industry's "Agent accuracy" panel (the reference app's "Trust Layer"
  buyer-behavior logging, generalized).

## What's been verified vs. what to verify on your machine

This build was done from a cloud sandbox linked to your Mac's filesystem,
not a machine that can pull Docker images or run containers — so every
Python module was syntax-checked, and the compose file was validated with
`docker compose config` run on your actual machine (see the delivery
message for that result), but a full `docker compose up --build` end-to-
end run — the Couchbase `/clusterInit` bootstrap sequence in particular,
which the reference apps' own READMEs note is exactly the kind of thing
that only surfaces against a real container — still needs to happen on
your machine to be certain. If `backend/app/couchbase_client.py`'s
bootstrap needs any adjustment after that first real run, that file (and
its close relative, the reference Procurement Command Center app's
`backend/src/db/couchbase.js`, if you want a second working example to
diff against) is the only place involved.

## License

Internal Couchbase demo tooling, in the same spirit as the reference
Procurement Command Center and Agent Operations Manager repos it's built
from — not an open-source release.
