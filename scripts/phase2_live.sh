#!/usr/bin/env bash
# Phase 2 live acceptance test — run ON the core VM: bash phase2_live.sh [IMSI]
B=http://127.0.0.1:8080
I=${1:-999703875813789}
J() { python3 -c "import json,sys;d=json.load(sys.stdin);$1"; }
sim() { curl -s "$B/api/state?fresh=true" | J "s=d['sims'].get('$I',{});print('  state:',s.get('status'),'ip=',s.get('live_ip'),s.get('interface'),'|',s.get('reason'))"; }

echo "== 1. baseline"; sim
echo "== 2. attach (Power On)"
time curl -s -X POST $B/api/5g/ue/attach/$I | J "d.pop('initial_logs',None);print(json.dumps(d,indent=1)[:1200])"
sim
echo "== 3. /api/ues row"
curl -s $B/api/ues | J "r=[x for x in d['data'] if str(x['imsi'])=='$I'][0];print('  fallback=',d.get('fallback'),{k:r.get(k) for k in ('status','ipv4_addr','last_ip','interface','sync_status')})"
echo "== 4. ping through own TUN"
curl -s -X POST $B/api/5g/ping/$I | J "d.pop('output');print(' ',d)"
echo "== 5. monitoring"
curl -s $B/api/5g/monitoring | J "print('  pdu=',d['pdu_count'],'verified=',d['verified_session_count'],'amf_registered=',d['attached_ues_count']);[print('  ',s['imsi'],s['ipv4'],s['interface'],s['pdu_state'],s['sync_status']) for s in d['active_pdu_sessions']]"
echo "== 6. detach (Power Off)"
time curl -s -X POST $B/api/5g/ue/detach/$I | J "print(json.dumps(d,indent=1)[:1200])"
sim
curl -s $B/api/ues | J "r=[x for x in d['data'] if str(x['imsi'])=='$I'][0];print('  ues row:',{k:r.get(k) for k in ('status','ipv4_addr','last_ip','sync_status')})"
echo "== 7. events"
curl -s "$B/api/state/events?imsi=$I&limit=8" | J "[print('  ',e['ts'][11:19],e['event'],e.get('frm',''),'->',e.get('to',''),e.get('reason','')[:90]) for e in d['events']]"
