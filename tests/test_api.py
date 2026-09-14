"""Test suite for FastAPI endpoints in app.py."""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app import app
from src.models import TenantUEMapping, UserGroup

client = TestClient(app)


class TestAppEndpoints(unittest.TestCase):
    """Test FastAPI application endpoints with mocked backend clients."""

    def test_status_endpoint(self):
        response = client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("default_apn", data)

    def test_config_endpoint(self):
        response = client.get("/api/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("client_id", data)
        self.assertIn("tsg_id", data)
        self.assertIn("has_secret", data)

    @patch("app.Prisma5GClient.list_tenants")
    def test_tenants_endpoint(self, mock_tenants):
        mock_tenants.return_value = [
            {"id": "1965438697", "display_name": "SP-5G-POC2-Transatel"},
            {"id": "1291887562", "display_name": "Transatel demo", "parent_id": "1965438697"},
        ]
        response = client.get("/api/tenants")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 2)

    @patch("app.Prisma5GClient.list_tenant_ues")
    def test_ues_endpoint(self, mock_ues):
        mock_ues.return_value = {
            "totalItems": 1,
            "models": [
                TenantUEMapping(
                    identity_id="uuid-1",
                    imsi="208950123456789",
                    imei="860123123456789",
                    apn="sasetest",
                    tsg_id="1291887562",
                    tenant_name="Transatel demo",
                )
            ],
            "data": [],
        }
        response = client.get("/api/ues")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["apn"], "sasetest")
        self.assertIn("ipv4_addr", data["data"][0])
        self.assertIn("status", data["data"][0])
        self.assertIn("region", data["data"][0])
        self.assertIn("tenant_status", data["data"][0])

    @patch("app.Prisma5GClient.create_tenant_ue")
    def test_create_ue_endpoint(self, mock_create):
        mock_create.return_value = {
            "data": {
                "id": "new-sim-id-99",
                "imsi": "208950999999999",
                "imei": "860123999999999",
                "apn": "sasetest",
            }
        }
        payload = {
            "imsi": "208950999999999",
            "imei": "860123999999999",
            "apn": "sasetest",
            "tsg_id": "1291887562",
        }
        response = client.post("/api/ues", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["identity_id"], "new-sim-id-99")

    def test_create_ue_invalid_imei_length(self):
        # 14-digit IMEI should be rejected with HTTP 400
        payload = {
            "imsi": "208950999999999",
            "imei": "86012395225221",  # 14 digits
            "apn": "sasetest",
        }
        response = client.post("/api/ues", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("15 digits", response.json()["detail"])

    @patch("app.Prisma5GClient.delete_tenant_ue")
    def test_delete_ue_endpoint(self, mock_del):
        mock_del.return_value = {"status": "deleted"}
        response = client.delete("/api/ues/uuid-to-delete")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @patch("app.Prisma5GClient.register_ue_session")
    def test_register_session_endpoint(self, mock_sess):
        mock_sess.return_value = {"status_code": 202, "data": {"status": "accepted"}}
        payload = {
            "imsi": "208950999999999",
            "imei": "860123999999999",
            "apn": "sasetest",
            "ip_type": "IPv4",
            "ipv4_addr": "10.56.0.195",
        }
        response = client.post("/api/sessions/register", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status_code"], 202)

    @patch("app.Prisma5GClient.update_tenant_ue")
    @patch("app.Prisma5GClient.assign_ue_to_group")
    def test_update_ue_endpoint(self, mock_assign, mock_update):
        mock_update.return_value = {"status": "success"}
        mock_assign.return_value = {"status": "success", "identity_id": "uuid-1", "target_group_id": "grp-1"}
        payload = {
            "imsi": "901370001420683",
            "imei": "000000000000000",
            "apn": "sase",
            "group_id": "grp-1",
            "tsg_id": "1291887562",
        }
        response = client.put("/api/ues/uuid-1", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["identity_id"], "uuid-1")

    @patch("app.Prisma5GClient.assign_ue_to_group")
    def test_assign_ue_group_endpoint(self, mock_assign):
        mock_assign.return_value = {"status": "success", "identity_id": "uuid-1", "target_group_id": "grp-1"}
        payload = {"group_id": "grp-1", "tsg_id": "1291887562"}
        response = client.put("/api/ues/uuid-1/group", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @patch("app.Prisma5GClient.update_user_group")
    @patch("app.Prisma5GClient.get_user_group")
    @patch("app.Prisma5GClient.list_user_groups")
    def test_set_ue_groups_endpoint(self, mock_list_grps, mock_get_grp, mock_upd_grp):
        from src.models import UserGroup
        mock_list_grps.return_value = {
            "models": [
                UserGroup(group_id="grp-1", name="Restrictive", identity_ids=["uuid-1"]),
                UserGroup(group_id="grp-2", name="IT-Engineering", identity_ids=[]),
            ]
        }
        mock_get_grp.side_effect = [
            {"data": [{"group_name": "Restrictive", "identity_id": ["uuid-1"]}]},
            {"data": [{"group_name": "IT-Engineering", "identity_id": []}]},
        ]
        mock_upd_grp.return_value = {"status": "success"}

        payload = {"group_ids": ["grp-2"], "tsg_id": "1291887562"}
        response = client.put("/api/ues/uuid-1/groups", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["changes"]), 2)  # removed from grp-1, added to grp-2

    @patch("app.Prisma5GClient.create_user_group")
    def test_create_group_endpoint(self, mock_create_grp):
        mock_create_grp.return_value = {"data": {"id": "new-grp-id", "group_name": "VIP-Sensors"}}
        payload = {
            "group_name": "VIP-Sensors",
            "tsg_id": "1291887562",
            "identity_ids": ["uuid-1"],
        }
        response = client.post("/api/groups", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @patch("app.Prisma5GClient.get_user_group")
    def test_get_group_endpoint(self, mock_get_grp):
        mock_get_grp.return_value = {
            "data": [{"group_name": "Restrictive", "identity_id": ["uuid-1", "uuid-2"], "tsg_id": "1291887562"}]
        }
        response = client.get("/api/groups/6c73c05b-9977-4bed-a61c-30edc47a49f8")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @patch("app.Prisma5GClient.update_user_group")
    def test_update_group_endpoint(self, mock_upd_grp):
        mock_upd_grp.return_value = {"status": "success"}
        payload = {
            "group_name": "Restrictive-Updated",
            "identity_ids": ["uuid-1"],
        }
        response = client.put("/api/groups/6c73c05b-9977-4bed-a61c-30edc47a49f8", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @patch("app.Prisma5GClient.delete_user_group")
    @patch("app.Prisma5GClient.get_user_group")
    def test_delete_group_endpoint(self, mock_get_grp, mock_del_grp):
        mock_get_grp.return_value = {"data": [{"group_name": "CustomGroup", "identity_id": []}]}
        mock_del_grp.return_value = {"status": "success"}
        response = client.delete("/api/groups/custom-grp-id")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @patch("app.Prisma5GClient.delete_user_group")
    def test_delete_any_group_endpoint(self, mock_del_grp):
        mock_del_grp.return_value = {"status": "success"}
        # Permissive or Restrictive can now be deleted
        response = client.delete("/api/groups/6c73c05b-9977-4bed-a61c-30edc47a49f8")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_serve_index_html(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Prisma SASE 5G", response.text)
        self.assertIn("favicon.svg", response.text)

    def test_favicon_endpoint(self):
        response = client.get("/favicon.ico")
        self.assertEqual(response.status_code, 200)
        svg_resp = client.get("/static/favicon.svg")
        self.assertEqual(svg_resp.status_code, 200)
        self.assertIn("svg", svg_resp.headers.get("content-type", ""))

    @patch("app.Prisma5GClient.get_monitoring_summary")
    def test_metrics_summary_endpoint(self, mock_summary):
        mock_summary.return_value = {
            "total_5g_tenants": 2,
            "total_bandwidth_mbps": 100,
            "total_configured_users": 200,
            "interconnects_count": 1,
            "interconnects_up": 1,
            "interconnects_down": 0,
            "compute_region": "europe-west9",
            "interconnect_items": [],
        }
        response = client.get("/api/metrics/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("total_5g_tenants", data["data"])
        self.assertIn("total_bandwidth_mbps", data["data"])
        self.assertIn("interconnects_count", data["data"])

    def test_metrics_throughput_endpoint(self):
        response = client.get("/api/metrics/throughput?time_range=24h&region=europe-west9")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["region"], "europe-west9")
        self.assertIn("active_sessions_count", data)
        self.assertTrue(len(data["points"]) > 0)
        self.assertIn("ingress_kbps", data["points"][0])
        self.assertIn("egress_kbps", data["points"][0])
        self.assertIn("sessions", data["points"][0])

    def test_version_endpoint(self):
        response = client.get("/api/version")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("version", data)
        self.assertIn("commit", data)
        self.assertIn("base_version", data)

    def test_changelog_endpoint(self):
        response = client.get("/api/changelog")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("content", data)
        self.assertIn("# Changelog", data["content"])

    def test_cidr_info_endpoint(self):
        response = client.get("/api/cidr/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("configured_cidrs", data)
        self.assertIn("next_available_ip", data)
        self.assertTrue(len(data["allocatable_ips"]) > 0)
        self.assertTrue(data["total_allocatable"] > 0)

    def test_cidr_validate_endpoint(self):
        # Valid IP in default 10.56.0.192/27
        resp_valid = client.get("/api/cidr/validate?ip=10.56.0.195")
        self.assertEqual(resp_valid.status_code, 200)
        self.assertTrue(resp_valid.json()["is_valid"])

        # Out-of-range IP (e.g. 10.58.0.195)
        resp_invalid = client.get("/api/cidr/validate?ip=10.58.0.195")
        self.assertEqual(resp_invalid.status_code, 200)

    @patch("app.Prisma5GClient.list_tenant_ues")
    def test_ues_endpoint_scm_503_fallback(self, mock_ues):
        # Simulate SCM 503 upstream failure
        mock_ues.side_effect = Exception("503 Server Error: no healthy upstream")
        response = client.get("/api/ues")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["fallback"])
        self.assertEqual(data["source"], "offline_cache")
        self.assertTrue(len(data["data"]) > 0)

    @patch("app.Prisma5GClient.list_user_groups")
    def test_groups_endpoint_scm_503_fallback(self, mock_groups):
        # Simulate SCM 503 upstream failure
        mock_groups.side_effect = Exception("503 Server Error: no healthy upstream")
        response = client.get("/api/groups")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["fallback"])
        self.assertEqual(data["source"], "offline_cache")
        self.assertTrue(len(data["data"]) > 0)


if __name__ == "__main__":
    unittest.main()

