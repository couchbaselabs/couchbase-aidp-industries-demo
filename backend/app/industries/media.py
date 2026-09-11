"""Media, Entertainment & Gaming — digital streaming platforms, major betting/entertainment groups."""
from app.industries.base import Agent, AgentDecision, CopilotAction, Industry, KPI
from app.industries.utils import count_where, top_by

SEED_SESSIONS = [
    {"id": "SESS-9001", "viewer_name": "Harper Lin", "device": "Smart TV", "content_watched": "Nebula Heist S2", "genre": "sci-fi thriller", "watch_minutes": 52, "buffering_events": 6, "tier": "premium"},
    {"id": "SESS-9002", "viewer_name": "Diego Fuentes", "device": "Mobile", "content_watched": "Coastal Kitchens", "genre": "cooking", "watch_minutes": 18, "buffering_events": 0, "tier": "free"},
    {"id": "SESS-9003", "viewer_name": "Priya Shah", "device": "Console", "content_watched": "Rift Arena (multiplayer)", "genre": "action game", "watch_minutes": 74, "buffering_events": 9, "tier": "premium"},
    {"id": "SESS-9004", "viewer_name": "Connor Byrne", "device": "Smart TV", "content_watched": "Nebula Heist S2", "genre": "sci-fi thriller", "watch_minutes": 44, "buffering_events": 1, "tier": "premium"},
    {"id": "SESS-9005", "viewer_name": "Talia Rosen", "device": "Mobile", "content_watched": "Late Night Wrap-Up", "genre": "talk show", "watch_minutes": 9, "buffering_events": 0, "tier": "free"},
    {"id": "SESS-9006", "viewer_name": "Marcus Webb", "device": "Console", "content_watched": "Rift Arena (multiplayer)", "genre": "action game", "watch_minutes": 61, "buffering_events": 2, "tier": "premium"},
    {"id": "SESS-9007", "viewer_name": "Sofia Marino", "device": "Tablet", "content_watched": "Coastal Kitchens", "genre": "cooking", "watch_minutes": 5, "buffering_events": 4, "tier": "free"},
    {"id": "SESS-9008", "viewer_name": "Kwame Asante", "device": "Smart TV", "content_watched": "Deep Field Docs", "genre": "documentary", "watch_minutes": 68, "buffering_events": 0, "tier": "premium"},
]


def _stream_quality_agent(entity: dict, all_entities: list) -> AgentDecision:
    events = entity["buffering_events"]
    if events >= 6:
        rec, sev = "Switch to a nearer edge node and step down bitrate automatically", "critical"
        fallback = f"{entity['viewer_name']}'s session on {entity['device']} had {events} buffering events — recommend an edge/CDN reroute and adaptive bitrate step-down."
        confidence = 0.9
    elif events >= 2:
        rec, sev = "Monitor — pre-emptively lower peak bitrate", "warning"
        fallback = f"{events} buffering events this session — below the reroute threshold but worth a bitrate check."
        confidence = 0.7
    else:
        rec, sev = "Stream quality healthy — no action", "positive"
        fallback = f"{entity['viewer_name']}'s session had {events} buffering events — healthy playback."
        confidence = 0.85
    return AgentDecision(rec, fallback, confidence, "Buffering events", str(events), {"buffering_events": events, "device": entity["device"]}, sev)


def _recommendation_agent(entity: dict, all_entities: list) -> AgentDecision:
    genre = entity["genre"]
    same_genre = [e for e in all_entities if e["id"] != entity["id"] and e["genre"] == genre]
    next_title = same_genre[0]["content_watched"] if same_genre else "a trending title in a related genre"
    fallback = f"{entity['viewer_name']} watched {entity['watch_minutes']} minutes of {genre} content — recommend '{next_title}' next."
    return AgentDecision(
        f"Recommend next: {next_title}", fallback, 0.7, "Genre", genre,
        {"genre": genre, "watch_minutes": entity["watch_minutes"], "next_title": next_title}, "info",
    )


INDUSTRY = Industry(
    id="media",
    name="Media, Entertainment & Gaming",
    tagline="Stream quality and real-time recommendations across sessions, on one AI data plane.",
    icon="🎮",
    examples=["digital streaming platforms", "major betting/entertainment groups"],
    entity_label="Session",
    entity_label_plural="Sessions",
    entity_title_field="id",
    entity_subtitle_field="viewer_name",
    kpis=[
        KPI("active_sessions", "Active Sessions", lambda es: len(es)),
        KPI("quality_alerts", "Quality Alerts", lambda es: count_where(es, lambda e: e["buffering_events"] >= 2)),
        KPI("premium_sessions", "Premium-Tier Sessions", lambda es: count_where(es, lambda e: e["tier"] == "premium")),
        KPI("avg_watch", "Avg Watch Minutes", lambda es: round(sum(e["watch_minutes"] for e in es) / len(es), 1) if es else 0),
    ],
    agents=[
        Agent("stream-quality", "Stream Quality Agent", "Flags sessions with high buffering and recommends a CDN/bitrate action.", _stream_quality_agent, lambda e: f"check stream health for session {e['id']}"),
        Agent("content-recommendation", "Content Recommendation Agent", "Recommends the next title from the viewer's current genre.", _recommendation_agent, lambda e: f"get viewer profile for {e['viewer_name']}"),
    ],
    copilot_actions=[
        CopilotAction("priority", "My priority", lambda e, es: f"Worst stream quality: {top_by(es, lambda x: x['buffering_events'])['id']}."),
        CopilotAction("recommend-content", "Recommend content", lambda e, es: f"{e['viewer_name']} is watching {e['genre']} content." if e else "Select a session first.", lambda e: f"recommend content for {e['viewer_name']}" if e else "recommend content"),
        CopilotAction("viewer-profile", "Viewer profile", lambda e, es: f"{e['viewer_name']} on {e['device']}, {e['tier']} tier, {e['watch_minutes']} min watched." if e else "Select a session first."),
    ],
    mcp_namespace="media",
    seed_entities=SEED_SESSIONS,
    roadmap=[
        "Content streaming delivery infrastructure — this demo scores session-reported quality, not real CDN telemetry.",
        "High-concurrency multiplayer game backends — matchmaking/state-sync workloads aren't modeled here.",
        "Full session-management breadth — auth/entitlement handling isn't part of this demo's surface.",
    ],
    color="#c026d3",
)
