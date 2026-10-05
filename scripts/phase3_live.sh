#!/usr/bin/env bash
# Phase 3 live acceptance — run ON the core VM: bash phase3_live.sh [IMSI]
B=http://127.0.0.1:8080
I=${1:-999703875813789}
RAN=jsuzanne@10.10.10.2
J() { python3 -c "import json,sys;d=json.load(sys.stdin);$1"; }
cache() { curl -s $B/api/state/sessions | J "e=d['sessions'].get('$I');print('  cache:',{k:e.get(k) for k in ('ipv4_addr','interface','scm_registered','scm_deregister_pending')} if e else None)"; }
st() { curl -s "$B/api/state" | J "s=d['sims'].get('$I',{});print('  state:',s.get('status'),s.get('live_ip'),'|',(s.get('reason') or '')[:90])"; }

echo "== 1. Power On"
curl -s -X POST $B/api/5g/ue/attach/$I | J "print('  ',d['success'],d.get('interface'),d.get('allocated_ip'),'scm_registered=',d.get('scm_registered'),d.get('scm_response',{}).get('skipped',''))"
st; cache

echo "== 2. agent down 8s -> cache must be KEPT"
ssh -o BatchMode=yes $RAN "docker pause prisma-5g-agent >/dev/null" && echo "   agent paused (UE keeps running)"
sleep 8; st; cache
ssh -o BatchMode=yes $RAN "docker unpause prisma-5g-agent >/dev/null" && echo "   agent unpaused"
sleep 4; st; cache

echo "== 3. kill -9 out-of-band -> offline + SCM deregister + cache pruned within 6s"
PID=$(curl -s "$B/api/state?fresh=true" | J "print(d['sims']['$I']['radio']['pid'])")
T0=$(date +%s.%N)
ssh -o BatchMode=yes $RAN "sudo -n kill -9 $PID" && echo "   killed pid $PID"
for n in $(seq 1 12); do
  sleep 1
  OUT=$(curl -s $B/api/state/sessions | J "print('gone' if '$I' not in d['sessions'] else 'present')")
  if [ "$OUT" = gone ]; then printf "   cache pruned after %.1fs\n" "$(echo "$(date +%s.%N) - $T0" | bc)"; break; fi
done
st; cache

echo "== 4. Power On again then Power Off (explicit path)"
curl -s -X POST $B/api/5g/ue/attach/$I | J "print('  on:',d['success'],d.get('allocated_ip'),'scm=',d.get('scm_registered'))"
cache
curl -s -X POST $B/api/5g/ue/detach/$I | J "print('  off:',d['success'],d.get('released_ip'),'scm=',d.get('scm_deregistered'),d.get('message'))"
st; cache

echo "== 5. session events"
curl -s "$B/api/state/events?imsi=$I&limit=40" | J "
[print('  ',e['ts'][11:19],e['event'],e.get('frm','') and (e['frm']+'->'+e['to']),e.get('ip') or '',e.get('reason','') if e['event'].startswith('session') else (e.get('reason') or '')[:60],'scm_ok=%s'%e.get('scm_ok') if 'scm_ok' in e else '') for e in d['events'] if e['event']!='state.ue']"
