"""Unit tests for 5G Live Traffic Generator and Fleet Lifecycle Management."""

import unittest
from fastapi.testclient import TestClient
import app as app_module
from app import app
from src.ueransim import UERANSIMClient


class TestTrafficAndFleet(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.ran = UERANSIMClient(mock_mode=True)
        # No RAN agent in unit tests: the real client would (correctly) report failure.
        self._orig_mock = app_module._ueransim_client.mock_mode
        app_module._ueransim_client.mock_mode = True

    def tearDown(self):
        app_module._ueransim_client.mock_mode = self._orig_mock

    def test_mock_traffic_allowed(self):
        res = self.ran.exec_ue_traffic("999700000000101", traffic_type="allowed")
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("http_code"), 200)
        self.assertEqual(res.get("security_verdict"), "Allowed (Clean Traffic)")

    def test_mock_traffic_ping(self):
        res = self.ran.exec_ue_traffic("999700000000101", traffic_type="ping")
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("traffic_type"), "ping")
        self.assertEqual(res.get("packet_loss"), "0%")

    def test_mock_traffic_threat_blocked(self):
        res = self.ran.exec_ue_traffic("999700000000101", traffic_type="threat_blocked")
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("status"), "BLOCKED_BY_PRISMA_SASE")
        self.assertIn("Threat Blocked", res.get("security_verdict", ""))

    def test_api_ue_traffic(self):
        resp = self.client.post(
            "/api/5g/ue/traffic",
            json={"imsi": "999700000000101", "traffic_type": "allowed"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))

    def test_api_fleet_power_endpoints(self):
        clean_resp = self.client.post("/api/5g/fleet/clean-tuns")
        self.assertEqual(clean_resp.status_code, 200)

        power_off_resp = self.client.post("/api/5g/fleet/power-off")
        self.assertEqual(power_off_resp.status_code, 200)
        self.assertTrue(power_off_resp.json().get("success"))


if __name__ == "__main__":
    unittest.main()
