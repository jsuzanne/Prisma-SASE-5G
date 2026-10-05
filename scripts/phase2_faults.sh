#!/usr/bin/env bash
# Phase 2 failure-mode test — run ON the core VM: bash phase2_faults.sh IMSI_A IMSI_B
B=http://127.0.0.1:8080
A=${1:-999703875813789}; C=${2:-999701249550336}
RAN=jsuzanne@10.10.10.2
J() { python3 -c "import json,sys;d=json.load(sys.stdin);$1"; }
show() { curl -s "$B/api/state?fresh=${2:-false}" | J "
src=d['sources'];print('  [$1] agent_ok=',src['agent']['ok'],'| summary=',d['summary'])
for i in ('$A','$C'):
  s=d['sims'].get(i,{});print('   ',i,s.get('status'),s.get('live_ip'),s.get('interface'),'|',(s.get('reason') or '')[:110])"; }

echo "== 1. power on two UEs"
for i in $A $C; do curl -s -X POST $B/api/5g/ue/attach/$i | J "print('  ',d['imsi'],d['success'],d.get('interface'),d.get('allocated_ip'),d.get('reason') or '')"; done
show after-attach true
curl -s $B/api/ues | J "[print('   ues',x['imsi'],x['status'],x['ipv4_addr'],x.get('interface')) for x in d['data'] if str(x['imsi']) in ('$A','$C')]"

echo "== 2. kill -9 nr-ue of $C (ungraceful: core keeps the session)"
PID=$(curl -s "$B/api/state?fresh=true" | J "print(d['sims']['$C']['radio']['pid'])")
echo "   pid=$PID"; ssh -o BatchMode=yes $RAN "sudo -n kill -9 $PID" && echo "   killed"
sleep 1; show t+1s true
sleep 7; show t+8s

echo "== 3. stop the RAN agent (network/agent failure)"
ssh -o BatchMode=yes $RAN "docker stop prisma-5g-agent >/dev/null" && echo "   agent stopped"
sleep 7; show agent-down
curl -s $B/api/ues | J "[print('   ues',x['imsi'],x['status'],x['ipv4_addr'],x.get('sync_status')) for x in d['data'] if str(x['imsi']) in ('$A','$C')]"
echo "   active_sessions.json untouched?"; docker exec prisma-5g-core cat /app/config/active_sessions.json 2>/dev/null | head -c 400; echo

echo "== 4. restart agent (container restart kills agent-spawned UEs)"
ssh -o BatchMode=yes $RAN "docker start prisma-5g-agent >/dev/null" && echo "   agent started"
sleep 8; show agent-back true

echo "== 5. cleanup: fleet power-off"
curl -s -X POST $B/api/5g/fleet/power-off | J "print('  ',d)"
show final true
curl -s $B/api/5g/monitoring | J "[print('   smf',s['imsi'],s['ipv4'],s['pdu_state'],s['sync_status']) for s in d['active_pdu_sessions']]"
