"""Unit tests for Open5GS 5G Core Manager and Real-Time Session Poller."""

import unittest
from src.models import (
    OrchestratedEndpoint,
    SecurityConfig,
    SliceConfig,
    QoSConfig,
)
from src.open5gs import Open5GSClient, PROTECTED_IMSIS


class TestOpen5GS(unittest.TestCase):
    def setUp(self):
        self.client = Open5GSClient(mock_mode=True)
        self.sec = SecurityConfig(
            k="465B5CE8B199B49FAA5F0A2EE238A6BC",
            op="E8ED289DEBA952E4283B54E88E6183CA",
            op_type="OPC",
            amf="8000",
            sqn=0,
        )
        self.slice_cfg = SliceConfig(sst=1, sd="000001", default_indicator=True)
        self.qos_cfg = QoSConfig(five_qi=4, ambr_dl_mbps=100, ambr_ul_mbps=50)
        self.endpoint = OrchestratedEndpoint(
            imsi="999700000000101",
            imei="354128091234567",
            apn="video.5g",
            vertical_id="smart_camera",
            device_name="Axis 4K Camera #1",
            vendor="Axis Communications",
            device_model="AXIS Q3538-LVE",
            icon="bi-camera-video",
            security=self.sec,
            slice=self.slice_cfg,
            qos=self.qos_cfg,
        )

    def test_build_subscriber_document_structure(self):
        """Verify Open5GS v2.8.0 MongoDB document structure."""
        doc = self.client.build_subscriber_document(self.endpoint)
        self.assertEqual(doc["imsi"], "999700000000101")
        self.assertEqual(doc["managed_by"], "stigix-orchestrator")
        self.assertEqual(doc["schema_version"], 1)
        self.assertEqual(doc["security"]["k"], "465B5CE8B199B49FAA5F0A2EE238A6BC")
        self.assertEqual(doc["security"]["opc"], "E8ED289DEBA952E4283B54E88E6183CA")
        self.assertEqual(doc["security"]["amf"], "8000")

        # Slice check
        self.assertEqual(len(doc["slice"]), 1)
        self.assertEqual(doc["slice"][0]["sst"], 1)
        self.assertEqual(doc["slice"][0]["sd"], "000001")
        self.assertEqual(doc["slice"][0]["default_indicator"], True)

        # Session QoS check
        session = doc["slice"][0]["session"][0]
        self.assertEqual(session["name"], "video.5g")
        self.assertEqual(session["qos"]["index"], 4)
        self.assertEqual(session["ambr"]["downlink"]["value"], 100)
        self.assertEqual(session["ambr"]["uplink"]["value"], 50)

    def test_mock_subscriber_crud(self):
        """Test creating, reading, listing, and deleting subscribers in mock mode."""
        self.assertTrue(self.client.create_subscriber(self.endpoint))
        sub = self.client.get_subscriber("999700000000101")
        self.assertIsNotNone(sub)
        self.assertEqual(sub["imsi"], "999700000000101")

        subs = self.client.list_subscribers(managed_only=True)
        self.assertEqual(len(subs), 1)

        self.assertTrue(self.client.delete_subscriber("999700000000101"))
        self.assertIsNone(self.client.get_subscriber("999700000000101"))

    def test_protected_imsi_safety(self):
        """Verify that baseline lab IMSIs are strictly protected against deletion."""
        for protected_imsi in PROTECTED_IMSIS:
            res = self.client.delete_subscriber(protected_imsi)
            self.assertFalse(res)

    def test_mock_pdu_session_polling(self):
        """Test polling PDU session in mock mode."""
        self.client._mock_sessions["imsi-999700000000101"] = {
            "supi": "imsi-999700000000101",
            "pdu": [
                {
                    "psi": 1,
                    "dnn": "video.5g",
                    "ipv4": "10.45.0.4",
                    "pdu_state": "active",
                    "snssai": {"sst": 1, "sd": "000001"},
                    "qos_flows": [{"qfi": 1, "5qi": 4}],
                }
            ],
        }
        res = self.client.poll_pdu_session("999700000000101", timeout_sec=2)
        self.assertIsNotNone(res)
        self.assertEqual(res["ipv4"], "10.45.0.4")
        self.assertEqual(res["dnn"], "video.5g")
        self.assertEqual(res["5qi"], 4)


if __name__ == "__main__":
    unittest.main()
