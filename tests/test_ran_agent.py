"""Unit tests for the RAN agent ground-truth logic (no UERANSIM host needed)."""

import json
import os
import tempfile
import unittest

from src.ran_agent import RanAgent, correlate, imsi_from_cmdline, parse_ip_json, parse_ue_log

IP_JSON = json.dumps([
    {"ifname": "lo", "flags": ["LOOPBACK", "UP"], "addr_info": [{"family": "inet", "local": "127.0.0.1"}]},
    {"ifname": "uesimtun0", "flags": ["POINTOPOINT", "UP", "LOWER_UP"], "operstate": "UNKNOWN",
     "addr_info": [{"family": "inet", "local": "10.45.0.3", "prefixlen": 24}]},
    {"ifname": "uesimtun1", "flags": ["POINTOPOINT", "UP"], "operstate": "UNKNOWN",
     "addr_info": [{"family": "inet", "local": "10.45.0.9", "prefixlen": 24}]},
])

LOG_ACTIVE = (
    "[nas] [info] Initial Registration is successful\n"
    "[nas] [info] PDU Session establishment is successful PSI[1]\n"
    "[app] [info] Connection setup for PDU session[1] is successful, TUN interface[uesimtun0, 10.45.0.3] is up.\n"
)
LOG_REJECT = "[nas] [error] Initial Registration failed [FIVEG_SERVICES_NOT_ALLOWED]\n"


class TestParsers(unittest.TestCase):
    def test_parse_ip_json_only_tuns(self):
        tuns = parse_ip_json(IP_JSON)
        self.assertEqual([t["interface"] for t in tuns], ["uesimtun0", "uesimtun1"])
        self.assertEqual(tuns[0]["ip"], "10.45.0.3")
        self.assertTrue(tuns[0]["up"])

    def test_parse_ip_json_garbage(self):
        self.assertEqual(parse_ip_json("not json"), [])
        self.assertEqual(parse_ip_json(""), [])

    def test_parse_log_active(self):
        r = parse_ue_log(LOG_ACTIVE)
        self.assertEqual((r["phase"], r["interface"], r["ip"]), ("pdu_active", "uesimtun0", "10.45.0.3"))

    def test_parse_log_last_tun_wins(self):
        r = parse_ue_log(LOG_ACTIVE + "TUN interface[uesimtun2, 10.45.0.7] is up.\n")
        self.assertEqual((r["interface"], r["ip"]), ("uesimtun2", "10.45.0.7"))

    def test_parse_log_rejected(self):
        r = parse_ue_log(LOG_REJECT)
        self.assertEqual(r["phase"], "rejected")
        self.assertIn("FIVEG_SERVICES_NOT_ALLOWED", r["last_error"])

    def test_parse_log_auth_mac_failure_seen_on_lab(self):
        log = ("[nas] [debug] Authentication Request received\n"
               "[nas] [error] AUTN validation MAC mismatch. expected [99D87D4F4DB9A7FD] received [902823FF1C3E6FEA]\n"
               "[nas] [error] Sending Authentication Failure with cause [MAC_FAILURE]\n"
               "[nas] [error] Authentication Reject received\n")
        r = parse_ue_log(log)
        self.assertEqual(r["phase"], "rejected")
        self.assertIn("5G-AKA authentication failed", r["last_error"])
        self.assertIn("MAC mismatch", r["last_error"])

    def test_parse_log_deregistered_after_tun(self):
        r = parse_ue_log(LOG_ACTIVE + "[nas] [info] De-registration is successful\n")
        self.assertEqual(r["phase"], "deregistered")

    def test_parse_log_empty(self):
        self.assertEqual(parse_ue_log("")["phase"], "no_log")

    def test_imsi_from_managed_cmdline(self):
        self.assertEqual(
            imsi_from_cmdline("./build/nr-ue -c /opt/UERANSIM/config/managed/ue-999700000000001.yaml"),
            "999700000000001",
        )

    def test_imsi_from_baseline_config(self):
        reader = lambda p: "supi: 'imsi-999700000000001'\nmcc: '999'\n" if p.endswith("open5gs-ue.yaml") else None
        self.assertEqual(imsi_from_cmdline("./build/nr-ue -c config/open5gs-ue.yaml", reader), "999700000000001")
        self.assertIsNone(imsi_from_cmdline("./build/nr-ue -c config/other.yaml", lambda p: None))


class TestCorrelation(unittest.TestCase):
    def setUp(self):
        self.tuns = parse_ip_json(IP_JSON)

    def test_active_requires_process_log_and_kernel(self):
        r = correlate([{"pid": 10, "imsi": "A"}], self.tuns, {"A": parse_ue_log(LOG_ACTIVE)})
        ue = r["ues"][0]
        self.assertEqual((ue["radio_state"], ue["interface"], ue["ip"]), ("active", "uesimtun0", "10.45.0.3"))
        self.assertEqual([t["interface"] for t in r["unattributed_tuns"]], ["uesimtun1"])

    def test_no_process_means_stopped_even_if_log_and_tun_exist(self):
        """Ghost case: stale log + leftover TUN but process dead → never active."""
        r = correlate([], self.tuns, {"A": parse_ue_log(LOG_ACTIVE)})
        ue = r["ues"][0]
        self.assertEqual(ue["radio_state"], "stopped")
        self.assertIsNone(ue["ip"])

    def test_tun_missing_in_kernel_means_not_active(self):
        r = correlate([{"pid": 10, "imsi": "A"}], [], {"A": parse_ue_log(LOG_ACTIVE)})
        self.assertEqual(r["ues"][0]["radio_state"], "connecting")
        self.assertIsNone(r["ues"][0]["ip"])

    def test_ip_mismatch_is_not_attributed(self):
        """Log says uesimtun0=10.45.0.3 but kernel uesimtun0 has another IP → no guess."""
        tuns = [{"interface": "uesimtun0", "ip": "10.45.0.99", "up": True}]
        r = correlate([{"pid": 10, "imsi": "A"}], tuns, {"A": parse_ue_log(LOG_ACTIVE)})
        self.assertNotEqual(r["ues"][0]["radio_state"], "active")
        self.assertEqual(len(r["unattributed_tuns"]), 1)

    def test_two_ues_get_their_own_tun(self):
        log_b = "TUN interface[uesimtun1, 10.45.0.9] is up.\n"
        r = correlate(
            [{"pid": 10, "imsi": "A"}, {"pid": 11, "imsi": "B"}],
            self.tuns,
            {"A": parse_ue_log(LOG_ACTIVE), "B": parse_ue_log(log_b)},
        )
        by = {u["imsi"]: u for u in r["ues"]}
        self.assertEqual(by["A"]["interface"], "uesimtun0")
        self.assertEqual(by["B"]["interface"], "uesimtun1")
        self.assertEqual(r["unattributed_tuns"], [])

    def test_rejected(self):
        r = correlate([{"pid": 10, "imsi": "A"}], [], {"A": parse_ue_log(LOG_REJECT)})
        self.assertEqual(r["ues"][0]["radio_state"], "failed")

    def test_tun_failure_seen_on_lab(self):
        """Core says PDU active, but UERANSIM could not create the TUN → failed, never active."""
        log = ("[nas] [info] Initial Registration is successful\n"
               "[nas] [info] PDU Session establishment is successful PSI[1]\n"
               "[app] [error] TUN configuration failure [Could not open '/etc/iproute2/rt_tables']\n")
        p = parse_ue_log(log)
        self.assertEqual(p["phase"], "tun_failed")
        self.assertIn("rt_tables", p["last_error"])
        r = correlate([{"pid": 10, "imsi": "A"}], self.tuns, {"A": p})
        self.assertEqual((r["ues"][0]["radio_state"], r["ues"][0]["ip"]), ("failed", None))

    def test_duplicate_processes_flagged(self):
        r = correlate([{"pid": 10, "imsi": "A"}, {"pid": 11, "imsi": "A"}], self.tuns, {"A": parse_ue_log(LOG_ACTIVE)})
        self.assertTrue(r["ues"][0]["duplicate_processes"])


class TestProcScan(unittest.TestCase):
    """scan_processes against a fake /proc tree: zombies and sudo wrappers excluded."""

    def _mk(self, root, pid, cmd, state="S"):
        d = os.path.join(root, str(pid))
        os.makedirs(d)
        with open(os.path.join(d, "cmdline"), "wb") as f:
            f.write(cmd.replace(" ", "\x00").encode())
        with open(os.path.join(d, "stat"), "w") as f:
            f.write(f"{pid} (nr-ue) {state} 1 1 1")

    def test_scan(self):
        with tempfile.TemporaryDirectory() as root:
            self._mk(root, 100, "./build/nr-ue -c config/managed/ue-111110000000001.yaml")
            self._mk(root, 101, "./build/nr-ue -c config/managed/ue-111110000000002.yaml", state="Z")
            self._mk(root, 102, "sudo ./build/nr-ue -c config/managed/ue-111110000000003.yaml")
            self._mk(root, 103, "./build/nr-gnb -c config/open5gs-gnb.yaml")
            self._mk(root, 104, "/usr/bin/python3 app.py")
            res = RanAgent(ueransim_dir=root, proc_root=root).scan_processes()
            self.assertEqual([(p["pid"], p["imsi"]) for p in res["ues"]], [(100, "111110000000001")])
            self.assertEqual([g["pid"] for g in res["gnbs"]], [103])


if __name__ == "__main__":
    unittest.main()
