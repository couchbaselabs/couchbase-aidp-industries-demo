"""
Minimal Couchbase client built on the cluster's public REST + N1QL HTTP
interfaces (`requests`), the same "no native SDK bindings" choice the
reference Procurement Command Center app made for its Node backend
(backend/src/db/couchbase.js) — ported here almost statement-for-statement,
generalized from one bucket-per-app to one bucket shared across all ten
industries in this app.

This module is also the "AI data plane" context cache described in the
README: every agent decision, keyed by industry + entity, is stored as a
document here so a repeat look — another operator re-opening the same
record, or the same record shown twice in a session — is served from
Couchbase instead of recomputed against the (simulated) system of record.
"""
import base64
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from app.config import (
    COUCHBASE_BUCKET,
    COUCHBASE_MGMT_URL,
    COUCHBASE_PASSWORD,
    COUCHBASE_QUERY_URL,
    COUCHBASE_USERNAME,
)

logger = logging.getLogger("aidp.couchbase")


def _auth_header() -> str:
    token = base64.b64encode(f"{COUCHBASE_USERNAME}:{COUCHBASE_PASSWORD}".encode()).decode()
    return f"Basic {token}"


class CouchbaseClient:
    """Thin REST/N1QL client + one-time cluster bootstrap, scoped to one
    shared bucket (`COUCHBASE_BUCKET`) for every industry's seed data,
    context-cache entries, and operator-action audit log."""

    def __init__(self) -> None:
        self.bucket = COUCHBASE_BUCKET
        self._session = requests.Session()

    # -- low-level HTTP -----------------------------------------------------
    def _mgmt(self, path: str, method: Optional[str] = None, data: Optional[dict] = None, auth: bool = True):
        resolved_method = method or ("POST" if data is not None else "GET")
        headers = {}
        if auth:
            headers["Authorization"] = _auth_header()
        payload = None
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            payload = data
        return self._session.request(
            resolved_method, f"{COUCHBASE_MGMT_URL}{path}", headers=headers, data=payload, timeout=15
        )

    def query(self, statement: str, **named_params: Any) -> List[dict]:
        """Run a N1QL statement. Named parameters (`$key`, `$doc`, ...) must
        be sent as top-level `$`-prefixed request fields — Couchbase's Query
        REST API treats a positional `args` array as an entirely different
        wire format that never binds to a named placeholder. (This exact
        mismatch was a real, shipped bug in the reference app's first
        Couchbase integration — see that repo's README "Second real bug
        found" section — so it's called out here rather than repeated.)
        """
        body: Dict[str, Any] = {"statement": statement}
        for key, value in named_params.items():
            body[key if key.startswith("$") else f"${key}"] = value
        resp = self._session.post(
            f"{COUCHBASE_QUERY_URL}/query/service",
            headers={"Authorization": _auth_header(), "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        try:
            payload = resp.json()
        except ValueError:
            payload = {}
        if not resp.ok or payload.get("status") in ("fatal", "errors"):
            errors = payload.get("errors") or f"HTTP {resp.status_code}"
            raise RuntimeError(f"N1QL query failed: {errors} :: {statement[:200]}")
        return payload.get("results") or []

    # -- document CRUD (via N1QL, matching the reference app's approach) ----
    def upsert(self, key: str, doc: dict) -> None:
        self.query(f"UPSERT INTO `{self.bucket}` (KEY, VALUE) VALUES ($key, $doc)", key=key, doc=doc)

    def upsert_many(self, entries: List[Dict[str, Any]]) -> None:
        for entry in entries:
            self.upsert(entry["key"], entry["doc"])

    def get(self, key: str) -> Optional[dict]:
        rows = self.query(f"SELECT RAW `{self.bucket}` FROM `{self.bucket}` USE KEYS $key", key=key)
        return rows[0] if rows else None

    def remove(self, key: str) -> None:
        self.query(f"DELETE FROM `{self.bucket}` USE KEYS $key", key=key)

    def select_by_type(self, doc_type: str) -> List[dict]:
        return self.query(f"SELECT RAW t FROM `{self.bucket}` t WHERE t.type = $type", type=doc_type)

    def select_by_type_and_industry(self, doc_type: str, industry: str) -> List[dict]:
        return self.query(
            f"SELECT RAW t FROM `{self.bucket}` t WHERE t.type = $type AND t.industry = $industry",
            type=doc_type,
            industry=industry,
        )

    # -- cluster bootstrap ----------------------------------------------------
    def _cluster_initialized(self) -> bool:
        try:
            resp = self._mgmt("/pools/default")
        except requests.RequestException:
            return False
        if resp.status_code == 401:
            return True  # initialized, just not authenticated as us (shouldn't happen, but not fatal)
        if resp.status_code != 200:
            return False
        try:
            nodes = resp.json().get("nodes") or []
        except ValueError:
            return False
        return len(nodes) > 0

    def _bucket_exists(self) -> bool:
        try:
            resp = self._mgmt(f"/pools/default/buckets/{self.bucket}")
        except requests.RequestException:
            return False
        return resp.status_code == 200

    def _wait_for(self, fn, label: str, attempts: int = 60, delay_seconds: float = 2.0) -> None:
        last_error = None
        for _ in range(attempts):
            try:
                if fn():
                    return
            except Exception as exc:  # noqa: BLE001
                last_error = exc
            time.sleep(delay_seconds)
        suffix = f": {last_error}" if last_error else ""
        raise RuntimeError(f"Timed out waiting for {label}{suffix}")

    def init_cluster(self) -> None:
        """One-time cluster/bucket/primary-index bootstrap, safe to call on
        every backend startup (every step tolerates "already exists" —
        this only does real work on a fresh Couchbase container)."""
        logger.info("waiting for Couchbase node to accept connections...")

        def _node_up() -> bool:
            try:
                resp = self._session.get(f"{COUCHBASE_MGMT_URL}/pools", timeout=5)
                return resp.status_code < 500
            except requests.RequestException:
                return False

        self._wait_for(_node_up, "couchbase node")

        if not self._cluster_initialized():
            logger.info("performing first-time cluster setup via POST /clusterInit...")
            resp = self._mgmt(
                "/clusterInit",
                data={
                    "hostname": "127.0.0.1",
                    "services": "kv,n1ql,index",
                    "memoryQuota": "512",
                    "indexMemoryQuota": "256",
                    "indexerStorageMode": "plasma",
                    "clusterName": "couchbase-aidp-industries-demo",
                    "sendStats": "false",
                    "username": COUCHBASE_USERNAME,
                    "password": COUCHBASE_PASSWORD,
                    "port": "SAME",
                },
                auth=False,
            )
            if not resp.ok:
                raise RuntimeError(f"POST /clusterInit failed: HTTP {resp.status_code} {resp.text}")
            logger.info("/clusterInit succeeded.")
            time.sleep(3)

        self._wait_for(self._cluster_initialized, "cluster init")

        if not self._bucket_exists():
            logger.info("creating bucket '%s'...", self.bucket)
            resp = self._mgmt(
                "/pools/default/buckets",
                data={"name": self.bucket, "bucketType": "couchbase", "ramQuotaMB": "512", "flushEnabled": "1"},
            )
            if not resp.ok and resp.status_code != 202:
                raise RuntimeError(f"Failed to create bucket: HTTP {resp.status_code} {resp.text}")

        self._wait_for(self._bucket_exists, "bucket ready")
        time.sleep(4)  # give the query service a moment to see the new keyspace

        logger.info("ensuring primary index exists...")

        def _index_ready() -> bool:
            try:
                self.query(f"CREATE PRIMARY INDEX IF NOT EXISTS ON `{self.bucket}`")
                return True
            except RuntimeError as exc:
                logger.info("index not ready yet (%s), retrying...", exc)
                return False

        self._wait_for(_index_ready, "primary index", attempts=30, delay_seconds=3.0)
        logger.info("Couchbase cluster ready.")


couchbase = CouchbaseClient()
