"""Unit tests for 5G Industry Verticals and Device Generators (Standard Unittest)."""

import unittest
from src.verticals import (
    VERTICAL_CATALOG,
    get_vertical,
    list_verticals,
    calculate_luhn_check_digit,
    generate_imei,
    generate_imeisv,
    generate_k,
    generate_opc,
    generate_device_credentials,
)
from src.models import (
    SliceConfig,
    QoSConfig,
    SecurityConfig,
    OrchestratedEndpoint,
)


class TestVerticals(unittest.TestCase):
    def test_vertical_catalog_completeness(self):
        """Verify that all 5 key industry verticals are defined with required attributes."""
        expected_verticals = [
            "smart_camera",
            "industry_plc",
            "connected_ambulance",
            "smart_meter",
            "executive_user",
        ]
        self.assertGreaterEqual(len(VERTICAL_CATALOG), 5)
        for v_id in expected_verticals:
            self.assertIn(v_id, VERTICAL_CATALOG)
            profile = get_vertical(v_id)
            self.assertIsNotNone(profile)
            self.assertEqual(len(profile.tac_prefix), 8)
            self.assertTrue(profile.apn)
            self.assertGreaterEqual(profile.sst, 1)
            self.assertGreater(profile.ambr_dl_mbps, 0)
            self.assertGreater(profile.ambr_ul_mbps, 0)
            self.assertTrue(profile.prisma_group)
            self.assertTrue(profile.traffic_profile)

    def test_luhn_checksum(self):
        """Test standard Luhn checksum calculation for IMEI validation."""
        self.assertEqual(calculate_luhn_check_digit("35693803564380"), "9")
        self.assertEqual(calculate_luhn_check_digit("86329404123456"), "3")

    def test_imei_and_imeisv_generation(self):
        """Test generating 15-digit IMEI and 16-digit IMEISV from TAC."""
        tac = "35412809"
        imei = generate_imei(tac)
        self.assertEqual(len(imei), 15)
        self.assertTrue(imei.startswith(tac))
        self.assertTrue(imei.isdigit())

        # Validate Luhn check digit
        body = imei[:14]
        check = calculate_luhn_check_digit(body)
        self.assertEqual(imei[14], check)

        imeisv = generate_imeisv(tac, software_version="02")
        self.assertEqual(len(imeisv), 16)
        self.assertTrue(imeisv.startswith(tac))
        self.assertTrue(imeisv.endswith("02"))

    def test_crypto_key_generation(self):
        """Test 128-bit hex key generation."""
        k = generate_k()
        opc = generate_opc()
        self.assertEqual(len(k), 32)
        self.assertEqual(len(opc), 32)
        # Verify hex format
        int(k, 16)
        int(opc, 16)

    def test_generate_device_credentials(self):
        """Test full credential bundle generation for a vertical."""
        creds = generate_device_credentials("smart_camera", custom_imsi="999700000000101")
        self.assertEqual(creds["imsi"], "999700000000101")
        self.assertEqual(len(creds["imei"]), 15)
        self.assertEqual(len(creds["k"]), 32)
        self.assertEqual(len(creds["opc"]), 32)
        self.assertEqual(creds["apn"], "video.5g")
        self.assertEqual(creds["slice"]["sst"], 1)
        self.assertEqual(creds["qos"]["5qi"], 4)
        self.assertEqual(creds["prisma_group"], "Surveillance-Cameras")

    def test_orchestrated_endpoint_model(self):
        """Test OrchestratedEndpoint model serialization and mongo converters."""
        sec = SecurityConfig(k="465B5CE8B199B49FAA5F0A2EE238A6BC", op="E8ED289DEBA952E4283B54E88E6183CA")
        slice_cfg = SliceConfig(sst=1, sd="000001")
        qos_cfg = QoSConfig(five_qi=4, ambr_dl_mbps=100, ambr_ul_mbps=50)

        endpoint = OrchestratedEndpoint(
            imsi="999700000000101",
            imei="354128091234567",
            apn="video.5g",
            vertical_id="smart_camera",
            device_name="Axis 4K Camera #1",
            vendor="Axis Communications",
            device_model="AXIS Q3538-LVE",
            icon="bi-camera-video",
            security=sec,
            slice=slice_cfg,
            qos=qos_cfg,
            state="pending",
        )

        d = endpoint.to_dict()
        self.assertEqual(d["imsi"], "999700000000101")
        self.assertNotIn("k", d)  # Secret key not exposed in public dict
        self.assertEqual(d["qos"]["5qi"], 4)
        self.assertEqual(d["slice"]["sst"], 1)

        mongo_sec = sec.to_mongo_security()
        self.assertEqual(mongo_sec["k"], "465B5CE8B199B49FAA5F0A2EE238A6BC")
        self.assertEqual(mongo_sec["opc"], "E8ED289DEBA952E4283B54E88E6183CA")

        mongo_qos = qos_cfg.to_mongo_session_qos("video.5g")
        self.assertEqual(mongo_qos["name"], "video.5g")
        self.assertEqual(mongo_qos["qos"]["index"], 4)
        self.assertEqual(mongo_qos["ambr"]["downlink"]["value"], 100)


if __name__ == "__main__":
    unittest.main()
