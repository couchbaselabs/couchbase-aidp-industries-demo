#!/usr/bin/env python3
"""
One-time setup: register this app's bundled industry MCP tool servers with
a running Couchbase Agent Operations Manager (AOM) appliance, and mint a
dedicated "aidp-industries-demo" agent identity for this app's backend to
authenticate with — so this app's LLM/MCP traffic shows up in AOM's
Agent Identities, Servers, Traces, and Agent Tool Audit pages as its own
named agent rather than borrowing one of AOM's generic seeded demo keys.

AOM's server-registration and agent-identity endpoints (POST /v1/servers,
POST /v1/agents) are part of its *dashboard* admin surface, gated behind a
human-login session cookie — not the bearer-API-key path agents use for
discover/invoke/complete (see that appliance's app/main.py
UNPROTECTED_PATH_PREFIXES). This script logs in the same way the AOM
dashboard's login page does, then makes those calls with the resulting
session cookie.

Usage (after `docker compose up` on BOTH this repo and the AOM repo):

    python3 scripts/register_with_aom.py \\
        --aom-url https://localhost:8090 \\
        --admin-username admin --admin-password '<your AOM admin password>'

Run with --help for every option. Idempotent: re-running skips servers
that are already registered and reuses an existing "aidp-industries-demo"
agent identity's role rather than erroring, but note that AOM only ever
returns an agent's API key once — if you've lost it, use --recreate-agent
to revoke the old one and mint a fresh key.
"""
import argparse
import pathlib
import sys
import time

import requests

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"

AGENT_NAME = "aidp-industries-demo"
DEFAULT_ROLES = ["admin", "finance_analyst", "support_agent"]


def wait_for_health(session: requests.Session, base_url: str, timeout_s: int = 120) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            resp = session.get(f"{base_url}/api/health", verify=False, timeout=5)
            if resp.ok and resp.json().get("status") in ("ok", "starting"):
                print(f"AOM is reachable at {base_url} (status: {resp.json().get('status')}).")
                return
        except requests.RequestException:
            pass
        print("Waiting for AOM to become reachable...")
        time.sleep(3)
    raise SystemExit(f"Timed out waiting for AOM at {base_url}. Is `docker compose up` running for that repo?")


def ensure_logged_in(session: requests.Session, base_url: str, username: str, password: str) -> None:
    status = session.get(f"{base_url}/v1/auth/bootstrap-status", verify=False, timeout=10).json()
    if status.get("needs_setup"):
        print(f"AOM's admin account has no password set yet — bootstrapping it as '{username}'...")
        resp = session.post(f"{base_url}/v1/auth/bootstrap", json={"password": password}, verify=False, timeout=10)
        if not resp.ok:
            raise SystemExit(f"Bootstrap failed: HTTP {resp.status_code} {resp.text}")
        print("Bootstrap succeeded — admin password set and logged in.")
        return

    resp = session.post(f"{base_url}/v1/auth/login", json={"username": username, "password": password}, verify=False, timeout=10)
    if not resp.ok:
        raise SystemExit(
            f"Login failed: HTTP {resp.status_code} {resp.text}\n"
            "Pass the correct --admin-username/--admin-password for your running AOM appliance."
        )
    print(f"Logged in to AOM as '{username}'.")


def fetch_bundled_servers(mcp_servers_local_url: str) -> list:
    resp = requests.get(f"{mcp_servers_local_url}/servers", timeout=10)
    resp.raise_for_status()
    return resp.json()["servers"]


def register_servers(session: requests.Session, base_url: str, servers: list, mcp_base_url_for_aom: str) -> None:
    for server in servers:
        server_id = f"aidp-{server['id']}"
        mcp_url = f"{mcp_base_url_for_aom}{server['mcp_url']}"
        payload = {
            "server_id": server_id,
            "label": f"AIDP Demo — {server['id'].replace('_', ' ').title()}",
            "owner": "AIDP Industries Demo",
            "mcp_url": mcp_url,
            "trust_status": "trusted",
            "default_allowed_roles": DEFAULT_ROLES,
        }
        resp = session.post(f"{base_url}/v1/servers", json=payload, verify=False, timeout=20)
        if resp.status_code == 409:
            print(f"  [skip] '{server_id}' is already registered.")
            continue
        if not resp.ok:
            print(f"  [FAIL] '{server_id}': HTTP {resp.status_code} {resp.text}")
            continue
        body = resp.json()
        print(f"  [ok]   '{server_id}' -> {mcp_url} ({body.get('ingested_tools', 0)} tools ingested)")


def find_existing_agent(session: requests.Session, base_url: str) -> "dict | None":
    resp = session.get(f"{base_url}/v1/agents", verify=False, timeout=10)
    resp.raise_for_status()
    for agent in resp.json().get("agents", []):
        if agent.get("name") == AGENT_NAME:
            return agent
    return None


def create_agent(session: requests.Session, base_url: str) -> str:
    payload = {
        "name": AGENT_NAME,
        "role": "admin",
        "owner": "AIDP Industries Demo",
        "description": "Backend for the Couchbase AIDP Industries Demo app — one dashboard across ten industry verticals.",
        "allowed_tools": [],
        "expires_at": None,
    }
    resp = session.post(f"{base_url}/v1/agents", json=payload, verify=False, timeout=20)
    if not resp.ok:
        raise SystemExit(f"Failed to create agent identity: HTTP {resp.status_code} {resp.text}")
    body = resp.json()
    print(f"Created agent identity '{AGENT_NAME}' (role: admin). API key shown once below.")
    return body["api_key"]


def revoke_agent(session: requests.Session, base_url: str, agent_id: str) -> None:
    resp = session.post(f"{base_url}/v1/agents/{agent_id}/revoke", verify=False, timeout=10)
    if not resp.ok:
        print(f"  (could not revoke old agent {agent_id}: HTTP {resp.status_code} {resp.text})")


def write_api_key_to_env(api_key: str) -> None:
    if not ENV_PATH.exists() and ENV_EXAMPLE_PATH.exists():
        ENV_PATH.write_text(ENV_EXAMPLE_PATH.read_text())

    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    found = False
    for i, line in enumerate(lines):
        if line.startswith("AOM_API_KEY="):
            lines[i] = f"AOM_API_KEY={api_key}"
            found = True
            break
    if not found:
        lines.append(f"AOM_API_KEY={api_key}")
    ENV_PATH.write_text("\n".join(lines) + "\n")
    print(f"Wrote AOM_API_KEY into {ENV_PATH} — restart `docker compose up` on this repo to pick it up.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aom-url", default="https://localhost:8090", help="AOM's dashboard/API origin, reachable from THIS machine.")
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--admin-password", required=True, help="AOM admin password (used to bootstrap it on first run, or to log in).")
    parser.add_argument("--mcp-servers-local-url", default="http://localhost:8500", help="This app's mcp-servers container, reachable from THIS machine.")
    parser.add_argument("--mcp-base-url-for-aom", default="http://host.docker.internal:8500", help="This app's mcp-servers container, reachable from AOM's OWN container.")
    parser.add_argument("--recreate-agent", action="store_true", help="Revoke any existing 'aidp-industries-demo' agent identity and mint a fresh one.")
    parser.add_argument("--skip-write-env", action="store_true", help="Print the API key instead of writing it into .env.")
    args = parser.parse_args()

    session = requests.Session()
    requests.packages.urllib3.disable_warnings()  # noqa: SLF001 - self-signed cert by default, same posture as aom_gateway.py

    wait_for_health(session, args.aom_url)
    ensure_logged_in(session, args.aom_url, args.admin_username, args.admin_password)

    print("\nRegistering bundled industry MCP servers with AOM...")
    servers = fetch_bundled_servers(args.mcp_servers_local_url)
    register_servers(session, args.aom_url, servers, args.mcp_base_url_for_aom)

    print("\nSetting up this app's agent identity...")
    existing = find_existing_agent(session, args.aom_url)
    if existing and args.recreate_agent:
        print(f"Revoking existing agent identity '{AGENT_NAME}' ({existing['agent_id']})...")
        revoke_agent(session, args.aom_url, existing["agent_id"])
        existing = None

    if existing:
        print(
            f"Agent identity '{AGENT_NAME}' already exists (role: {existing['role']}). "
            "Its API key was only ever shown once at creation time — re-run with --recreate-agent "
            "if you need a fresh key."
        )
        return

    api_key = create_agent(session, args.aom_url)
    if args.skip_write_env:
        print(f"\nAOM_API_KEY={api_key}")
    else:
        write_api_key_to_env(api_key)
    print("\nDone. Start (or restart) this app's stack: docker compose up --build")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
