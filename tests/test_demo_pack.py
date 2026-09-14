"""Test suite for Standalone Demo Sandbox and Demo Pack Import/Export system."""

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app import app
from src.config import (
    Config,
    export_demo_pack,
    import_demo_pack,
    get_builtin_scenario_presets,
    load_builtin_scenario,
    BUILTIN_SCENARIOS,
)
from src.client import Prisma5GClient

client = TestClient(app)


class TestDemoPackSystem(unittest.TestCase):
    """Test Demo Pack export, import, preset scenarios, and standalone mode."""

    def test_get_builtin_presets(self):
        presets = get_builtin_scenario_presets()
        self.assertEqual(len(presets), 3)
        preset_ids = [p["id"] for p in presets]
        self.assertIn("retail_supermarket", preset_ids)
        self.assertIn("smart_factory", preset_ids)
        self.assertIn("ev_infrastructure", preset_ids)

    def test_export_demo_pack_structure(self):
        pack = export_demo_pack("Unit Test Scenario")
        self.assertEqual(pack["pack_version"], "1.0")
        self.assertEqual(pack["scenario_name"], "Unit Test Scenario")
        self.assertIn("tenant_info", pack)
        self.assertIn("sim_metadata", pack)
        self.assertIn("active_sessions", pack)
        self.assertIn("group_metadata", pack)

    def test_import_demo_pack_and_load_scenario(self):
        result = load_builtin_scenario("retail_supermarket")
        self.assertTrue(result["success"])
        self.assertTrue(result["sims_count"] >= 10)

        # Verify load invalid scenario raises ValueError
        with self.assertRaises(ValueError):
            load_builtin_scenario("non_existent_preset_123")

    def test_api_mode_endpoints(self):
        # 1. Get current mode (should default to live)
        get_res = client.get("/api/mode")
        self.assertEqual(get_res.status_code, 200)
        self.assertIn("standalone_mode", get_res.json())

        # 2. Switch to standalone
        post_res = client.post("/api/mode", json={"standalone_mode": True})
        self.assertEqual(post_res.status_code, 200)
        self.assertTrue(post_res.json()["standalone_mode"])
        self.assertEqual(post_res.json()["mode"], "standalone")

        # Verify /api/status returns standalone mode
        status_res = client.get("/api/status")
        self.assertEqual(status_res.status_code, 200)
        self.assertTrue(status_res.json()["standalone_mode"])
        self.assertEqual(status_res.json()["status"], "standalone")

        # 3. Switch back to live (default)
        post_res2 = client.post("/api/mode", json={"standalone_mode": False})
        self.assertEqual(post_res2.status_code, 200)
        self.assertFalse(post_res2.json()["standalone_mode"])
        self.assertEqual(post_res2.json()["mode"], "live")

        # Verify /api/status returns live mode
        status_res2 = client.get("/api/status")
        self.assertEqual(status_res2.status_code, 200)
        self.assertFalse(status_res2.json()["standalone_mode"])

    def test_api_demo_export_endpoint(self):
        resp = client.get("/api/demo/export")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["pack_version"], "1.0")
        self.assertIn("tenant_info", data)

    def test_api_demo_presets_and_load_endpoints(self):
        # List presets
        resp = client.get("/api/demo/presets")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["presets"]), 3)

        # Load preset via API
        resp_load = client.post("/api/demo/presets/load/smart_factory")
        self.assertEqual(resp_load.status_code, 200)
        self.assertTrue(resp_load.json()["success"])

    def test_api_demo_import_endpoint(self):
        sample_pack = {
            "pack_version": "1.0",
            "scenario_name": "API Test Import Fleet",
            "sim_metadata": {
                "208959999999999": {"vertical": "retail", "device_type": "Test POS", "last_ip": "10.56.0.193"}
            },
            "active_sessions": {
                "208959999999999": {"ipv4_addr": "10.56.0.193", "status": "Active"}
            }
        }
        resp = client.post("/api/demo/import", json=sample_pack)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    def test_client_standalone_mode_simulation(self):
        cfg = Config(standalone_mode=True, tsg_id="2909477548")
        standalone_client = Prisma5GClient(cfg)

        # 1. Register Session in standalone mode
        from src.models import UESession
        sess = UESession(imsi="208950123456789", imei="860123123456789", apn="transatel.com", ipv4_addr="10.56.0.195")
        res_reg = standalone_client.register_ue_session(sess)
        self.assertEqual(res_reg["status_code"], 200)

        # 2. Deregister Session in standalone mode
        res_dereg = standalone_client.deregister_ue_session(sess)
        self.assertEqual(res_dereg["status_code"], 200)

        # 3. Create UE in standalone mode
        res_create = standalone_client.create_tenant_ue("208950123456789", "860123123456789")
        self.assertEqual(res_create["status"], "Success")


if __name__ == "__main__":
    unittest.main()
