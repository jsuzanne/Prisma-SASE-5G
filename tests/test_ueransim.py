"""Unit tests for UERANSIM UE Manager and Process Supervisor."""

import unittest
from src.models import (
    OrchestratedEndpoint,
    SecurityConfig,
    SliceConfig,
    QoSConfig,
)
from src.ueransim import UERANSIMClient


class TestUERANSIM(unittest.TestCase):
    def setUp(self):
        self.client = UERANSIMClient(mock_mode=True)
        self.sec = SecurityConfig(
            k="465B5CE8B199B49FAA5F0A2EE238A6BC",
            op="E8ED289DEBA952E4283B54E88E6183CA",
            op_type="OPC",
            amf="8000",
            sqn=0,
        )
        self.slice_cfg = SliceConfig(sst=1, sd="000001")
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

    def test_generate_ue_yaml_content(self):
        """Verify generated UERANSIM YAML structure and field mappings."""
        yaml_out = self.client.generate_ue_yaml(self.endpoint)
        self.assertIn("supi: 'imsi-999700000000101'", yaml_out)
        self.assertIn("key: '465B5CE8B199B49FAA5F0A2EE238A6BC'", yaml_out)
        self.assertIn("op: 'E8ED289DEBA952E4283B54E88E6183CA'", yaml_out)
        self.assertIn("opType: 'OPC'", yaml_out)
        self.assertIn("amf: '8000'", yaml_out)
        self.assertIn("imei: '354128091234567'", yaml_out)
        self.assertIn("apn: 'video.5g'", yaml_out)
        self.assertIn("sst: 1", yaml_out)
        self.assertIn("sd: 000001", yaml_out)
        self.assertIn("10.10.10.2", yaml_out)

    def test_start_and_stop_mock_ue(self):
        """Test starting, querying status, and stopping a UE in mock mode."""
        res = self.client.start_ue(self.endpoint)
        self.assertEqual(res["imsi"], "999700000000101")
        self.assertEqual(res["status"], "running")

        status = self.client.get_ue_status("999700000000101")
        self.assertTrue(status["running"])
        self.assertEqual(status["pdu_status"], "PS-ACTIVE")

        self.assertTrue(self.client.stop_ue("999700000000101"))
        status_after = self.client.get_ue_status("999700000000101")
        self.assertFalse(status_after["running"])


if __name__ == "__main__":
    unittest.main()
