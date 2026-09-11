"""
Couchbase AIDP Industries Demo — backend.

One FastAPI app, ten industry verticals (see app/industries/), a shared
Couchbase-backed context cache, and every LLM/MCP call routed through the
Couchbase Agent Operations Manager via the real aom_sdk client
(app/aom_gateway.py) — so this app's traffic lights up AOM's own Traces,
LLM Caching, and Agent Tool Audit pages exactly the way a real agent
fleet's would.
"""
import logging
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import aom_gateway, audit, copilot, decisions
from app.config import APP_NAME
from app.couchbase_client import couchbase
from app.demo_simulator import simulator
from app.industries import get_industry, list_industries

logging.basicConfig(level="INFO")
logger = logging.getLogger("aidp.main")

app = FastAPI(title=APP_NAME, version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"]
)

_ready = False
_startup_error = None


@app.on_event("startup")
def _startup() -> None:
    global _ready, _startup_error

    def _init():
        global _ready, _startup_error
        try:
            couchbase.init_cluster()
            _ready = True
            logger.info("Startup complete — %d industries loaded.", len(list_industries()))
        except Exception as exc:  # noqa: BLE001
            _startup_error = str(exc)
            logger.error("Couchbase bootstrap failed: %s", exc)

    threading.Thread(target=_init, daemon=True).start()


def _industry_summary(industry) -> dict:
    return {
        "id": industry.id,
        "name": industry.name,
        "tagline": industry.tagline,
        "icon": industry.icon,
        "examples": industry.examples,
        "color": industry.color,
        "entity_label": industry.entity_label,
        "entity_label_plural": industry.entity_label_plural,
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok" if _ready else ("starting" if not _startup_error else "degraded"),
        "appliance": APP_NAME,
        "startup_error": _startup_error,
        "industries": len(list_industries()),
    }


@app.get("/api/aom/status")
def aom_status():
    return aom_gateway.status()


@app.get("/api/industries")
def api_list_industries():
    return {"industries": [_industry_summary(i) for i in list_industries()]}


@app.get("/api/industries/{industry_id}")
def api_get_industry(industry_id: str):
    try:
        industry = get_industry(industry_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown industry")
    kpis = [{"id": k.id, "label": k.label, "value": k.compute(industry.seed_entities), "format": k.format} for k in industry.kpis]
    return {
        **_industry_summary(industry),
        "kpis": kpis,
        "agents": [{"id": a.id, "name": a.name, "description": a.description} for a in industry.agents],
        "copilot_actions": copilot.list_actions(industry),
        "roadmap": industry.roadmap,
        "mcp_namespace": industry.mcp_namespace,
        "entity_title_field": industry.entity_title_field,
        "entity_subtitle_field": industry.entity_subtitle_field,
    }


@app.get("/api/industries/{industry_id}/entities")
def api_list_entities(industry_id: str):
    try:
        industry = get_industry(industry_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown industry")
    return {"entities": industry.seed_entities}


@app.get("/api/industries/{industry_id}/entities/{entity_id}/decision")
def api_decide(industry_id: str, entity_id: str, session_id: str = ""):
    try:
        industry = get_industry(industry_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown industry")
    try:
        result = decisions.decide_for_entity(industry, entity_id, session_id=session_id or "operator")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


class ActionRequest(BaseModel):
    agent_id: str
    action: str
    operator: str = "demo-operator"


@app.post("/api/industries/{industry_id}/entities/{entity_id}/action")
def api_record_action(industry_id: str, entity_id: str, body: ActionRequest):
    try:
        get_industry(industry_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown industry")
    audit.record_action(industry_id, entity_id, body.agent_id, body.action, body.operator)
    return {"ok": True}


@app.get("/api/industries/{industry_id}/accuracy")
def api_accuracy(industry_id: str):
    try:
        get_industry(industry_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown industry")
    return {"agents": audit.agent_accuracy(industry_id)}


class CopilotRequest(BaseModel):
    action_id: str | None = None
    message: str | None = None
    entity_id: str | None = None
    session_id: str | None = None


@app.post("/api/industries/{industry_id}/copilot/chat")
def api_copilot_chat(industry_id: str, body: CopilotRequest):
    try:
        industry = get_industry(industry_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown industry")
    session_id = body.session_id or f"session-{uuid.uuid4().hex[:8]}"
    return copilot.chat(industry, body.action_id, body.message, body.entity_id, session_id)


class DemoStartRequest(BaseModel):
    industry_id: str
    operators: int = 25


@app.post("/api/demo/start")
def api_demo_start(body: DemoStartRequest):
    try:
        get_industry(body.industry_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown industry")
    simulator.start(body.industry_id, operators=max(1, min(body.operators, 200)))
    return simulator.status()


@app.post("/api/demo/stop")
def api_demo_stop():
    simulator.stop()
    return simulator.status()


@app.get("/api/demo/status")
def api_demo_status():
    return simulator.status()
