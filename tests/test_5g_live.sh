#!/bin/bash
# Comprehensive 5G Function Test Suite
BASE="http://localhost:8081"
IMSI="999700000000001"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
NC="\033[0m"

pass() { echo -e "${GREEN}PASS${NC} $1"; }
fail() { echo -e "${RED}FAIL${NC} $1"; }
info() { echo -e "${YELLOW}INFO${NC} $1"; }

test_json() {
  local label="$1"
  local result="$2"
  local success=$(echo "$result" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("success","N/A"))' 2>/dev/null)
  local msg=$(echo "$result" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(str(d.get("message",""))[:70])' 2>/dev/null)
  if [ "$success" = "True" ]; then
    pass "$label | $msg"
  else
    fail "$label | result: ${result:0:120}"
  fi
}

echo ""
echo "======================================================"
echo "  PRISMA SASE 5G - Full Function Test Suite"
echo "======================================================"

# TEST 1: Fleet Power Off
echo ""; echo "-- TEST 1: Fleet Power Off --"
R=$(curl -s -X POST "$BASE/api/5g/fleet/power-off" -m 15)
test_json "fleet/power-off" "$R"
sleep 2
TUNS=$(ip -br a 2>/dev/null | grep uesimtun | wc -l)
[ "$TUNS" -eq 0 ] && pass "TUN cleaned (count=0)" || fail "TUN still present: $TUNS"

# TEST 2: Clean Orphan TUNs
echo ""; echo "-- TEST 2: Clean Orphan TUNs --"
R=$(curl -s -X POST "$BASE/api/5g/fleet/clean-tuns" -m 10)
test_json "fleet/clean-tuns" "$R"
CLEANED=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("count",0))' 2>/dev/null)
info "Cleaned $CLEANED orphan TUN(s)"

# TEST 3: Single UE Attach
echo ""; echo "-- TEST 3: Single UE Attach ($IMSI) --"
R=$(curl -s -X POST "$BASE/api/5g/ue/attach/$IMSI" -m 20)
test_json "ue/attach/$IMSI" "$R"
IF=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("interface","??"))' 2>/dev/null)
IP=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("allocated_ip","??"))' 2>/dev/null)
PDU=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("pdu_status","??"))' 2>/dev/null)
info "Interface=$IF  IP=$IP  PDU=$PDU"
sleep 3
TUNS=$(ip -br a 2>/dev/null | grep uesimtun)
[ -n "$TUNS" ] && pass "TUN UP: $TUNS" || fail "No TUN after attach"

# TEST 4: UE Status
echo ""; echo "-- TEST 4: UE Status --"
R=$(curl -s "$BASE/api/5g/ue/status/$IMSI" -m 10)
PDU=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("pdu_status","??"))' 2>/dev/null)
IF=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("interface","??"))' 2>/dev/null)
info "PDU=$PDU Interface=$IF"
[ "$PDU" = "PS-ACTIVE" ] && pass "ue/status = PS-ACTIVE" || fail "ue/status = $PDU"

# TEST 5: UE Logs
echo ""; echo "-- TEST 5: UE Logs --"
R=$(curl -s "$BASE/api/5g/ue/logs/$IMSI" -m 10)
LOGS=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); l=d.get("logs",""); print(len(l), l[-80:] if l else "")' 2>/dev/null)
echo "  Logs: $LOGS"
echo "$R" | python3 -c 'import sys,json; l=json.load(sys.stdin).get("logs",""); exit(0 if len(l)>10 else 1)' 2>/dev/null \
  && pass "ue/logs has content" || fail "ue/logs empty"

# TEST 6: Traffic - PING
echo ""; echo "-- TEST 6: Traffic - PING --"
R=$(curl -s -X POST "$BASE/api/5g/ue/traffic" -H 'Content-Type: application/json' \
  -d "{\"imsi\":\"$IMSI\",\"traffic_type\":\"ping\"}" -m 20)
test_json "ue/traffic ping" "$R"
LAT=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("latency_ms","??"))' 2>/dev/null)
LOSS=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("packet_loss","??"))' 2>/dev/null)
info "latency=${LAT}ms packet_loss=$LOSS"

# TEST 7: Traffic - Allowed HTTP
echo ""; echo "-- TEST 7: Traffic - Allowed HTTP --"
R=$(curl -s -X POST "$BASE/api/5g/ue/traffic" -H 'Content-Type: application/json' \
  -d "{\"imsi\":\"$IMSI\",\"traffic_type\":\"allowed\"}" -m 20)
test_json "ue/traffic allowed" "$R"
CODE=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("http_code","??"))' 2>/dev/null)
RTT=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("rtt_seconds","??"))' 2>/dev/null)
info "HTTP code=$CODE rtt=${RTT}s"

# TEST 8: Traffic - Threat Blocked
echo ""; echo "-- TEST 8: Traffic - Threat Blocked --"
R=$(curl -s -X POST "$BASE/api/5g/ue/traffic" -H 'Content-Type: application/json' \
  -d "{\"imsi\":\"$IMSI\",\"traffic_type\":\"threat_blocked\"}" -m 20)
test_json "ue/traffic threat_blocked" "$R"
VERDICT=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("security_verdict","??"))' 2>/dev/null)
STATUS=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("status","??"))' 2>/dev/null)
info "verdict=$VERDICT status=$STATUS"

# TEST 9: UE Detach
echo ""; echo "-- TEST 9: UE Detach --"
R=$(curl -s -X POST "$BASE/api/5g/ue/detach/$IMSI" -m 15)
test_json "ue/detach/$IMSI" "$R"
sleep 3
TUNS=$(ip -br a 2>/dev/null | grep uesimtun | wc -l)
[ "$TUNS" -eq 0 ] && pass "TUN cleaned after detach" || info "TUN still: $TUNS (may persist briefly)"

# TEST 10: Fleet Power On
echo ""; echo "-- TEST 10: Fleet Power On --"
R=$(curl -s -X POST "$BASE/api/5g/fleet/power-on" -H 'Content-Type: application/json' -d '{}' -m 60)
test_json "fleet/power-on" "$R"
TOTAL=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("total_attempted",0))' 2>/dev/null)
ACTIVE=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("active_count",0))' 2>/dev/null)
info "attempted=$TOTAL active=$ACTIVE"
sleep 15  # Fleet of 4 UEs needs ~3s each for 5G-AKA + PDU session
TUNS=$(ip -br a 2>/dev/null | grep uesimtun)
[ -n "$TUNS" ] && pass "Fleet TUN(s) UP after power-on" || fail "No TUN after fleet power-on"

# TEST 11: 5G Core Monitoring
echo ""; echo "-- TEST 11: 5G Core Monitoring --"
R=$(curl -s "$BASE/api/5g/monitoring" -m 10)
STATUS=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("overall_status","??"))' 2>/dev/null)
ACTIVE_UES=$(echo "$R" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("ran",{}).get("active_tun_count",0))' 2>/dev/null)
info "overall_status=$STATUS  active_tun_count=$ACTIVE_UES"
[ -n "$STATUS" ] && pass "5g/monitoring responds" || fail "5g/monitoring failed"

# SUMMARY
echo ""
echo "======================================================"
echo "  Final TUN State:"
ip -br a 2>/dev/null | grep uesimtun || echo "  (no uesimtun interfaces)"
echo "======================================================"
