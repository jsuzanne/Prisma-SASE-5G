"""Prisma 5G RAN Agent — minimal HTTP API on the UERANSIM host.

Exposes ONLY /api/agent/* and /healthz. The full UI / SCM API is never mounted
here. Every /api/agent/* call must carry `X-Agent-Token: $AGENT_TOKEN`.

Start (see entrypoint.sh, ROLE=ue-agent):
    uvicorn agent_app:app --host ${AGENT_BIND:-10.10.10.2} --port ${AGENT_PORT:-8081}
"""

import hmac
import logging
import os
import threading
import time
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.ran_agent import DEBUG, RanAgent, clean_imsi, recent_events

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
logger = logging.getLogger("AgentApp")
logger.info("RAN Agent starting (DEBUG=%s)", DEBUG)

AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")
app = FastAPI(title="Prisma 5G RAN Agent", docs_url=None, redoc_url=None, openapi_url=None)
agent = RanAgent()

# Serialize control actions per IMSI (two Power On clicks must not spawn two nr-ue).
_locks: dict = {}
_locks_guard = threading.Lock()


def _lock_for(imsi: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(imsi, threading.Lock())


@app.middleware("http")
async def require_token(request: Request, call_next):
    rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:8]
    path = request.url.path
    client = request.client.host if request.client else "?"
    t0 = time.monotonic()
    if path.startswith("/api/agent/"):
        if not AGENT_TOKEN:
            logger.error("req=%s %s %s from=%s -> 503 AGENT_TOKEN not set", rid, request.method, path, client)
            return JSONResponse({"detail": "Agent misconfigured: AGENT_TOKEN not set"}, status_code=503)
        supplied = request.headers.get("X-Agent-Token", "")
        if not hmac.compare_digest(supplied, AGENT_TOKEN):
            logger.warning("req=%s %s %s from=%s -> 401 bad/missing token", rid, request.method, path, client)
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    elif path != "/healthz":
        logger.warning("req=%s %s %s from=%s -> 404 (not an agent route)", rid, request.method, path, client)
        return JSONResponse({"detail": "Not found"}, status_code=404)
    response = await call_next(request)
    ms = round((time.monotonic() - t0) * 1000)
    response.headers["X-Request-Id"] = rid
    # Polling routes are logged only in DEBUG; control actions are always logged.
    noisy = request.method == "GET"
    level = logging.DEBUG if noisy else logging.INFO
    if response.status_code >= 400:
        level = logging.WARNING
    logger.log(level, "req=%s %s %s from=%s -> %s in %sms", rid, request.method, path, client, response.status_code, ms)
    return response


class StartPayload(BaseModel):
    yaml: str
    timeout_s: float = 15.0


class TrafficPayload(BaseModel):
    traffic_type: str = "allowed"
    target_url: Optional[str] = None


@app.get("/healthz")
def healthz():
    return {"ok": True, "role": "ue-agent", "token_configured": bool(AGENT_TOKEN), "debug": DEBUG}


@app.get("/api/agent/events")
def events(limit: int = 100, imsi: Optional[str] = None):
    """Recent agent events (newest first): start/stop steps, state transitions, errors."""
    return {"debug": DEBUG, "events": recent_events(limit, clean_imsi(imsi) if imsi else None)}


@app.get("/api/agent/telemetry")
def telemetry():
    return agent.telemetry()


@app.get("/api/agent/ue/{imsi}")
def ue_state(imsi: str):
    return agent.ue_state(imsi)


@app.post("/api/agent/ue/{imsi}/start")
def start_ue(imsi: str, payload: StartPayload):
    imsi = clean_imsi(imsi)
    lock = _lock_for(imsi)
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail=f"Action already in progress for {imsi}")
    try:
        return agent.start_ue(imsi, payload.yaml, timeout_s=min(max(payload.timeout_s, 3.0), 30.0))
    finally:
        lock.release()


@app.post("/api/agent/ue/{imsi}/stop")
def stop_ue(imsi: str):
    imsi = clean_imsi(imsi)
    lock = _lock_for(imsi)
    with lock:
        return agent.stop_ue(imsi)


@app.post("/api/agent/stop-all")
def stop_all():
    return agent.stop_all()


@app.post("/api/agent/cleanup-tuns")
def cleanup_tuns():
    return agent.cleanup_orphan_tuns()


@app.get("/api/agent/ue/{imsi}/logs")
def ue_logs(imsi: str, lines: int = 60):
    imsi = clean_imsi(imsi)
    text = agent.read_log(imsi)
    if not text:
        try:
            with open(agent.log_path(imsi) + ".prev", errors="replace") as f:
                text = f.read()
        except Exception:
            text = ""
    tail = "\n".join(text.splitlines()[-max(1, min(lines, 500)):])
    return {"imsi": imsi, "log_path": agent.log_path(imsi), "logs": tail, "lines": lines}


@app.post("/api/agent/ue/{imsi}/traffic")
def ue_traffic(imsi: str, payload: TrafficPayload):
    return agent.traffic(imsi, payload.traffic_type, payload.target_url)
