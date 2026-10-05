"""Unit tests for the 4-pillar reconciler (pure decision function + debounce + snapshot shape)."""

import unittest

from src.reconciler import Reconciler, compute_sim_state

IMSI = "999703875813789"
ACTIVE_RADIO = {"radio_state": "active", "pid": 123, "interface": "uesimtun0", "ip": "10.45.0.9",
                "reason": "PDU session active"}


def state(**kw):
    args = dict(imsi=IMSI, agent_ok=True, agent_error=None, core_ok=True, radio=None, amf=None, smf=None,
                in_mongo=True, managed=True, scm={"imsi": IMSI}, scm_ok=True, starting_since=None, now=1000.0)
    args.update(kw)
    return compute_sim_state(**args)


class TestComputeSimState(unittest.TestCase):
    def test_agent_down_is_unknown_never_offline(self):
        d = state(agent_ok=False, agent_error="timeout", radio=ACTIVE_RADIO)
        self.assertEqual(d["status"], "unknown")
        self.assertIsNone(d["live_ip"])

    def test_active_requires_all_pillars(self):
        d = state(radio=ACTIVE_RADIO, amf={"mm_state": "registered"},
                  smf={"ipv4": "10.45.0.9", "pdu_state": "active"})
        self.assertEqual(d["status"], "active")
        self.assertEqual(d["live_ip"], "10.45.0.9")
        self.assertEqual(d["interface"], "uesimtun0")

    def test_amf_deregistered_is_inconsistent(self):
        d = state(radio=ACTIVE_RADIO, amf={"mm_state": "deregistered"},
                  smf={"ipv4": "10.45.0.9", "pdu_state": "active"})
        self.assertEqual(d["status"], "inconsistent")
        self.assertTrue(d["candidate_inconsistent"])
        self.assertIsNone(d["live_ip"])

    def test_ip_mismatch_is_inconsistent(self):
        d = state(radio=ACTIVE_RADIO, amf={"mm_state": "registered"},
                  smf={"ipv4": "10.45.0.7", "pdu_state": "active"})
        self.assertEqual(d["status"], "inconsistent")
        self.assertIn("10.45.0.7", d["reason"])

    def test_radio_active_core_down_is_unknown(self):
        d = state(radio=ACTIVE_RADIO, core_ok=False)
        self.assertEqual(d["status"], "unknown")

    def test_tun_failed_is_failed(self):
        d = state(radio={"radio_state": "failed", "last_error": "TUN configuration failure"})
        self.assertEqual(d["status"], "failed")
        self.assertIn("TUN", d["reason"])

    def test_starting_window(self):
        d = state(radio={"radio_state": "connecting", "reason": "registering"}, starting_since=990.0)
        self.assertEqual(d["status"], "starting")
        d2 = state(radio={"radio_state": "connecting", "reason": "registering"}, starting_since=900.0)
        self.assertEqual(d2["status"], "inconsistent")

    def test_ghost_core_session_without_radio(self):
        d = state(amf={"mm_state": "registered"}, smf={"ipv4": "10.45.0.8", "pdu_state": "active"})
        self.assertEqual(d["status"], "inconsistent")
        self.assertIsNone(d["live_ip"])

    def test_stopped_with_deregistered_amf_is_offline(self):
        d = state(amf={"mm_state": "deregistered"})
        self.assertEqual(d["status"], "offline")

    def test_scm_only_and_core_only(self):
        self.assertEqual(state(in_mongo=False)["status"], "scm_only")
        self.assertEqual(state(scm=None)["status"], "core_only")
        # SCM unknown -> never claim core_only
        self.assertEqual(state(scm=None, scm_ok=False)["status"], "offline")


class FakeRan:
    agent_url = "http://agent"

    def __init__(self):
        self.tele = {"ok": True, "ues": [], "gnb": {"running": True}}

    def telemetry(self, max_age_s=None):
        return self.tele


class FakeDB:
    def __init__(self, docs):
        self.subscribers = self
        self.docs = docs

    def find(self, *_a, **_k):
        return list(self.docs)


class FakeCore:
    amf_url = "amf"
    smf_url = "smf"

    def __init__(self):
        self.amf = {"items": []}
        self.smf = {"items": []}
        self.mongo_db = FakeDB([{"imsi": IMSI, "managed_by": "stigix-orchestrator"}])

    def _http_get(self, url):
        return self.amf if url.startswith("amf") else self.smf


class TestReconciler(unittest.TestCase):
    def setUp(self):
        self.ran, self.core = FakeRan(), FakeCore()
        self.rec = Reconciler(self.ran, self.core, scm_fetcher=lambda: [{"imsi": IMSI, "tenant_name": "T"}])

    def test_snapshot_offline(self):
        snap = self.rec.refresh_now(refresh_scm=True)
        sim = snap["sims"][IMSI]
        self.assertEqual(sim["status"], "offline")
        self.assertIsNone(sim["live_ip"])
        self.assertEqual(sim["scm"]["tenant_name"], "T")
        self.assertTrue(snap["sources"]["agent"]["ok"])

    def test_active_then_agent_down_goes_unknown(self):
        self.ran.tele = {"ok": True, "ues": [dict(ACTIVE_RADIO, imsi=IMSI)]}
        self.core.amf = {"items": [{"supi": f"imsi-{IMSI}", "mm_state": "registered"}]}
        self.core.smf = {"items": [{"supi": f"imsi-{IMSI}", "pdu": [{"ipv4": "10.45.0.9", "pdu_state": "active"}]}]}
        self.assertEqual(self.rec.refresh_now(refresh_scm=True)["sims"][IMSI]["status"], "active")
        self.ran.tele = {"ok": False, "error": "down", "ues": []}
        sim = self.rec.refresh_now()["sims"][IMSI]
        self.assertEqual(sim["status"], "unknown")
        self.assertIsNone(sim["live_ip"])

    def test_inconsistent_is_debounced(self):
        self.core.amf = {"items": [{"supi": f"imsi-{IMSI}", "mm_state": "registered"}]}
        self.core.smf = {"items": [{"supi": f"imsi-{IMSI}", "pdu": [{"ipv4": "10.45.0.8", "pdu_state": "active"}]}]}
        s1 = self.rec.refresh_now(refresh_scm=True)
        self.assertNotEqual(s1["sims"][IMSI]["status"], "inconsistent")
        self.assertTrue(s1["sims"][IMSI]["reason"].startswith("checking"))
        s2 = self.rec.refresh_now()
        self.assertEqual(s2["sims"][IMSI]["status"], "inconsistent")
        self.assertEqual(s2["stale_core_sessions"][0]["ip"], "10.45.0.8")

    def test_scm_error_keeps_last_good_copy(self):
        self.rec.refresh_now(refresh_scm=True)

        def boom():
            raise RuntimeError("SCM 503")
        self.rec.scm_fetcher = boom
        snap = self.rec.refresh_now(refresh_scm=True)
        self.assertEqual(snap["sims"][IMSI]["scm"]["state"], "registered")
        self.assertFalse(snap["sources"]["scm"]["ok"])
        self.assertIn("503", snap["sources"]["scm"]["error"])

    def test_listener_called_on_transition(self):
        seen = []
        self.rec.add_listener(lambda sim, before, ctx: seen.append((sim["status"], before and before["status"])))
        self.rec.refresh_now(refresh_scm=True)
        self.ran.tele = {"ok": True, "ues": [dict(ACTIVE_RADIO, imsi=IMSI)]}
        self.core.amf = {"items": [{"supi": f"imsi-{IMSI}", "mm_state": "registered"}]}
        self.core.smf = {"items": [{"supi": f"imsi-{IMSI}", "pdu": [{"ipv4": "10.45.0.9", "pdu_state": "active"}]}]}
        self.rec.refresh_now()
        self.assertEqual(seen[-1], ("active", "offline"))


if __name__ == "__main__":
    unittest.main()
