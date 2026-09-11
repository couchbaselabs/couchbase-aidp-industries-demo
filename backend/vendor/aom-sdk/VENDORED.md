# Vendored: Couchbase Agent Operations Manager SDK

This directory is a vendored copy of `aom_sdk`, the official Python client
for the Couchbase Agent Operations Manager, copied from the sibling
`couchbase-agent-operations-manager` repo's `operations-manager/sdk/`
folder (MIT licensed — see `LICENSE` in this directory) so that
`docker compose build` here doesn't require that repo to be checked out
alongside this one.

It is installed unmodified via `pip install ./vendor/aom-sdk` in
`backend/Dockerfile`. If you upgrade the AOM appliance, re-copy this
folder's `aom_sdk/` package and `pyproject.toml` from that repo's SDK
folder to pick up client changes.

See that project's own `operations-manager/sdk/README.md` for the SDK's
full documentation (discover/invoke/complete, agent memory, MCP tool
integration, error handling) — `backend/app/aom_gateway.py` in this repo
is a thin, fallback-safe wrapper around it.
