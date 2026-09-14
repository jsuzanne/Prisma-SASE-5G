import unittest
from fastapi.testclient import TestClient

from app import app
from src.config import Config, export_demo_pack
from src.client import Prisma5GClient

client = TestClient(app)


class TestBulkProvisioning(unittest.TestCase):
    """Test suite for 1-Click SCM Bulk Provisioning and Fleet Synchronization."""

    def setUp(self):
        # Ensure testing in standalone mode to avoid live SCM API calls in CI
        client.post("/api/mode", json={"standalone_mode": True})

    def tearDown(self):
        # Reset to live mode default
        client.post("/api/mode", json={"standalone_mode": False})

    def test_client_bulk_provision_pipeline(self):
        cfg = Config(standalone_mode=True, tsg_id="2909477548")
        prisma_client = Prisma5GClient(cfg)

        sample_pack = {
            "pack_version": "1.0",
            "scenario_name": "Test Bulk Fleet",
            "tenant_info": {"tsg_id": "2909477548", "default_apn": "sasetest"},
            "sim_inventory": [
                {"imsi": "208950000000001", "imei": "860123000000001", "apn": "sasetest", "groups": ["IoT-Robotics"]},
                {"imsi": "208950000000002", "imei": "860123000000002", "apn": "sasetest", "groups": ["IoT-Robotics", "Permissive"]},
            ],
            "active_sessions": {
                "208950000000001": {"ipv4_addr": "10.56.0.194", "status": "Active"},
                "208950000000002": {"ipv4_addr": "10.56.0.195", "status": "Active"},
            },
            "user_groups": [
                {"name": "IoT-Robotics", "group_name": "IoT-Robotics", "identity_id": []}
            ]
        }

        result = prisma_client.bulk_provision_fleet(sample_pack, attach_sessions=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["sims_provisioned_count"], 2)
        self.assertGreaterEqual(result["groups_configured_count"], 1)
        self.assertEqual(result["sessions_attached_count"], 2)

    def test_api_bulk_provision_endpoint(self):
        # 1. Trigger bulk provision without body (pushes active fleet snapshot)
        resp = client.post("/api/demo/bulk-provision", json={})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("data", data)
        self.assertIn("sims_provisioned_count", data["data"])

    def test_api_import_with_push_to_scm(self):
        sample_pack = {
            "pack_version": "1.0",
            "scenario_name": "Test Import Push",
            "tenant_info": {"tsg_id": "2909477548", "default_apn": "sasetest"},
            "sim_inventory": [
                {"imsi": "208959999999991", "imei": "860123999999991", "apn": "sasetest", "groups": ["Retail-Kiosks"]}
            ],
            "active_sessions": {
                "208959999999991": {"ipv4_addr": "10.56.0.199", "status": "Active"}
            }
        }

        resp = client.post("/api/demo/import", json={"pack": sample_pack, "push_to_scm": True})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data.get("scm_provisioning"))
        self.assertTrue(data["scm_provisioning"]["success"])


if __name__ == "__main__":
    unittest.main()
