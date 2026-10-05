"""Session sync (plan phase 3) — single owner of SCM session register/deregister + active_sessions.json.

`active_sessions.json` is a DERIVED record: "this IMSI is registered in SCM with this IP".
It is never a source of truth for the UI (the reconciler snapshot is).

Rules, evaluated on every reconciler cycle (`on_cycle`):
  * SIM `active` with live_ip X, cache has no entry or a different IP
        -> (deregister old IP) + register X in SCM + write cache            [event session.register]
  * SIM confirmed NOT active (offline / inconsistent / failed / ...) for >= 2 cycles and >= CONFIRM_S,
    while the cache still has an entry
        -> deregister that IP in SCM + delete cache entry + metadata Inactive  [event session.deregister]
  * SIM `unknown` / `starting`, or RAN agent unreachable
        -> NOTHING is touched (never prune on a blip)

Safety:
  * SCM deregister is skipped if the IP is currently live on ANOTHER active SIM (IP reuse), or if the
    cache key is not a SIM known to SCM/MongoDB (e.g. legacy IMEI-keyed entries) — cache entry is still pruned.
  * SCM failures are retried with a backoff (no API spam); the cache only records a successful registration.
  * Explicit Power On / Power Off call `register()` / `deregister()` directly (no 2-cycle wait).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("SessionSync")
DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes", "on")

CONFIRM_CYCLES = 2
CONFIRM_S = float(os.environ.get("SESSION_DOWN_CONFIRM_S", "2.5"))
RETRY_BACKOFF_S = float(os.environ.get("SCM_RETRY_BACKOFF_S", "30"))
HOLD_STATUSES = ("unknown", "starting")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SessionSync:
    def __init__(
        self,
        get_client: Callable[[], Any],
        load_sessions: Callable[[], Dict[str, Dict[str, Any]]],
        save_sessions: Callable[[Dict[str, Dict[str, Any]]], None],
        update_meta: Callable[[str, Dict[str, Any]], None],
        load_meta: Callable[[], Dict[str, Dict[str, Any]]],
        session_cls: Any,
        enabled: Optional[bool] = None,
    ):
        self.get_client = get_client
        self.load_sessions = load_sessions
        self.save_sessions = save_sessions
        self.update_meta = update_meta
        self.load_meta = load_meta
        self.session_cls = session_cls
        self.enabled = enabled if enabled is not None else (
            os.environ.get("SESSION_SYNC_ENABLED", "true").lower() not in ("0", "false", "no", "off"))
        self._lock = threading.RLock()
        self._pending_down: Dict[str, Dict[str, Any]] = {}
        self._retry_at: Dict[str, float] = {}
        self._events: deque = deque(maxlen=300)

    # ------------------------------------------------------------------ events
    def _event(self, level: int, name: str, imsi: Optional[str] = None, **detail: Any) -> None:
        rec = {"ts": _now_iso(), "level": logging.getLevelName(level), "event": name, "imsi": imsi, **detail}
        kv = " ".join(f'{k}="{v}"' if isinstance(v, str) and " " in v else f"{k}={v}" for k, v in detail.items())
        logger.log(level, "event=%s%s %s", name, f" imsi={imsi}" if imsi else "", kv)
        if level >= logging.INFO or DEBUG:
            self._events.appendleft(rec)

    def events(self, limit: int = 100, imsi: Optional[str] = None):
        items = list(self._events)
        if imsi:
            items = [e for e in items if e.get("imsi") == imsi]
        return items[:max(1, min(limit, 300))]

    # ------------------------------------------------------------------ helpers
    def _identity(self, imsi: str, entry: Dict[str, Any], sim: Optional[Dict[str, Any]]) -> Dict[str, str]:
        scm = (sim or {}).get("scm") or {}
        meta = self.load_meta().get(imsi, {})
        return {
            "imei": entry.get("imei") or scm.get("imei") or meta.get("imei") or f"35412809{imsi[-7:]}",
            "apn": entry.get("apn") or scm.get("apn") or meta.get("apn") or "internet",
        }

    def _scm_call(self, action: str, imsi: str, ip: str, ident: Dict[str, str]) -> Dict[str, Any]:
        sess = self.session_cls(imsi=imsi, imei=ident["imei"], apn=ident["apn"], ip_type="IPv4", ipv4_addr=ip)
        t0 = time.monotonic()
        try:
            client = self.get_client()
            res = client.register_ue_session(sess) if action == "register" else client.deregister_ue_session(sess)
            ms = round((time.monotonic() - t0) * 1000)
            return {"ok": True, "ms": ms, "response": res}
        except Exception as e:
            ms = round((time.monotonic() - t0) * 1000)
            return {"ok": False, "ms": ms, "error": str(e)[:300]}

    # ------------------------------------------------------------------ explicit actions
    def register(self, imsi: str, ip: str, interface: Optional[str] = None, sim: Optional[Dict[str, Any]] = None,
                 imei: Optional[str] = None, apn: Optional[str] = None, reason: str = "power_on") -> Dict[str, Any]:
        """Register IMSI<->IP in SCM (idempotent) and record it in active_sessions.json."""
        with self._lock:
            sessions = self.load_sessions()
            entry = sessions.get(imsi, {})
            if entry.get("ipv4_addr") == ip and entry.get("scm_registered"):
                if interface and entry.get("interface") != interface:
                    entry["interface"] = interface
                    sessions[imsi] = entry
                    self.save_sessions(sessions)
                return {"ok": True, "skipped": "already registered with this IP"}
            ident = self._identity(imsi, {**entry, **({"imei": imei} if imei else {}), **({"apn": apn} if apn else {})}, sim)
            old_ip = entry.get("ipv4_addr")
            if old_ip and old_ip != ip and entry.get("scm_registered"):
                r_old = self._scm_call("deregister", imsi, old_ip, ident)
                self._event(logging.INFO if r_old["ok"] else logging.WARNING, "session.deregister", imsi,
                            ip=old_ip, reason="ip_changed", scm_ok=r_old["ok"], ms=r_old["ms"],
                            error=r_old.get("error"))
            r = self._scm_call("register", imsi, ip, ident)
            sessions = self.load_sessions()
            sessions[imsi] = {
                "ipv4_addr": ip,
                "interface": interface,
                "imei": ident["imei"],
                "apn": ident["apn"],
                "status": "Active",
                "region": "europe-west9",
                "tenant_status": "Yes",
                "scm_registered": bool(r["ok"]),
                "scm_error": r.get("error"),
                "since": entry.get("since") if entry.get("ipv4_addr") == ip else _now_iso(),
                "updated": _now_iso(),
            }
            self.save_sessions(sessions)
            self.update_meta(imsi, {"last_ip": ip, "status": "Active"})
            if r["ok"]:
                self._retry_at.pop(imsi, None)
            else:
                self._retry_at[imsi] = time.time() + RETRY_BACKOFF_S
            self._event(logging.INFO if r["ok"] else logging.WARNING, "session.register", imsi, ip=ip,
                        interface=interface, reason=reason, scm_ok=r["ok"], ms=r["ms"], error=r.get("error"))
            return r

    def deregister(self, imsi: str, ip_hint: Optional[str] = None, sim: Optional[Dict[str, Any]] = None,
                   reason: str = "power_off", live_ips_elsewhere: Optional[Dict[str, str]] = None,
                   known_sim: bool = True) -> Dict[str, Any]:
        """Deregister the IMSI's SCM session (IP from cache, else ip_hint) and drop the cache entry."""
        with self._lock:
            sessions = self.load_sessions()
            entry = sessions.get(imsi, {})
            ip = entry.get("ipv4_addr") or ip_hint
            result: Dict[str, Any] = {"ok": True, "ip": ip}
            owner = (live_ips_elsewhere or {}).get(ip) if ip else None
            if not ip:
                result["skipped"] = "no known IP for this IMSI"
            elif owner and owner != imsi:
                result["skipped"] = f"IP {ip} is now live on {owner} — SCM mapping left to that SIM"
            elif not known_sim:
                result["skipped"] = "cache key is not a known SIM (legacy entry) — cache pruned only"
            else:
                r = self._scm_call("deregister", imsi, ip, self._identity(imsi, entry, sim))
                result.update(r)
            self.update_meta(imsi, {"status": "Inactive", "last_ip": None})
            self._pending_down.pop(imsi, None)
            ok = result.get("ok", True)
            if ok:
                if imsi in sessions:
                    del sessions[imsi]
                    self.save_sessions(sessions)
                self._retry_at.pop(imsi, None)
            else:
                # Keep the entry (marked) so the SCM deregistration is retried later — never forget a mapping.
                if imsi in sessions:
                    sessions[imsi].update({"status": "Inactive", "scm_deregister_pending": True,
                                           "scm_error": result.get("error"), "updated": _now_iso()})
                    self.save_sessions(sessions)
                self._retry_at[imsi] = time.time() + RETRY_BACKOFF_S
            self._event(logging.INFO if ok else logging.WARNING, "session.deregister", imsi, ip=ip, reason=reason,
                        scm_ok=ok if "skipped" not in result else None, skipped=result.get("skipped"),
                        ms=result.get("ms"), error=result.get("error"))
            return result

    # ------------------------------------------------------------------ reconciler hook
    def on_cycle(self, snap: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        if not self._lock.acquire(blocking=False):
            return  # an explicit action / previous cycle is running; next cycle will catch up
        try:
            self._on_cycle(snap)
        except Exception as e:
            logger.exception("event=session.sync_error error=%r", str(e))
        finally:
            self._lock.release()

    def _on_cycle(self, snap: Dict[str, Any]) -> None:
        agent_ok = bool(((snap.get("sources") or {}).get("agent") or {}).get("ok"))
        if not agent_ok:
            if self._pending_down:
                self._event(logging.INFO, "session.hold", reason="RAN agent unreachable — nothing pruned",
                            pending=len(self._pending_down))
            self._pending_down.clear()
            return
        now = time.time()
        sims: Dict[str, Dict[str, Any]] = snap.get("sims") or {}
        sessions = self.load_sessions()
        live_ips = {s["live_ip"]: i for i, s in sims.items() if s.get("status") == "active" and s.get("live_ip")}

        # 1. Up: every active SIM must be registered with its live IP
        for imsi, sim in sims.items():
            if sim.get("status") != "active" or not sim.get("live_ip"):
                continue
            self._pending_down.pop(imsi, None)
            entry = sessions.get(imsi, {})
            if entry.get("ipv4_addr") == sim["live_ip"] and entry.get("scm_registered"):
                continue
            if self._retry_at.get(imsi, 0) > now:
                continue
            if (sim.get("scm") or {}).get("state") == "absent":
                # Not in SCM inventory: record the session locally, nothing to register in SCM.
                if entry.get("ipv4_addr") != sim["live_ip"]:
                    sessions[imsi] = {"ipv4_addr": sim["live_ip"], "interface": sim.get("interface"),
                                      "status": "Active", "scm_registered": False,
                                      "scm_error": "SIM not in SCM inventory", "since": _now_iso()}
                    self.save_sessions(sessions)
                    self._event(logging.INFO, "session.local_only", imsi, ip=sim["live_ip"],
                                reason="SIM not in SCM inventory")
                continue
            self.register(imsi, sim["live_ip"], interface=sim.get("interface"), sim=sim, reason="reconcile_up")
            sessions = self.load_sessions()

        # 2. Down: cache entries whose SIM is confirmed not active
        for imsi in list(sessions.keys()):
            sim = sims.get(imsi)
            status = (sim or {}).get("status", "absent")
            if status == "active":
                continue
            reason = (sim or {}).get("reason") or ""
            # Real holds: power-on in progress, or a source unreachable. The reconciler's own
            # debounce verdict ("checking: ...", agent reachable) counts as a down candidate.
            if status == "starting" or (status == "unknown" and not reason.startswith("checking")):
                self._pending_down.pop(imsi, None)
                continue
            p = self._pending_down.get(imsi)
            if p is None:
                self._pending_down[imsi] = {"first": now, "count": 1, "status": status}
                self._event(logging.DEBUG, "session.down_pending", imsi, status=status,
                            ip=sessions[imsi].get("ipv4_addr"))
                continue
            p["status"] = status
            p["count"] += 1
            if p["count"] < CONFIRM_CYCLES or (now - p["first"]) < CONFIRM_S:
                continue
            if self._retry_at.get(imsi, 0) > now:
                continue
            known = sim is not None and (
                (sim.get("scm") or {}).get("state") == "registered" or (sim.get("core") or {}).get("state") == "provisioned")
            self.deregister(imsi, sim=sim, reason=f"reconcile_down:{status}", live_ips_elsewhere=live_ips,
                            known_sim=known)
