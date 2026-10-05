#!/usr/bin/env bash
# agent-ctl — test & debug the RAN agent from the Core VM (152.236.5.40).
#
# Usage:
#   agent-ctl status                 # per-IMSI state + reason, TUNs, gNB
#   agent-ctl watch                  # status refreshed every 2s
#   agent-ctl start <IMSI>           # power on (YAML built from MongoDB subscriber)
#   agent-ctl stop  <IMSI>           # graceful power off (3GPP deregister -> kill)
#   agent-ctl stop-all
#   agent-ctl events [IMSI] [N]      # recent agent events (transitions, steps, errors)
#   agent-ctl logs  <IMSI> [N]       # nr-ue radio log
#   agent-ctl core  [IMSI]           # what AMF/SMF think (to compare with the agent)
#   agent-ctl raw   <path>           # raw GET on any /api/agent/* path
#
# Token: read from $AGENT_TOKEN or ~/Docker/5g-orchestrator/agent.env
set -euo pipefail

AGENT_URL="${AGENT_URL:-http://10.10.10.2:8081}"
ENV_FILE="${AGENT_ENV_FILE:-$HOME/Docker/5g-orchestrator/agent.env}"
CORE_CONTAINER="${CORE_CONTAINER:-prisma-5g-core}"
if [ -z "${AGENT_TOKEN:-}" ] && [ -f "$ENV_FILE" ]; then
  AGENT_TOKEN="$(grep -E '^AGENT_TOKEN=' "$ENV_FILE" | cut -d= -f2-)"
fi
: "${AGENT_TOKEN:?AGENT_TOKEN not set (export it or create $ENV_FILE)}"

call() {  # call METHOD PATH [JSON_BODY]
  local m="$1" p="$2" b="${3:-}"
  if [ -n "$b" ]; then
    curl -sS -m 45 -X "$m" -H "X-Agent-Token: $AGENT_TOKEN" -H 'Content-Type: application/json' --data-binary "$b" "$AGENT_URL$p"
  else
    curl -sS -m 45 -X "$m" -H "X-Agent-Token: $AGENT_TOKEN" "$AGENT_URL$p"
  fi
}
pretty() { python3 -m json.tool 2>/dev/null || cat; }

# ---- Python formatters (quoted heredocs: no shell escaping) -----------------
read -r -d '' PY_STATUS <<'PY' || true
import json, sys
t = json.load(sys.stdin)
g = t["gnb"]
print(f"agent scan {t['scan_ms']}ms   gNB running={g['running']} pids={g['pids']}")
print("kernel TUNs: " + (", ".join(f"{x['interface']}={x['ip']}" for x in t["tuns"]) or "none"))
if t["unattributed_tuns"]:
    print("  !! unattributed TUNs: " + ", ".join(x["interface"] for x in t["unattributed_tuns"]))
if t["unidentified_processes"]:
    print("  !! nr-ue processes with unknown IMSI: " + ", ".join(str(p["pid"]) for p in t["unidentified_processes"]))
print()
print(f"{'IMSI':<17}{'STATE':<12}{'PID':<9}{'TUN':<11}{'IP':<14}REASON")
for u in t["ues"]:
    print(f"{u['imsi']:<17}{u['radio_state']:<12}{str(u['pid'] or '-'):<9}{u['interface'] or '-':<11}{u['ip'] or '-':<14}{u['reason']}")
if not t["ues"]:
    print("(no UE process and no UE log on the RAN host)")
PY

read -r -d '' PY_START <<'PY' || true
import json, sys
r = json.load(sys.stdin)
s = r.get("state") or {}
tag = "OK  " if r.get("success") else "FAIL"
print(f"{tag} {r.get('imsi')} in {r.get('elapsed_ms')}ms  state={s.get('radio_state')} tun={s.get('interface')} ip={s.get('ip')}")
print("reason:", s.get("reason"))
if not r.get("success"):
    print("error :", r.get("error"))
    print("--- last radio log lines ---")
    print("\n".join((r.get("logs") or "").splitlines()[-15:]))
PY

read -r -d '' PY_STOP <<'PY' || true
import json, sys
r = json.load(sys.stdin)
tag = "OK  " if r.get("success") else "FAIL"
print(f"{tag} {r.get('imsi')} stopped in {r.get('elapsed_ms')}ms")
for s in r.get("steps", []):
    print("  -", s)
PY

read -r -d '' PY_EVENTS <<'PY' || true
import json, sys
skip = ("ts", "level", "event", "imsi")
for e in reversed(json.load(sys.stdin)["events"]):
    extra = " ".join(f"{k}={v}" for k, v in e.items() if k not in skip and v not in (None, ""))
    print(f"{e['ts'][11:23]} {e['level']:<7} {e['event']:<24} {e.get('imsi') or '':<16} {extra}")
PY

read -r -d '' PY_AMF <<'PY' || true
import json, sys
f = sys.argv[1] if len(sys.argv) > 1 else ""
for i in json.load(sys.stdin).get("items", []):
    if f in i["supi"]:
        print(f"  {i['supi']:<22} mm_state={str(i.get('mm_state')):<13} cm_state={i.get('cm_state')}")
PY

read -r -d '' PY_SMF <<'PY' || true
import json, sys
f = sys.argv[1] if len(sys.argv) > 1 else ""
for i in json.load(sys.stdin).get("items", []):
    if f in i["supi"]:
        for p in i.get("pdu", []):
            print(f"  {i['supi']:<22} ip={str(p.get('ipv4')):<12} pdu_state={p.get('pdu_state')}")
PY

read -r -d '' PY_YAML <<'PY' || true
import sys
sys.path.insert(0, "/app")
from src.open5gs import Open5GSClient
from src.ueransim import UERANSIMClient
from src.models import OrchestratedEndpoint, SecurityConfig, SliceConfig, QoSConfig
imsi = sys.argv[1]
sub = Open5GSClient().get_subscriber(imsi)
if not sub:
    sys.exit(f"IMSI {imsi} is not provisioned in MongoDB")
sec, sl = sub["security"], sub["slice"][0]
ep = OrchestratedEndpoint(
    imsi=imsi, imei=(sub.get("imeisv") or "356938035643800")[:15], apn=sl["session"][0]["name"],
    vertical_id="cli", device_name="agent-ctl", vendor="cli", device_model="cli", icon="cli",
    security=SecurityConfig(k=sec["k"], op=sec.get("opc") or sec.get("op"),
                            op_type="OPC" if sec.get("opc") else "OP"),
    slice=SliceConfig(sst=sl["sst"], sd=sl.get("sd")),
    qos=QoSConfig(five_qi=9, ambr_dl_mbps=100, ambr_ul_mbps=50))
print(UERANSIMClient().generate_ue_yaml(ep))
PY

status() { call GET /api/agent/telemetry | python3 -c "$PY_STATUS"; }

cmd="${1:-status}"; shift || true
case "$cmd" in
  status) status ;;
  watch)  while true; do clear; date; status; sleep 2; done ;;
  start)
    imsi="${1:?usage: agent-ctl start <IMSI>}"
    yaml="$(docker exec "$CORE_CONTAINER" python -c "$PY_YAML" "$imsi")"
    body="$(python3 -c 'import json,sys; print(json.dumps({"yaml": sys.stdin.read(), "timeout_s": 15}))' <<<"$yaml")"
    call POST "/api/agent/ue/$imsi/start" "$body" | python3 -c "$PY_START" ;;
  stop)
    imsi="${1:?usage: agent-ctl stop <IMSI>}"
    call POST "/api/agent/ue/$imsi/stop" | python3 -c "$PY_STOP" ;;
  stop-all) call POST /api/agent/stop-all | pretty ;;
  events)
    q="limit=${2:-40}"; [ -n "${1:-}" ] && q="$q&imsi=$1"
    call GET "/api/agent/events?$q" | python3 -c "$PY_EVENTS" ;;
  logs)
    call GET "/api/agent/ue/${1:?usage: agent-ctl logs <IMSI>}/logs?lines=${2:-60}" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin)["logs"])' ;;
  core)
    echo "== AMF (only mm_state=registered counts as attached) =="
    curl -s 'http://127.0.0.5:9090/ue-info?page=-1' | python3 -c "$PY_AMF" "${1:-}"
    echo "== SMF PDU sessions =="
    curl -s 'http://127.0.0.4:9090/pdu-info?page=-1' | python3 -c "$PY_SMF" "${1:-}" ;;
  raw) call GET "${1:?usage: agent-ctl raw /api/agent/...}" | pretty ;;
  *) sed -n '2,15p' "$0"; exit 1 ;;
esac
