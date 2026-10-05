"""Ground-truth reconciler — one snapshot of every SIM across the 4 pillars.

Every ~3s it collects:
  1. RAN agent telemetry  (nr-ue process + kernel uesimtun, per IMSI)
  2. AMF /ue-info         (mm_state registered / deregistered)
  3. SMF /pdu-info        (allocated IP + pdu_state)
  4. MongoDB subscribers  (Open5GS provisioning)
  5. SCM inventory        (every ~30s, API rate limits; last good copy kept + age)

and computes ONE status per SIM. Every API / UI view reads this snapshot, so
Fleet View, UE Mappings and Live Telemetry can never disagree.

Status rules (first match wins):
  unknown         agent or 5G core API unreachable  -> never prune, never guess
  active          nr-ue alive + kernel TUN with IP + AMF registered + TUN IP == SMF IP
  starting        Power On requested < 30s ago, not active yet
  failed          nr-ue alive but registration/TUN setup failed (reason from radio log)
  inconsistent    pillars disagree for >= 2 consecutive cycles (reason explains which)
  scm_only        in SCM, not provisioned in MongoDB
  core_only       in MongoDB (managed), not in SCM
  offline         no nr-ue process, no TUN

`live_ip` is set ONLY when status == active.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("Reconciler")
DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes", "on")

BASELINE_IMSIS = {"901700000000001", "999700000000001"}
STARTING_WINDOW_S = 30.0
INCONSISTENT_CONFIRM_CYCLES = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _supi_imsi(supi: str) -> str:
    return str(supi or "").replace("imsi-", "")


def compute_sim_state(
    imsi: str,
    agent_ok: bool,
    agent_error: Optional[str],
    core_ok: bool,
    radio: Optional[Dict[str, Any]],
    amf: Optional[Dict[str, Any]],
    smf: Optional[Dict[str, Any]],
    in_mongo: Optional[bool],
    managed: bool,
    scm: Optional[Dict[str, Any]],
    scm_ok: bool,
    starting_since: Optional[float],
    now: float,
) -> Dict[str, Any]:
    """Pure decision function: returns {status, live_ip, interface, reason, candidate_inconsistent}."""
    radio = radio or {"radio_state": "stopped", "reason": "no nr-ue process and no log for this IMSI"}
    rs = radio.get("radio_state", "stopped")
    amf_state = (amf or {}).get("mm_state") or ("absent" if core_ok else "unknown")
    smf_ip = (smf or {}).get("ipv4")
    smf_pdu = (smf or {}).get("pdu_state")
    tun_ip, iface = radio.get("ip"), radio.get("interface")
    starting = starting_since is not None and (now - starting_since) < STARTING_WINDOW_S

    def out(status, reason, live=False, cand=False):
        return {"status": status, "reason": reason, "candidate_inconsistent": cand,
                "live_ip": tun_ip if live else None, "interface": iface if live else None}

    if not agent_ok:
        return out("unknown", f"RAN agent unreachable — radio/TUN state cannot be verified ({agent_error})")

    if rs == "active":
        if not core_ok:
            return out("unknown", f"radio up on {iface}={tun_ip} but 5G Core API unreachable — cannot confirm session")
        if amf_state != "registered":
            return out("inconsistent", f"kernel {iface}={tun_ip} up but AMF mm_state={amf_state}", cand=True)
        if not smf_ip:
            return out("inconsistent", f"kernel {iface}={tun_ip} up but SMF has no PDU session for this IMSI", cand=True)
        if smf_ip != tun_ip:
            return out("inconsistent", f"kernel {iface}={tun_ip} but SMF allocated {smf_ip}", cand=True)
        return out("active", f"nr-ue PID {radio.get('pid')} + kernel {iface}={tun_ip} + AMF registered + SMF {smf_ip}",
                   live=True)

    if rs == "failed":
        return out("failed", radio.get("last_error") or radio.get("reason") or "radio failure")

    if starting:
        return out("starting", f"Power On in progress ({int(now - starting_since)}s): {radio.get('reason')}")

    if rs == "connecting":
        return out("inconsistent", f"nr-ue alive but not active: {radio.get('reason')}", cand=True)

    # radio stopped
    if core_ok and amf_state == "registered" and smf_pdu == "active":
        return out("inconsistent", f"no nr-ue process but core still shows AMF registered + SMF session {smf_ip}",
                   cand=True)
    if scm_ok and scm is not None and in_mongo is False:
        return out("scm_only", "registered in SCM but not provisioned in Open5GS MongoDB")
    if in_mongo and managed and scm_ok and scm is None:
        return out("core_only", "provisioned in MongoDB but not registered in SCM")
    return out("offline", radio.get("reason") or "no nr-ue process")


class Reconciler:
    def __init__(
        self,
        ran,
        core,
        scm_fetcher: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        interval_s: float = float(os.environ.get("RECONCILE_INTERVAL_S", "3")),
        scm_interval_s: float = float(os.environ.get("SCM_POLL_INTERVAL_S", "30")),
    ):
        self.ran = ran
        self.core = core
        self.scm_fetcher = scm_fetcher
        self.interval_s = interval_s
        self.scm_interval_s = scm_interval_s
        self._snapshot: Optional[Dict[str, Any]] = None
        self._cycle_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._starting: Dict[str, float] = {}
        self._incons_count: Dict[str, int] = {}
        self._scm_cache: Optional[List[Dict[str, Any]]] = None
        self._scm_at = 0.0
        self._scm_error: Optional[str] = None
        self._scm_attempt_at = 0.0
        self._events: deque = deque(maxlen=500)
        self._listeners: List[Callable[[Dict[str, Any], Optional[Dict[str, Any]], Dict[str, Any]], None]] = []

    # ---- public ----------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="reconciler", daemon=True)
        self._thread.start()
        logger.info("event=reconciler.start interval_s=%s scm_interval_s=%s debug=%s",
                    self.interval_s, self.scm_interval_s, DEBUG)

    def stop(self) -> None:
        self._stop.set()

    def snapshot(self, max_age_s: float = 10.0) -> Dict[str, Any]:
        snap = self._snapshot
        if snap is None or (time.time() - snap["_epoch"]) > max_age_s:
            snap = self.refresh_now()
        return snap

    def refresh_now(self, refresh_scm: bool = False) -> Dict[str, Any]:
        if refresh_scm:
            self._scm_attempt_at = 0.0
        return self._cycle(fetch_scm_if_due=refresh_scm or self._snapshot is None)

    def mark_starting(self, imsi: str) -> None:
        self._starting[imsi] = time.time()
        self._event(logging.INFO, "state.power_on_requested", imsi)

    def clear_starting(self, imsi: str) -> None:
        self._starting.pop(imsi, None)

    def add_listener(self, fn) -> None:
        """fn(sim_now, sim_before_or_None, snapshot) on every status/IP change (Phase 3 hooks)."""
        self._listeners.append(fn)

    def events(self, limit: int = 100, imsi: Optional[str] = None) -> List[Dict[str, Any]]:
        items = list(self._events)
        if imsi:
            items = [e for e in items if e.get("imsi") == imsi]
        return items[:max(1, min(limit, 500))]

    # ---- internals -------------------------------------------------------
    def _event(self, level: int, name: str, imsi: Optional[str] = None, **detail: Any) -> None:
        rec = {"ts": _now_iso(), "level": logging.getLevelName(level), "event": name, "imsi": imsi, **detail}
        kv = " ".join(f'{k}="{v}"' if isinstance(v, str) and " " in v else f"{k}={v}" for k, v in detail.items())
        logger.log(level, "event=%s%s %s", name, f" imsi={imsi}" if imsi else "", kv)
        if level >= logging.INFO or DEBUG:
            self._events.appendleft(rec)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._cycle(fetch_scm_if_due=True)
            except Exception as e:  # never let the loop die
                logger.exception("event=reconciler.cycle_error error=%r", str(e))
            self._stop.wait(self.interval_s)

    def _fetch_core(self):
        amf = smf = None
        mongo: Optional[Dict[str, Dict[str, Any]]] = None
        try:
            amf_raw = self.core._http_get(f"{self.core.amf_url}/ue-info?page=-1")
            if isinstance(amf_raw, dict):
                amf = {_supi_imsi(i.get("supi")): i for i in amf_raw.get("items", [])}
        except Exception as e:
            logger.warning("event=reconciler.amf_error error=%r", str(e))
        try:
            smf_raw = self.core._http_get(f"{self.core.smf_url}/pdu-info?page=-1")
            if isinstance(smf_raw, dict):
                smf = {}
                for i in smf_raw.get("items", []):
                    pdus = i.get("pdu", [])
                    if pdus:
                        # prefer an active PDU if several
                        p = next((x for x in pdus if x.get("pdu_state") == "active"), pdus[0])
                        smf[_supi_imsi(i.get("supi"))] = p
        except Exception as e:
            logger.warning("event=reconciler.smf_error error=%r", str(e))
        try:
            db = self.core.mongo_db
            if db is not None:
                mongo = {str(d.get("imsi")): d for d in db.subscribers.find({}, {"_id": 0, "imsi": 1, "managed_by": 1})}
        except Exception as e:
            logger.warning("event=reconciler.mongo_error error=%r", str(e))
        return amf, smf, mongo

    def _fetch_scm(self, due: bool) -> None:
        if not self.scm_fetcher or not due:
            return
        if (time.time() - self._scm_attempt_at) < self.scm_interval_s:
            return
        self._scm_attempt_at = time.time()
        t0 = time.monotonic()
        try:
            self._scm_cache = self.scm_fetcher()
            self._scm_at = time.time()
            self._scm_error = None
            self._event(logging.DEBUG, "reconciler.scm_refresh", count=len(self._scm_cache),
                        ms=round((time.monotonic() - t0) * 1000))
        except Exception as e:
            self._scm_error = str(e)
            self._event(logging.WARNING, "reconciler.scm_error", error=str(e)[:200])

    def _cycle(self, fetch_scm_if_due: bool) -> Dict[str, Any]:
        with self._cycle_lock:
            t0 = time.monotonic()
            now = time.time()
            tele = self.ran.telemetry(max_age_s=0)
            agent_ok = bool(tele.get("ok"))
            amf, smf, mongo = self._fetch_core()
            core_ok = amf is not None and smf is not None
            self._fetch_scm(fetch_scm_if_due)
            scm_list = self._scm_cache
            scm_ok = scm_list is not None
            scm_by_imsi = {str(s.get("imsi")): s for s in (scm_list or [])}

            radio_by_imsi = {u["imsi"]: u for u in tele.get("ues", [])} if agent_ok else {}
            imsis = set(scm_by_imsi) | set(mongo or {}) | set(radio_by_imsi) | set(self._starting)
            # forget expired power-on marks
            for i, ts in list(self._starting.items()):
                if now - ts > STARTING_WINDOW_S:
                    self._starting.pop(i, None)

            prev = (self._snapshot or {}).get("sims", {})
            sims: Dict[str, Dict[str, Any]] = {}
            for imsi in sorted(imsis):
                radio = radio_by_imsi.get(imsi)
                a = (amf or {}).get(imsi)
                s = (smf or {}).get(imsi)
                mdoc = (mongo or {}).get(imsi)
                d = compute_sim_state(
                    imsi, agent_ok, tele.get("error"), core_ok, radio, a, s,
                    in_mongo=None if mongo is None else (mdoc is not None),
                    managed=bool(mdoc and mdoc.get("managed_by") == "stigix-orchestrator"),
                    scm=scm_by_imsi.get(imsi), scm_ok=scm_ok,
                    starting_since=self._starting.get(imsi), now=now,
                )
                if d["status"] in ("active", "failed"):
                    self._starting.pop(imsi, None)
                # Debounce: an 'inconsistent' verdict must hold for N cycles before it is shown.
                if d["candidate_inconsistent"]:
                    n = self._incons_count.get(imsi, 0) + 1
                    self._incons_count[imsi] = n
                    if n < INCONSISTENT_CONFIRM_CYCLES:
                        before = prev.get(imsi)
                        d["status"] = before["status"] if before and before["status"] != "active" else "unknown"
                        d["reason"] = f"checking: {d['reason']}"
                else:
                    self._incons_count.pop(imsi, None)

                scm_rec = scm_by_imsi.get(imsi)
                sim = {
                    "imsi": imsi,
                    "status": d["status"],
                    "live_ip": d["live_ip"],
                    "interface": d["interface"],
                    "reason": d["reason"],
                    "radio": {
                        "state": (radio or {}).get("radio_state", "stopped") if agent_ok else "unknown",
                        "pid": (radio or {}).get("pid"),
                        "interface": (radio or {}).get("interface"),
                        "ip": (radio or {}).get("ip"),
                        "reason": (radio or {}).get("reason"),
                        "last_error": (radio or {}).get("last_error"),
                    },
                    "core": {
                        "state": "unknown" if mongo is None else ("provisioned" if mdoc else "absent"),
                        "managed": bool(mdoc and mdoc.get("managed_by") == "stigix-orchestrator"),
                        "amf": (a or {}).get("mm_state") or ("absent" if amf is not None else "unknown"),
                        "cm_state": (a or {}).get("cm_state"),
                        "smf_ip": (s or {}).get("ipv4"),
                        "smf_pdu_state": (s or {}).get("pdu_state"),
                    },
                    "scm": {
                        "state": ("registered" if scm_rec else "absent") if scm_ok else "unknown",
                        "tenant_name": (scm_rec or {}).get("tenant_name"),
                        "tsg_id": (scm_rec or {}).get("tsg_id"),
                        "groups": (scm_rec or {}).get("groups") or [],
                        "apn": (scm_rec or {}).get("apn"),
                        "identity_id": (scm_rec or {}).get("identity_id"),
                    },
                    "since": (prev.get(imsi) or {}).get("since") or _now_iso(),
                }
                before = prev.get(imsi)
                if before is None or before["status"] != sim["status"] or before["live_ip"] != sim["live_ip"]:
                    sim["since"] = _now_iso()
                    if before is not None or sim["status"] not in ("offline", "core_only", "scm_only"):
                        self._event(logging.INFO, "state.transition", imsi,
                                    frm=before["status"] if before else "unseen", to=sim["status"],
                                    live_ip=sim["live_ip"], interface=sim["interface"], reason=sim["reason"])
                    for fn in self._listeners:
                        try:
                            fn(sim, before, {"agent_ok": agent_ok, "core_ok": core_ok})
                        except Exception as e:
                            logger.exception("event=reconciler.listener_error imsi=%s error=%r", imsi, str(e))
                elif DEBUG:
                    self._event(logging.DEBUG, "state.ue", imsi, status=sim["status"], reason=sim["reason"])
                sims[imsi] = sim

            stale_core = [
                {"imsi": i, "ip": p.get("ipv4"), "pdu_state": p.get("pdu_state"),
                 "amf": ((amf or {}).get(i) or {}).get("mm_state")}
                for i, p in (smf or {}).items() if sims.get(i, {}).get("status") != "active"
            ]
            summary: Dict[str, int] = {}
            for s in sims.values():
                summary[s["status"]] = summary.get(s["status"], 0) + 1

            snap = {
                "ts": _now_iso(),
                "_epoch": now,
                "cycle_ms": round((time.monotonic() - t0) * 1000, 1),
                "sources": {
                    "agent": {"ok": agent_ok, "error": tele.get("error"), "scan_ms": tele.get("scan_ms"),
                              "gnb": tele.get("gnb"), "url": getattr(self.ran, "agent_url", None)},
                    "amf": {"ok": amf is not None},
                    "smf": {"ok": smf is not None},
                    "mongodb": {"ok": mongo is not None},
                    "scm": {"ok": scm_ok and self._scm_error is None, "has_data": scm_ok,
                            "age_s": round(now - self._scm_at, 1) if self._scm_at else None,
                            "error": self._scm_error},
                },
                "summary": summary,
                "sims": sims,
                "stale_core_sessions": stale_core,
                "unattributed_tuns": tele.get("unattributed_tuns", []) if agent_ok else [],
                "unidentified_processes": tele.get("unidentified_processes", []) if agent_ok else [],
            }
            self._snapshot = snap
            if DEBUG:
                self._event(logging.DEBUG, "reconciler.cycle", ms=snap["cycle_ms"], agent_ok=agent_ok,
                            core_ok=core_ok, scm_ok=scm_ok, summary=str(summary))
            return snap
