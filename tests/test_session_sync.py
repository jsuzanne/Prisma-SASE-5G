"""Unit tests for SessionSync (phase 3): confirmed transitions -> SCM register/deregister + cache prune."""

import unittest
from dataclasses import dataclass
from typing import Optional

from src import session_sync as ss
from src.session_sync import SessionSync

A, B = "999703875813789", "999701249550336"


@dataclass
class Sess:
    imsi: str
    imei: str
    apn: str
    ip_type: str = "IPv4"
    ipv4_addr: Optional[str] = None


class FakeClient:
    def __init__(self):
        self.calls = []
        self.fail = False

    def register_ue_session(self, s):
        if self.fail:
            raise RuntimeError("SCM 503")
        self.calls.append(("register", s.imsi, s.ipv4_addr))
        return {"status_code": 202}

    def deregister_ue_session(self, s):
        if self.fail:
            raise RuntimeError("SCM 503")
        self.calls.append(("deregister", s.imsi, s.ipv4_addr))
        return {"status_code": 202}


def sim(status, ip=None, scm="registered", core="provisioned"):
    return {"status": status, "live_ip": ip if status == "active" else None, "interface": "uesimtun0" if ip else None,
            "scm": {"state": scm, "apn": "internet", "imei": "354128090000001"}, "core": {"state": core}}


def snap(sims, agent_ok=True):
    return {"sources": {"agent": {"ok": agent_ok}}, "sims": sims}


class TestSessionSync(unittest.TestCase):
    def setUp(self):
        ss.CONFIRM_S = 0.0  # cycles-only confirmation in tests
        self.store, self.meta, self.client = {}, {}, FakeClient()
        self.sync = SessionSync(
            get_client=lambda: self.client,
            load_sessions=lambda: {k: dict(v) for k, v in self.store.items()},
            save_sessions=lambda d: (self.store.clear(), self.store.update(d)),
            update_meta=lambda i, d: self.meta.setdefault(i, {}).update(d),
            load_meta=lambda: self.meta,
            session_cls=Sess,
            enabled=True,
        )

    def test_up_registers_once(self):
        self.sync.on_cycle(snap({A: sim("active", "10.45.0.9")}))
        self.sync.on_cycle(snap({A: sim("active", "10.45.0.9")}))
        self.assertEqual(self.client.calls, [("register", A, "10.45.0.9")])
        self.assertEqual(self.store[A]["ipv4_addr"], "10.45.0.9")
        self.assertTrue(self.store[A]["scm_registered"])

    def test_ip_change_deregisters_old_then_registers_new(self):
        self.sync.on_cycle(snap({A: sim("active", "10.45.0.9")}))
        self.sync.on_cycle(snap({A: sim("active", "10.45.0.12")}))
        self.assertEqual(self.client.calls[1:], [("deregister", A, "10.45.0.9"), ("register", A, "10.45.0.12")])

    def test_down_needs_two_cycles_then_deregisters_and_prunes(self):
        self.sync.on_cycle(snap({A: sim("active", "10.45.0.9")}))
        self.sync.on_cycle(snap({A: sim("offline")}))
        self.assertIn(A, self.store)  # 1 cycle: pending only
        self.sync.on_cycle(snap({A: sim("offline")}))
        self.assertNotIn(A, self.store)
        self.assertEqual(self.client.calls[-1], ("deregister", A, "10.45.0.9"))
        self.assertEqual(self.meta[A], {"last_ip": None, "status": "Inactive"})

    def test_agent_down_never_prunes(self):
        self.sync.on_cycle(snap({A: sim("active", "10.45.0.9")}))
        for _ in range(5):
            self.sync.on_cycle(snap({A: sim("unknown")}, agent_ok=False))
        self.assertIn(A, self.store)
        self.assertEqual(len(self.client.calls), 1)

    def test_unknown_or_starting_holds(self):
        self.sync.on_cycle(snap({A: sim("active", "10.45.0.9")}))
        for st in ("offline", "unknown", "offline", "starting", "offline"):
            self.sync.on_cycle(snap({A: sim(st)}))
        self.assertIn(A, self.store)  # never 2 consecutive confirmed-down cycles

    def test_checking_verdict_counts_toward_down(self):
        self.sync.on_cycle(snap({A: sim("active", "10.45.0.9")}))
        checking = dict(sim("unknown"), reason="checking: no nr-ue process but core still shows AMF registered")
        self.sync.on_cycle(snap({A: checking}))
        self.sync.on_cycle(snap({A: sim("offline")}))
        self.assertNotIn(A, self.store)
        # a 'checking' blip that recovers to active cancels the pending down
        self.sync.on_cycle(snap({B: sim("active", "10.45.0.5")}))
        self.sync.on_cycle(snap({B: dict(sim("unknown"), reason="checking: x")}))
        self.sync.on_cycle(snap({B: sim("active", "10.45.0.5")}))
        self.sync.on_cycle(snap({B: sim("offline")}))
        self.assertIn(B, self.store)

    def test_ip_reused_by_other_sim_skips_scm_deregister(self):
        self.store[A] = {"ipv4_addr": "10.45.0.1", "scm_registered": True}
        s = snap({A: sim("offline"), B: sim("active", "10.45.0.1")})
        self.sync.on_cycle(s)
        self.sync.on_cycle(s)
        self.assertNotIn(A, self.store)
        self.assertNotIn(("deregister", A, "10.45.0.1"), self.client.calls)
        self.assertIn(("register", B, "10.45.0.1"), self.client.calls)

    def test_legacy_unknown_key_pruned_without_scm_call(self):
        self.store["356938035643800"] = {"ipv4_addr": "10.45.0.1"}
        self.sync.on_cycle(snap({}))
        self.sync.on_cycle(snap({}))
        self.assertEqual(self.store, {})
        self.assertEqual(self.client.calls, [])

    def test_scm_failure_on_deregister_keeps_entry_for_retry(self):
        self.sync.on_cycle(snap({A: sim("active", "10.45.0.9")}))
        self.client.fail = True
        self.sync.on_cycle(snap({A: sim("offline")}))
        self.sync.on_cycle(snap({A: sim("offline")}))
        self.assertTrue(self.store[A]["scm_deregister_pending"])
        self.client.fail = False
        self.sync._retry_at.clear()
        self.sync.on_cycle(snap({A: sim("offline")}))
        self.sync.on_cycle(snap({A: sim("offline")}))
        self.assertNotIn(A, self.store)

    def test_not_in_scm_is_local_only(self):
        self.sync.on_cycle(snap({A: sim("active", "10.45.0.9", scm="absent")}))
        self.assertEqual(self.client.calls, [])
        self.assertFalse(self.store[A]["scm_registered"])

    def test_explicit_register_is_idempotent(self):
        r1 = self.sync.register(A, "10.45.0.9", sim=sim("active", "10.45.0.9"))
        r2 = self.sync.register(A, "10.45.0.9")
        self.assertTrue(r1["ok"])
        self.assertIn("skipped", r2)
        self.assertEqual(len(self.client.calls), 1)


if __name__ == "__main__":
    unittest.main()
