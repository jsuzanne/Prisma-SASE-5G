"""UERANSIM RAN client (core side) — talks to the RAN agent over HTTP.

The RAN agent (agent_app.py on the UERANSIM host) is the ONLY component that
starts/stops nr-ue processes and touches uesimtun interfaces. This client:
  - generates the 3GPP UE YAML (from the endpoint / MongoDB credentials),
  - calls the agent REST API (X-Agent-Token over the private 10.10.10.0/24 link),
  - never guesses: no `uesimtun0` default, no fallback IP, no SSH.

If the agent is unreachable, state is reported as `unknown` (never `stopped`),
so nothing downstream prunes sessions on a network blip.

Env:
  UE_AGENT_URL   (default http://10.10.10.2:8081)
  AGENT_TOKEN    shared secret, same value as on the agent
  DEBUG=true     verbose logs of every agent call
  MOCK_MODE=true in-memory simulation for tests / offline demo
"""

from typing import Dict, List, Optional, Any
import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.request
import uuid

from src.models import (
    OrchestratedEndpoint,
    SecurityConfig,
    SliceConfig,
    QoSConfig,
)

logger = logging.getLogger("UERANSIMClient")
DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes", "on")


class AgentUnavailable(Exception):
    """The RAN agent could not be reached or returned an unusable answer."""


def _clean(imsi: str) -> str:
    return re.sub(r"\D", "", str(imsi))


def _pdu_status(radio_state: Optional[str]) -> str:
    return {
        "active": "PS-ACTIVE",
        "connecting": "CONNECTING",
        "failed": "FAILED",
        "stopped": "STOPPED",
        "unknown": "UNKNOWN",
    }.get(radio_state or "unknown", "UNKNOWN")


def _compat_status(ue: Dict[str, Any], agent_ok: bool = True) -> Dict[str, Any]:
    """Map an agent UE record to the legacy status shape used by app.py / the UI."""
    radio = ue.get("radio_state") if agent_ok else "unknown"
    return {
        "imsi": ue.get("imsi"),
        "running": ue.get("process_alive") if agent_ok else None,
        "pid": ue.get("pid"),
        "pdu_status": _pdu_status(radio),
        "radio_state": radio,
        "reason": ue.get("reason") if agent_ok else "RAN agent unreachable",
        "interface": ue.get("interface"),
        "assigned_ip": ue.get("ip"),
        "last_error": ue.get("last_error"),
        "agent_reachable": agent_ok,
    }


class UERANSIMClient:
    """Core-side client for the RAN agent (single owner of nr-ue / uesimtun)."""

    def __init__(
        self,
        agent_url: Optional[str] = None,
        agent_token: Optional[str] = None,
        gnb_search_list: Optional[List[str]] = None,
        mcc: str = "999",
        mnc: str = "70",
        mock_mode: bool = False,
        timeout_s: float = 3.0,
        telemetry_ttl_s: float = 1.0,
        # Legacy kwargs accepted for backward compatibility (ignored):
        ueransim_dir: Optional[str] = None,
        ssh_host: Optional[str] = None,
    ):
        self.agent_url = (agent_url or os.environ.get("UE_AGENT_URL", "http://10.10.10.2:8081")).rstrip("/")
        self.agent_token = agent_token if agent_token is not None else os.environ.get("AGENT_TOKEN", "")
        self.gnb_search_list = gnb_search_list or ["10.10.10.2"]
        self.mcc = mcc
        self.mnc = mnc
        self.mock_mode = mock_mode or (os.environ.get("MOCK_MODE", "false").lower() == "true")
        self.timeout_s = timeout_s
        self.telemetry_ttl_s = telemetry_ttl_s
        self._tele_cache: Optional[Dict[str, Any]] = None
        self._tele_at = 0.0
        self._tele_lock = threading.Lock()
        self._mock_processes: Dict[str, Dict[str, Any]] = {}
        self._mock_next_ip = 2
        # Kept for UI/log display only
        self.ssh_host = None

    # ------------------------------------------------------------------
    # YAML generation (unchanged 3GPP config)
    # ------------------------------------------------------------------
    def generate_ue_yaml(self, endpoint: OrchestratedEndpoint) -> str:
        """Generate UERANSIM YAML configuration for an endpoint."""
        imsi = str(endpoint.imsi)
        supi = f"imsi-{imsi}" if not imsi.startswith("imsi-") else imsi
        clean_imsi = re.sub(r"\D", "", imsi)
        if len(clean_imsi) >= 5:
            mcc = clean_imsi[:3]
            mnc = clean_imsi[3:5]
        else:
            mcc = self.mcc
            mnc = self.mnc

        k = endpoint.security.k.upper()
        op = endpoint.security.op.upper()
        op_type = endpoint.security.op_type.upper()
        amf = endpoint.security.amf
        imei = endpoint.imei
        # Ensure IMEISV is exactly 16 digits (TAC 8 + SNR 6 + SV 2)
        imeisv = f"{imei[:14]}01" if len(imei) >= 14 else f"{imei}01"

        sst = endpoint.slice.sst
        sd_session = f"\n      sd: {endpoint.slice.sd}" if endpoint.slice.sd else ""
        sd_nssai = f"\n    sd: {endpoint.slice.sd}" if endpoint.slice.sd else ""
        gnb_entries = "\n".join([f"  - {ip}" for ip in self.gnb_search_list])

        yaml_content = f"""# UERANSIM Config for {endpoint.device_name} ({endpoint.vertical_id})
# Auto-generated by Prisma 5G Orchestrator
supi: '{supi}'
mcc: '{mcc}'
mnc: '{mnc}'
protectionScheme: 0
homeNetworkPublicKey: '5a8d38864820197c3394b92613b20b91633cbd897119273bf8e4a6f4eec0a650'
homeNetworkPublicKeyId: 1
routingIndicator: '0000'

key: '{k}'
op: '{op}'
opType: '{op_type}'
amf: '{amf}'
imei: '{imei}'
imeiSv: '{imeisv}'

tunNetmask: '255.255.255.0'
useNamespace: false

gnbSearchList:
{gnb_entries}

uacAic:
  mps: false
  mcs: false

uacAcc:
  normalClass: 0
  class11: false
  class12: false
  class13: false
  class14: false
  class15: false

sessions:
  - type: 'IPv4'
    apn: '{endpoint.apn}'
    slice:
      sst: {sst}{sd_session}

configured-nssai:
  - sst: {sst}{sd_nssai}

default-nssai:
  - sst: {sst}{sd_nssai}

integrity:
  IA1: true
  IA2: true
  IA3: true

ciphering:
  EA1: true
  EA2: true
  EA3: true

integrityMaxRate:
  uplink: 'full'
  downlink: 'full'
"""
        return yaml_content

    # ------------------------------------------------------------------
    # Agent transport
    # ------------------------------------------------------------------
    def _call(self, method: str, path: str, body: Optional[Dict[str, Any]] = None,
              timeout: Optional[float] = None) -> Dict[str, Any]:
        if not self.agent_token:
            raise AgentUnavailable("AGENT_TOKEN not configured on the core")
        rid = uuid.uuid4().hex[:8]
        url = f"{self.agent_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "X-Agent-Token": self.agent_token,
            "X-Request-Id": rid,
            "Content-Type": "application/json",
        })
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout_s) as resp:
                payload = json.loads(resp.read().decode() or "{}")
            ms = round((time.monotonic() - t0) * 1000)
            log_level = logging.DEBUG if method == "GET" else logging.INFO
            logger.log(log_level, "event=agent.call req=%s %s %s -> 200 in %sms", rid, method, path, ms)
            return payload
        except urllib.error.HTTPError as e:
            ms = round((time.monotonic() - t0) * 1000)
            detail = e.read().decode(errors="replace")[:300]
            logger.warning("event=agent.call req=%s %s %s -> HTTP %s in %sms detail=%s", rid, method, path, e.code, ms, detail)
            if e.code == 409:
                raise AgentUnavailable(f"Action already in progress on agent ({detail})")
            raise AgentUnavailable(f"Agent HTTP {e.code}: {detail}")
        except Exception as e:
            ms = round((time.monotonic() - t0) * 1000)
            logger.warning("event=agent.unreachable req=%s %s %s after %sms error=%r", rid, method, path, ms, str(e))
            raise AgentUnavailable(f"RAN agent unreachable at {self.agent_url}: {e}")

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------
    def telemetry(self, max_age_s: Optional[float] = None) -> Dict[str, Any]:
        """Agent telemetry (cached ~1s). Returns {"ok": False, "error": ...} if unreachable."""
        if self.mock_mode:
            return self._mock_telemetry()
        ttl = self.telemetry_ttl_s if max_age_s is None else max_age_s
        with self._tele_lock:
            if self._tele_cache is not None and (time.monotonic() - self._tele_at) < ttl:
                return self._tele_cache
        try:
            t = self._call("GET", "/api/agent/telemetry")
            t["ok"] = True
        except AgentUnavailable as e:
            t = {"ok": False, "error": str(e), "ues": [], "tuns": [], "processes": [],
                 "unattributed_tuns": [], "unidentified_processes": [], "gnb": {"running": None, "pids": []}}
        with self._tele_lock:
            self._tele_cache, self._tele_at = t, time.monotonic()
        return t

    def invalidate_cache(self) -> None:
        with self._tele_lock:
            self._tele_cache = None

    def get_ue_status(self, imsi: str) -> Dict[str, Any]:
        """Live radio state for one IMSI (radio_state: active/connecting/failed/stopped/unknown)."""
        clean = _clean(imsi)
        t = self.telemetry(max_age_s=0.5)
        if not t.get("ok"):
            return _compat_status({"imsi": clean}, agent_ok=False) | {"reason": t.get("error")}
        ue = next((u for u in t["ues"] if u["imsi"] == clean), None)
        if ue is None:
            ue = {"imsi": clean, "process_alive": False, "radio_state": "stopped",
                  "reason": "no nr-ue process and no log for this IMSI"}
        return _compat_status(ue)

    def list_active_ues(self) -> List[Dict[str, Any]]:
        """UEs with a live nr-ue process (any radio_state)."""
        t = self.telemetry()
        return [_compat_status(u) for u in t.get("ues", []) if u.get("process_alive")]

    def get_active_tun_interfaces(self) -> List[Dict[str, Any]]:
        """Kernel uesimtun interfaces on the RAN host (as seen by the agent)."""
        t = self.telemetry()
        return [{
            "interface": x["interface"],
            "status": "UP" if x.get("up") else (x.get("operstate") or "DOWN"),
            "ip": x.get("ip"),
            "cidr": f"{x['ip']}/24" if x.get("ip") else None,
        } for x in t.get("tuns", [])]

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------
    def start_ue(self, endpoint: OrchestratedEndpoint, timeout_s: float = 15.0) -> Dict[str, Any]:
        """Power on: send YAML to the agent, which waits until the kernel TUN is up or fails."""
        imsi = _clean(endpoint.imsi)
        if self.mock_mode:
            return self._mock_start(imsi)
        yaml_content = self.generate_ue_yaml(endpoint)
        try:
            r = self._call("POST", f"/api/agent/ue/{imsi}/start",
                           {"yaml": yaml_content, "timeout_s": timeout_s}, timeout=timeout_s + 15)
        except AgentUnavailable as e:
            return _compat_status({"imsi": imsi}, agent_ok=False) | {
                "success": False, "error": str(e), "initial_logs": ""}
        finally:
            self.invalidate_cache()
        state = r.get("state") or {"imsi": imsi}
        return _compat_status(state) | {
            "success": bool(r.get("success")),
            "error": r.get("error"),
            "elapsed_ms": r.get("elapsed_ms"),
            "initial_logs": r.get("logs", ""),
        }

    def stop_ue_detail(self, imsi: str) -> Dict[str, Any]:
        clean = _clean(imsi)
        if self.mock_mode:
            self._mock_processes.pop(clean, None)
            return {"success": True, "imsi": clean, "steps": ["mock stop"]}
        try:
            return self._call("POST", f"/api/agent/ue/{clean}/stop", timeout=20)
        except AgentUnavailable as e:
            return {"success": False, "imsi": clean, "error": str(e), "steps": []}
        finally:
            self.invalidate_cache()

    def stop_ue(self, imsi: str) -> bool:
        """Power off one IMSI (graceful 3GPP deregistration, then kill). True if confirmed stopped."""
        return bool(self.stop_ue_detail(imsi).get("success"))

    def stop_all_ues(self) -> bool:
        if self.mock_mode:
            self._mock_processes.clear()
            return True
        try:
            return bool(self._call("POST", "/api/agent/stop-all", timeout=120).get("success"))
        except AgentUnavailable:
            return False
        finally:
            self.invalidate_cache()

    def cleanup_orphan_tuns(self) -> List[str]:
        """Delete TUNs not attributed to any live UE (agent refuses if ownership is ambiguous)."""
        if self.mock_mode:
            return []
        try:
            return self._call("POST", "/api/agent/cleanup-tuns", timeout=10).get("deleted", [])
        except AgentUnavailable:
            return []
        finally:
            self.invalidate_cache()

    def get_ue_logs(self, imsi: str, lines: int = 50) -> Dict[str, Any]:
        clean = _clean(imsi)
        if self.mock_mode:
            return {"imsi": clean, "log_path": f"/tmp/nr-ue-{clean}.log", "lines": lines, "logs": (
                "[rrc] [info] RRC connection established\n"
                "[nas] [info] Initial Registration is successful\n"
                "[nas] [info] PDU Session establishment is successful PSI[1]\n"
                "[app] [info] Connection setup for PDU session[1] is successful, TUN interface[uesimtun0, 10.45.0.2] is up.")}
        try:
            return self._call("GET", f"/api/agent/ue/{clean}/logs?lines={int(lines)}")
        except AgentUnavailable as e:
            return {"imsi": clean, "log_path": None, "lines": lines, "logs": f"[RAN agent unreachable] {e}"}

    def get_agent_events(self, limit: int = 100, imsi: Optional[str] = None) -> Dict[str, Any]:
        if self.mock_mode:
            return {"events": []}
        q = f"limit={int(limit)}" + (f"&imsi={_clean(imsi)}" if imsi else "")
        try:
            return self._call("GET", f"/api/agent/events?{q}")
        except AgentUnavailable as e:
            return {"events": [], "error": str(e)}

    def imsi_for_interface(self, iface: str) -> Optional[str]:
        t = self.telemetry(max_age_s=0.5)
        return next((u["imsi"] for u in t.get("ues", []) if u.get("interface") == iface), None)

    # ------------------------------------------------------------------
    # Traffic (always bound to THIS IMSI's own TUN, refused if not active)
    # ------------------------------------------------------------------
    def exec_ue_traffic(self, imsi: str, traffic_type: str = "allowed", target_url: Optional[str] = None) -> Dict[str, Any]:
        clean = _clean(imsi)
        if self.mock_mode:
            return self._mock_traffic(clean, traffic_type, target_url)
        try:
            r = self._call("POST", f"/api/agent/ue/{clean}/traffic",
                           {"traffic_type": traffic_type, "target_url": target_url}, timeout=25)
        except AgentUnavailable as e:
            return {"success": False, "imsi": clean, "traffic_type": traffic_type, "error": str(e)}
        if not r.get("success"):
            return {"success": False, "imsi": clean, "traffic_type": traffic_type,
                    "error": r.get("error"), "state": r.get("state")}
        return self._interpret_traffic(r)

    @staticmethod
    def _interpret_traffic(r: Dict[str, Any]) -> Dict[str, Any]:
        out = r.get("raw_output", "") or ""
        base = {"success": True, "imsi": r["imsi"], "interface": r["interface"],
                "assigned_ip": r["assigned_ip"], "target": r["target"],
                "traffic_type": r["traffic_type"], "raw_output": out}
        kind = r["traffic_type"]
        if kind == "ping":
            rtt = re.search(r"rtt min/avg/max/mdev = ([0-9.]+)/([0-9.]+)/", out)
            loss = re.search(r"([0-9.]+)% packet loss", out)
            received = re.search(r"(\d+) (?:packets )?received", out)
            ok = bool(received and int(received.group(1)) > 0)
            return base | {"status": "SUCCESS" if ok else "FAILED",
                           "latency_ms": float(rtt.group(2)) if rtt else None,
                           "packet_loss": f"{loss.group(1)}%" if loss else None}
        code_m = re.search(r"HTTP_CODE:(\d+)", out)
        time_m = re.search(r"TIME_TOTAL:([0-9.]+)", out)
        code = int(code_m.group(1)) if code_m else 0
        rtt = float(time_m.group(1)) if time_m else None
        if kind == "threat_blocked":
            blocked = code in (0, 403) or "reset" in out.lower()
            return base | {"status": "BLOCKED_BY_PRISMA_SASE" if blocked else "RECEIVED",
                           "http_code": code, "rtt_seconds": rtt,
                           "security_verdict": "Threat Blocked (Zero-Trust Enforcement)" if blocked else "Not blocked",
                           "threat_name": "Exploit-Test/WICAR.SecurityTest",
                           "scm_correlation_hint": f"Search SCM Threat logs for IP {r['assigned_ip']} / IMSI {r['imsi']}"}
        ok = code > 0
        return base | {"status": "SUCCESS" if ok else "FAILED", "http_code": code, "rtt_seconds": rtt,
                       "security_verdict": "Allowed (Clean Traffic)" if 200 <= code < 400 else f"HTTP {code or 'no response'}"}

    def ping(self, imsi: str, target: str = "10.45.0.1") -> Dict[str, Any]:
        """ICMP through the IMSI's own TUN (used by the Live Telemetry 'Ping Data Plane' button)."""
        clean = _clean(imsi)
        if self.mock_mode:
            return self._mock_traffic(clean, "ping", target)
        try:
            r = self._call("POST", f"/api/agent/ue/{clean}/traffic",
                           {"traffic_type": "ping", "target_url": target}, timeout=25)
        except AgentUnavailable as e:
            return {"success": False, "imsi": clean, "error": str(e)}
        if not r.get("success"):
            return {"success": False, "imsi": clean, "error": r.get("error")}
        return self._interpret_traffic(r)

    # ------------------------------------------------------------------
    # Mock mode (tests / offline)
    # ------------------------------------------------------------------
    def _mock_start(self, imsi: str) -> Dict[str, Any]:
        if imsi not in self._mock_processes:
            self._mock_processes[imsi] = {
                "imsi": imsi, "pid": 90000 + len(self._mock_processes),
                "interface": f"uesimtun{len(self._mock_processes)}", "ip": f"10.45.0.{self._mock_next_ip}",
            }
            self._mock_next_ip += 1
        p = self._mock_processes[imsi]
        ue = {"imsi": imsi, "pid": p["pid"], "process_alive": True, "radio_state": "active",
              "reason": "mock", "interface": p["interface"], "ip": p["ip"]}
        return _compat_status(ue) | {"success": True, "status": "running", "error": None, "initial_logs": ""}

    def _mock_telemetry(self) -> Dict[str, Any]:
        ues = [{"imsi": p["imsi"], "pid": p["pid"], "process_alive": True, "duplicate_processes": False,
                "radio_state": "active", "reason": "mock", "log_phase": "pdu_active", "last_error": None,
                "interface": p["interface"], "ip": p["ip"]} for p in self._mock_processes.values()]
        return {"ok": True, "mock": True, "gnb": {"running": True, "pids": [1]},
                "processes": [{"pid": u["pid"], "imsi": u["imsi"]} for u in ues],
                "unidentified_processes": [], "ues": ues, "unattributed_tuns": [],
                "tuns": [{"interface": u["interface"], "ip": u["ip"], "up": True} for u in ues], "scan_ms": 0}

    @staticmethod
    def _mock_traffic(imsi: str, traffic_type: str, target: Optional[str]) -> Dict[str, Any]:
        base = {"success": True, "imsi": imsi, "interface": "uesimtun0", "assigned_ip": "10.45.0.2",
                "traffic_type": traffic_type, "mock": True}
        if traffic_type == "threat_blocked":
            return base | {"target": target or "http://wicar.org/data/ms14-064.html",
                           "status": "BLOCKED_BY_PRISMA_SASE", "http_code": 403,
                           "security_verdict": "Threat Blocked (Zero-Trust Enforcement)",
                           "threat_name": "Exploit-Payload/Generic.Wicar"}
        if traffic_type == "ping":
            return base | {"target": target or "8.8.8.8", "status": "SUCCESS", "latency_ms": 14.2,
                           "packet_loss": "0%"}
        return base | {"target": target or "https://paloaltonetworks.com", "status": "SUCCESS",
                       "http_code": 200, "rtt_seconds": 0.082, "security_verdict": "Allowed (Clean Traffic)"}
