"""RAN Agent core — single owner of UERANSIM nr-ue processes and uesimtun interfaces.

Runs inside the `prisma-5g-agent` container on the UERANSIM host with:
  - pid: host          → sees every nr-ue / nr-gnb process on the host via /proc
  - network_mode: host → sees host kernel interfaces (uesimtunX)
  - NET_ADMIN + /dev/net/tun

Ground truth comes only from the kernel:
  - processes : /proc/<pid>/cmdline + /proc/<pid>/stat (zombies excluded)
  - interfaces: `ip -j addr show`
  - attribution TUN ↔ IMSI: the IMSI's own nr-ue log, confirmed by the kernel

Parsing functions are pure (take raw inputs) so they can be unit-tested
without a UERANSIM host.
"""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("RanAgent")

DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes", "on")

# Recent agent events (start/stop steps, state transitions, errors) for /api/agent/events
_EVENTS: deque = deque(maxlen=int(os.environ.get("AGENT_EVENT_BUFFER", "500")))
_EVENTS_LOCK = threading.Lock()


def event(level: int, name: str, imsi: Optional[str] = None, **detail: Any) -> Dict[str, Any]:
    """Log one structured event line (`event=<name> imsi=<imsi> k=v ...`) and keep it in the ring.

    Grep examples:  docker logs prisma-5g-agent | grep 'imsi=999703875813789'
                    docker logs prisma-5g-agent | grep 'event=ue.transition'
    """
    rec = {"ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
           "level": logging.getLevelName(level), "event": name, "imsi": imsi, **detail}
    def fmt(v: Any) -> str:
        if isinstance(v, (list, dict)) or (isinstance(v, str) and (" " in v or not v)):
            return json.dumps(v)
        return str(v)

    kv = " ".join(f"{k}={fmt(v)}" for k, v in detail.items())
    logger.log(level, "event=%s%s %s", name, f" imsi={imsi}" if imsi else "", kv)
    if level >= logging.INFO or DEBUG:
        with _EVENTS_LOCK:
            _EVENTS.appendleft(rec)
    return rec


def recent_events(limit: int = 100, imsi: Optional[str] = None) -> List[Dict[str, Any]]:
    with _EVENTS_LOCK:
        items = list(_EVENTS)
    if imsi:
        items = [e for e in items if e.get("imsi") == imsi]
    return items[:max(1, min(limit, 500))]

LOG_DIR = "/tmp"
TUN_PREFIX = "uesimtun"
_UE_YAML_RE = re.compile(r"ue-(\d{6,15})\.yaml")
_SUPI_RE = re.compile(r"supi:\s*['\"]?imsi-(\d{6,15})")
_TUN_LOG_RE = re.compile(r"TUN interface\[(" + TUN_PREFIX + r"\d+),\s*([0-9.]+)\]")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def clean_imsi(imsi: str) -> str:
    return re.sub(r"\D", "", str(imsi))


# -----------------------------------------------------------------------------
# Pure parsers
# -----------------------------------------------------------------------------

def parse_ip_json(raw: str) -> List[Dict[str, Any]]:
    """Parse `ip -j addr show` output into uesimtun interface records."""
    try:
        data = json.loads(raw or "[]")
    except Exception:
        return []
    tuns = []
    for link in data:
        name = link.get("ifname", "")
        if not name.startswith(TUN_PREFIX):
            continue
        ipv4 = next(
            (a.get("local") for a in link.get("addr_info", []) if a.get("family") == "inet"),
            None,
        )
        flags = link.get("flags", [])
        tuns.append({
            "interface": name,
            "ip": ipv4,
            "up": "UP" in flags,
            "operstate": link.get("operstate"),
        })
    return tuns


def parse_ue_log(text: str) -> Dict[str, Any]:
    """Extract the latest radio/NAS state from an nr-ue log."""
    result: Dict[str, Any] = {"interface": None, "ip": None, "phase": "unknown", "last_error": None}
    if not text:
        result["phase"] = "no_log"
        return result

    # The LAST TUN line wins (a UE may re-establish its session).
    tun_matches = _TUN_LOG_RE.findall(text)
    if tun_matches:
        result["interface"], result["ip"] = tun_matches[-1]

    if "FIVEG_SERVICES_NOT_ALLOWED" in text or "Registration reject" in text or "registration failed" in text.lower():
        result["phase"] = "rejected"
        m = re.findall(r"\[error\]\s*(.+)", text)
        result["last_error"] = m[-1].strip() if m else "Registration rejected by core"
    tun_fail = re.findall(r"TUN configuration failure \[([^\]]*)\]", text)
    last_tun_ok = text.rfind("TUN interface[")
    last_tun_fail = text.rfind("TUN configuration failure")
    if tun_fail and last_tun_fail > last_tun_ok:
        result["phase"] = "tun_failed"
        result["last_error"] = f"TUN configuration failure: {tun_fail[-1]}"
        result["interface"], result["ip"] = None, None
        return result
    if tun_matches:
        result["phase"] = "pdu_active"
    elif "Initial Registration is successful" in text:
        result["phase"] = "registered"
    elif result["phase"] != "rejected":
        result["phase"] = "connecting"

    if "De-registration" in text or "Switch-off" in text or "switch-off" in text:
        # Explicit deregistration after the last TUN line → no longer active
        last_tun = text.rfind("TUN interface[")
        last_dereg = max(text.rfind("De-registration"), text.rfind("witch-off"))
        if last_dereg > last_tun:
            result["phase"] = "deregistered"
    return result


def imsi_from_cmdline(cmdline: str, read_file=None) -> Optional[str]:
    """Return the IMSI an nr-ue process serves, from its cmdline (and config if needed)."""
    m = _UE_YAML_RE.search(cmdline)
    if m:
        return m.group(1)
    # Baseline/manual UEs (e.g. config/open5gs-ue.yaml): read supi from the config file
    if read_file is not None:
        parts = cmdline.split()
        for i, tok in enumerate(parts):
            if tok in ("-c", "--config") and i + 1 < len(parts):
                content = read_file(parts[i + 1])
                if content:
                    sm = _SUPI_RE.search(content)
                    if sm:
                        return sm.group(1)
    return None


def correlate(
    processes: List[Dict[str, Any]],
    tuns: List[Dict[str, Any]],
    logs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the per-IMSI view from processes, kernel TUNs and per-IMSI logs.

    A TUN is attributed to an IMSI only if the IMSI's log names that interface
    AND the kernel interface carries the same IP. Anything else is reported as
    unattributed — never guessed.
    """
    tun_by_name = {t["interface"]: t for t in tuns}
    imsis = {p["imsi"] for p in processes if p.get("imsi")} | set(logs.keys())
    attributed = set()
    ues = []
    for imsi in sorted(imsis):
        procs = [p for p in processes if p.get("imsi") == imsi]
        log = logs.get(imsi, {"phase": "no_log", "interface": None, "ip": None, "last_error": None})
        pid = procs[0]["pid"] if procs else None
        tun = None
        if procs and log.get("interface"):
            k = tun_by_name.get(log["interface"])
            if k and k.get("ip") and k["ip"] == log.get("ip") and log.get("phase") == "pdu_active":
                tun = k
                attributed.add(k["interface"])

        if procs and tun:
            radio = "active"
            reason = f"nr-ue PID {pid} alive; log and kernel agree: {tun['interface']} = {tun['ip']}"
        elif procs and log.get("phase") in ("rejected", "tun_failed"):
            radio = "failed"
            reason = f"nr-ue PID {pid} alive but failed: {log.get('last_error')}"
        elif procs:
            radio = "connecting"
            if not log.get("interface"):
                reason = f"nr-ue PID {pid} alive; no TUN in log yet (log phase: {log.get('phase')})"
            else:
                k = tun_by_name.get(log["interface"])
                if not k:
                    reason = f"log says {log['interface']}={log.get('ip')} but kernel has no {log['interface']}"
                elif k.get("ip") != log.get("ip"):
                    reason = f"log says {log['interface']}={log.get('ip')} but kernel {log['interface']} has {k.get('ip')}"
                else:
                    reason = f"log phase is {log.get('phase')} (not pdu_active)"
        else:
            radio = "stopped"
            reason = "no nr-ue process for this IMSI" + (
                f" (stale log still mentions {log['interface']}; ignored)" if log.get("interface") else "")

        ues.append({
            "imsi": imsi,
            "pid": pid,
            "process_alive": bool(procs),
            "duplicate_processes": len(procs) > 1,
            "radio_state": radio,
            "reason": reason,
            "log_phase": log.get("phase"),
            "last_error": log.get("last_error"),
            "interface": tun["interface"] if tun else None,
            "ip": tun["ip"] if tun else None,
        })

    unattributed = [t for t in tuns if t["interface"] not in attributed]
    return {"ues": ues, "unattributed_tuns": unattributed}


# -----------------------------------------------------------------------------
# Host probes
# -----------------------------------------------------------------------------

class RanAgent:
    def __init__(self, ueransim_dir: Optional[str] = None, proc_root: str = "/proc"):
        self.ueransim_dir = ueransim_dir or os.environ.get("UERANSIM_DIR", "/opt/UERANSIM")
        self.proc_root = proc_root
        self.managed_dir = os.path.join(self.ueransim_dir, "config", "managed")
        self._children: Dict[str, subprocess.Popen] = {}
        self._last_states: Dict[str, Dict[str, Any]] = {}
        self._state_lock = threading.Lock()
        self._warned_pids: set = set()

    # ---- paths -----------------------------------------------------------
    def config_path(self, imsi: str) -> str:
        return os.path.join(self.managed_dir, f"ue-{imsi}.yaml")

    @staticmethod
    def log_path(imsi: str) -> str:
        return os.path.join(LOG_DIR, f"nr-ue-{imsi}.log")

    def _read_config(self, path: str) -> Optional[str]:
        """Read a UE config referenced by a host process (host paths map to /opt/UERANSIM)."""
        candidates = [path]
        if not os.path.isabs(path):
            candidates.append(os.path.join(self.ueransim_dir, path))
        else:
            # host path /home/ubuntu/UERANSIM/... → container /opt/UERANSIM/...
            m = re.search(r"/UERANSIM/(.+)$", path)
            if m:
                candidates.append(os.path.join(self.ueransim_dir, m.group(1)))
        for c in candidates:
            try:
                with open(c) as f:
                    return f.read()
            except Exception:
                continue
        return None

    # ---- probes ----------------------------------------------------------
    def _reap_children(self) -> None:
        for imsi, p in list(self._children.items()):
            if p.poll() is not None:
                self._children.pop(imsi, None)

    def scan_processes(self) -> Dict[str, Any]:
        """Scan /proc for live (non-zombie) nr-ue and nr-gnb processes."""
        self._reap_children()
        ues, gnbs = [], []
        try:
            entries = os.listdir(self.proc_root)
        except Exception:
            entries = []
        for pid_s in entries:
            if not pid_s.isdigit():
                continue
            base = os.path.join(self.proc_root, pid_s)
            try:
                with open(os.path.join(base, "cmdline"), "rb") as f:
                    cmd = f.read().replace(b"\x00", b" ").decode("utf-8", "replace").strip()
                if "nr-ue" not in cmd and "nr-gnb" not in cmd:
                    continue
                with open(os.path.join(base, "stat")) as f:
                    stat = f.read()
                state = stat[stat.rfind(")") + 2:].split()[0]
            except Exception:
                continue
            if state in ("Z", "X"):
                continue
            argv0 = cmd.split()[0] if cmd else ""
            if argv0 in ("sudo", "sh", "bash") or argv0.endswith("/sudo"):
                continue  # wrapper, not the radio process itself
            if argv0.endswith("nr-ue"):
                ues.append({"pid": int(pid_s), "imsi": imsi_from_cmdline(cmd, self._read_config), "cmdline": cmd})
            elif argv0.endswith("nr-gnb"):
                gnbs.append({"pid": int(pid_s), "cmdline": cmd})
        return {"ues": ues, "gnbs": gnbs}

    @staticmethod
    def scan_tuns() -> List[Dict[str, Any]]:
        try:
            r = subprocess.run(["ip", "-j", "addr", "show"], capture_output=True, text=True, timeout=3)
            return parse_ip_json(r.stdout)
        except Exception as e:
            logger.warning("ip -j addr failed: %s", e)
            return []

    def read_log(self, imsi: str, max_bytes: int = 64_000) -> str:
        try:
            with open(self.log_path(imsi), "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - max_bytes))
                return f.read().decode("utf-8", "replace")
        except Exception:
            return ""

    def _known_log_imsis(self) -> List[str]:
        out = []
        try:
            for name in os.listdir(LOG_DIR):
                m = re.fullmatch(r"nr-ue-(\d{6,15})\.log", name)
                if m:
                    out.append(m.group(1))
        except Exception:
            pass
        return out

    def telemetry(self) -> Dict[str, Any]:
        t0 = time.monotonic()
        procs = self.scan_processes()
        tuns = self.scan_tuns()
        imsis = {p["imsi"] for p in procs["ues"] if p["imsi"]} | set(self._known_log_imsis())
        logs = {i: parse_ue_log(self.read_log(i)) for i in imsis}
        corr = correlate(procs["ues"], tuns, logs)
        scan_ms = round((time.monotonic() - t0) * 1000, 1)
        self._track_transitions(corr["ues"])
        if DEBUG:
            event(logging.DEBUG, "telemetry.scan", scan_ms=scan_ms, gnb_pids=[g["pid"] for g in procs["gnbs"]],
                  ue_pids=[p["pid"] for p in procs["ues"]], tuns=[f"{t['interface']}={t['ip']}" for t in tuns],
                  unattributed=[t["interface"] for t in corr["unattributed_tuns"]])
            for u in corr["ues"]:
                event(logging.DEBUG, "telemetry.ue", u["imsi"], radio_state=u["radio_state"], reason=u["reason"])
        for p in procs["ues"]:
            if not p["imsi"] and p["pid"] not in self._warned_pids:
                self._warned_pids.add(p["pid"])
                event(logging.WARNING, "telemetry.unidentified_process", pid=p["pid"], cmdline=p["cmdline"])
        return {
            "ok": True,
            "ts": _now(),
            "gnb": {"running": bool(procs["gnbs"]), "pids": [g["pid"] for g in procs["gnbs"]]},
            "processes": [{k: p[k] for k in ("pid", "imsi")} for p in procs["ues"]],
            "unidentified_processes": [p for p in procs["ues"] if not p["imsi"]],
            "tuns": tuns,
            "ues": corr["ues"],
            "unattributed_tuns": corr["unattributed_tuns"],
            "scan_ms": scan_ms,
        }

    def _track_transitions(self, ues: List[Dict[str, Any]]) -> None:
        """Log every radio_state / IP change once, at INFO, with the reason."""
        seen = set()
        with self._state_lock:
            for u in ues:
                seen.add(u["imsi"])
                prev = self._last_states.get(u["imsi"])
                key = (u["radio_state"], u["interface"], u["ip"])
                if prev is None or prev["key"] != key:
                    event(logging.INFO, "ue.transition", u["imsi"],
                          frm=prev["key"][0] if prev else "unseen", to=u["radio_state"],
                          interface=u["interface"], ip=u["ip"], pid=u["pid"], reason=u["reason"])
                    self._last_states[u["imsi"]] = {"key": key}
            for imsi in [i for i in self._last_states if i not in seen]:
                if self._last_states[imsi]["key"][0] != "stopped":
                    event(logging.INFO, "ue.transition", imsi, frm=self._last_states[imsi]["key"][0],
                          to="stopped", reason="no process and no log anymore")
                self._last_states.pop(imsi, None)

    def ue_state(self, imsi: str) -> Dict[str, Any]:
        imsi = clean_imsi(imsi)
        t = self.telemetry()
        ue = next((u for u in t["ues"] if u["imsi"] == imsi), None)
        return ue or {
            "imsi": imsi, "pid": None, "process_alive": False, "duplicate_processes": False,
            "radio_state": "stopped", "reason": "no nr-ue process and no log for this IMSI",
            "log_phase": "no_log", "last_error": None,
            "interface": None, "ip": None,
        }

    def _pids_for(self, imsi: str) -> List[int]:
        return [p["pid"] for p in self.scan_processes()["ues"] if p["imsi"] == imsi]

    # ---- control ---------------------------------------------------------
    def start_ue(self, imsi: str, yaml_content: str, timeout_s: float = 15.0) -> Dict[str, Any]:
        """Write config, spawn nr-ue, and wait until the kernel TUN is up (or failure)."""
        imsi = clean_imsi(imsi)
        t0 = time.monotonic()
        event(logging.INFO, "ue.start.request", imsi, timeout_s=timeout_s)
        if not yaml_content or f"imsi-{imsi}" not in yaml_content:
            event(logging.ERROR, "ue.start.rejected", imsi, error="YAML missing or SUPI does not match IMSI")
            return {"success": False, "imsi": imsi, "error": "YAML missing or SUPI does not match IMSI"}

        existing = self._pids_for(imsi)
        if existing:
            event(logging.WARNING, "ue.start.already_running", imsi, pids=existing, action="stopping first")
            self.stop_ue(imsi)

        os.makedirs(self.managed_dir, exist_ok=True)
        with open(self.config_path(imsi), "w") as f:
            f.write(yaml_content)
        event(logging.DEBUG, "ue.start.config_written", imsi, path=self.config_path(imsi), bytes=len(yaml_content))

        log_fp = open(self.log_path(imsi), "w")
        proc = subprocess.Popen(
            ["./build/nr-ue", "-c", self.config_path(imsi)],
            cwd=self.ueransim_dir, stdout=log_fp, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True, close_fds=True,
        )
        log_fp.close()
        self._children[imsi] = proc
        event(logging.INFO, "ue.start.spawned", imsi, pid=proc.pid, log=self.log_path(imsi))

        deadline = time.monotonic() + timeout_s
        state = self.ue_state(imsi)
        last_phase = None
        while time.monotonic() < deadline:
            state = self.ue_state(imsi)
            if state["log_phase"] != last_phase:
                event(logging.DEBUG, "ue.start.progress", imsi, log_phase=state["log_phase"],
                      elapsed_ms=round((time.monotonic() - t0) * 1000))
                last_phase = state["log_phase"]
            if state["radio_state"] in ("active", "failed") or not state["process_alive"]:
                break
            time.sleep(0.5)

        ok = state["radio_state"] == "active"
        error = None if ok else (state.get("last_error") or f"UE not active after {timeout_s:.0f}s (radio_state={state['radio_state']})")
        event(logging.INFO if ok else logging.ERROR, "ue.start.result", imsi, success=ok,
              radio_state=state["radio_state"], interface=state["interface"], ip=state["ip"],
              elapsed_ms=round((time.monotonic() - t0) * 1000), reason=state.get("reason"), error=error)
        return {
            "success": ok,
            "imsi": imsi,
            "state": state,
            "error": error,
            "elapsed_ms": round((time.monotonic() - t0) * 1000),
            "logs": self.read_log(imsi)[-4000:],
        }

    def _nr_cli(self, imsi: str, command: str, timeout: float = 4.0) -> str:
        try:
            r = subprocess.run(
                [os.path.join(self.ueransim_dir, "build", "nr-cli"), f"imsi-{imsi}", "-e", command],
                capture_output=True, text=True, timeout=timeout,
            )
            return (r.stdout + r.stderr).strip()
        except Exception as e:
            return f"nr-cli error: {e}"

    def stop_ue(self, imsi: str, graceful_timeout_s: float = 3.0) -> Dict[str, Any]:
        """Gracefully deregister, then terminate, then clean only this IMSI's TUN."""
        imsi = clean_imsi(imsi)
        t0 = time.monotonic()
        before = self.ue_state(imsi)
        steps: List[str] = []

        def step(msg: str, level: int = logging.INFO) -> None:
            steps.append(msg)
            event(level, "ue.stop.step", imsi, step=msg, elapsed_ms=round((time.monotonic() - t0) * 1000))

        event(logging.INFO, "ue.stop.request", imsi, radio_state=before["radio_state"],
              pid=before["pid"], interface=before["interface"], ip=before["ip"])
        pids = self._pids_for(imsi)

        if pids:
            out = self._nr_cli(imsi, "deregister switch-off")
            step(f"nr-cli deregister switch-off: {out[:160] or 'ok'}")
            end = time.monotonic() + graceful_timeout_s
            while time.monotonic() < end and self._pids_for(imsi):
                time.sleep(0.25)
            if not self._pids_for(imsi):
                step("process exited after graceful deregistration")

            for sig, label, wait in ((signal.SIGTERM, "SIGTERM", 2.0), (signal.SIGKILL, "SIGKILL", 1.0)):
                remaining = self._pids_for(imsi)
                if not remaining:
                    break
                for pid in remaining:
                    try:
                        os.kill(pid, sig)
                    except ProcessLookupError:
                        pass
                    except PermissionError as e:
                        step(f"{label} {pid} denied: {e}", logging.ERROR)
                step(f"{label} → {remaining} (graceful exit did not happen)", logging.WARNING)
                end = time.monotonic() + wait
                while time.monotonic() < end and self._pids_for(imsi):
                    time.sleep(0.2)
        else:
            step("no nr-ue process for this IMSI")

        self._reap_children()

        # Remove only THIS IMSI's TUN if the kernel still has it and no live process owns it.
        iface = before.get("interface") or parse_ue_log(self.read_log(imsi)).get("interface")
        if iface and not self._pids_for(imsi):
            if any(t["interface"] == iface for t in self.scan_tuns()):
                owners = [u for u in self.telemetry()["ues"] if u["interface"] == iface and u["imsi"] != imsi]
                if not owners:
                    subprocess.run(["ip", "link", "delete", iface], capture_output=True)
                    step(f"deleted leftover {iface}", logging.WARNING)
                else:
                    step(f"{iface} now owned by {owners[0]['imsi']}; not deleted", logging.WARNING)

        try:
            os.remove(self.config_path(imsi))
        except FileNotFoundError:
            pass
        try:
            os.replace(self.log_path(imsi), self.log_path(imsi) + ".prev")
        except FileNotFoundError:
            pass

        after = self.ue_state(imsi)
        tun_gone = not iface or not any(t["interface"] == iface for t in self.scan_tuns())
        ok = not after["process_alive"] and tun_gone
        event(logging.INFO if ok else logging.ERROR, "ue.stop.result", imsi, success=ok,
              process_alive=after["process_alive"], tun_gone=tun_gone,
              elapsed_ms=round((time.monotonic() - t0) * 1000))
        return {"success": ok, "imsi": imsi, "before": before, "after": after, "steps": steps,
                "elapsed_ms": round((time.monotonic() - t0) * 1000)}

    def stop_all(self) -> Dict[str, Any]:
        imsis = sorted({p["imsi"] for p in self.scan_processes()["ues"] if p["imsi"]})
        results = [self.stop_ue(i) for i in imsis]
        return {"success": all(r["success"] for r in results), "stopped": imsis, "results": results}

    def cleanup_orphan_tuns(self) -> Dict[str, Any]:
        """Delete TUNs not attributed to any live UE — only if no unidentified nr-ue is running."""
        t = self.telemetry()
        if t["unidentified_processes"]:
            return {"success": False, "deleted": [], "error": "Unidentified nr-ue processes running; refusing to guess TUN ownership"}
        deleted = []
        for tun in t["unattributed_tuns"]:
            subprocess.run(["ip", "link", "delete", tun["interface"]], capture_output=True)
            deleted.append(tun["interface"])
        return {"success": True, "deleted": deleted}

    def traffic(self, imsi: str, kind: str, target: Optional[str] = None) -> Dict[str, Any]:
        """Run real traffic bound to THIS IMSI's TUN. Refuses if the UE is not active."""
        st = self.ue_state(imsi)
        if st["radio_state"] != "active":
            return {"success": False, "imsi": st["imsi"], "error": f"UE not active (radio_state={st['radio_state']})", "state": st}
        iface, ip = st["interface"], st["ip"]
        if kind == "ping":
            tgt = target or "8.8.8.8"
            cmd = ["ping", "-I", iface, "-c", "3", "-W", "2", tgt]
        else:
            tgt = target or ("http://wicar.org/data/ms14-064.html" if kind == "threat_blocked" else "https://paloaltonetworks.com")
            cmd = ["curl", "--interface", iface, "-s", "-m", "5", "-o", "/dev/null",
                   "-w", "HTTP_CODE:%{http_code} TIME_TOTAL:%{time_total}", tgt]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            out = (r.stdout + r.stderr).strip()
            rc = r.returncode
        except subprocess.TimeoutExpired:
            out, rc = "timeout", -1
        return {"success": True, "imsi": st["imsi"], "interface": iface, "assigned_ip": ip,
                "traffic_type": kind, "target": tgt, "exit_code": rc, "raw_output": out[-2000:]}
