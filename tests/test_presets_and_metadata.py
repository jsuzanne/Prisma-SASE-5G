"""Tests for vertical presets, 3GPP generation, and local metadata persistence."""

import tempfile
import unittest
from pathlib import Path

from src.presets import (
    compute_luhn_checksum,
    generate_transatel_imsi,
    generate_valid_imei,
    VERTICALS_CATALOG,
    get_all_verticals,
    get_random_preset,
)
from src.config import (
    load_sim_metadata,
    save_sim_metadata,
    update_single_sim_metadata,
    delete_single_sim_metadata,
    clear_all_sim_metadata,
)
from src.models import TenantUEMapping


class TestPresetsAndMetadata(unittest.TestCase):
    def test_luhn_checksum(self):
        # Known IMEI prefix
        prefix14 = "86012300000000"
        check = compute_luhn_checksum(prefix14)
        self.assertEqual(len(check), 1)
        self.assertTrue(check.isdigit())

    def test_imsi_and_imei_generation(self):
        imsi = generate_transatel_imsi()
        self.assertEqual(len(imsi), 15)
        self.assertTrue(imsi.startswith("20895"))

        imei = generate_valid_imei()
        self.assertEqual(len(imei), 15)

    def test_verticals_catalog(self):
        verticals = get_all_verticals()
        self.assertGreaterEqual(len(verticals), 7)
        for v in verticals:
            self.assertIn("id", v)
            self.assertIn("name", v)
            self.assertIn("icon", v)
            self.assertIn("equipment_types", v)
            self.assertGreater(len(v["equipment_types"]), 0)

        preset = get_random_preset("ev_infrastructure")
        self.assertEqual(preset["vertical_id"], "ev_infrastructure")
        self.assertTrue(preset["imsi"].startswith("20895"))
        self.assertEqual(len(preset["imei"]), 15)

    def test_generate_fleet_devices(self):
        from src.presets import generate_fleet_devices

        # 1 device per all 7 verticals
        fleet_all = generate_fleet_devices(vertical_id="all")
        self.assertEqual(len(fleet_all), 7)
        for dev in fleet_all:
            self.assertTrue(dev["imsi"].startswith("20895"))
            self.assertEqual(len(dev["imei"]), 15)
            self.assertIn("vertical", dev)
            self.assertIn("device_type", dev)
            self.assertIn("session_ip", dev)

        # 5 devices for specific vertical
        fleet_ev = generate_fleet_devices(vertical_id="ev_infrastructure", count=5)
        self.assertEqual(len(fleet_ev), 5)
        for dev in fleet_ev:
            self.assertEqual(dev["vertical"], "ev_infrastructure")
            self.assertEqual(dev["suggested_group"], "Restrictive")
            self.assertTrue(dev["session_ip"].startswith("10.45.0.") or dev["session_ip"].startswith("10.56.0."))

    def test_enrich_existing_imsis(self):
        from src.presets import enrich_existing_imsis

        sample_imsis = ["901370007299137", "901370007299147", "901370007299136"]
        
        # Test distribution across all verticals
        enriched_all = enrich_existing_imsis(sample_imsis, vertical_id="all")
        self.assertEqual(len(enriched_all), 3)
        for imsi in sample_imsis:
            self.assertIn(imsi, enriched_all)
            self.assertIn("vertical", enriched_all[imsi])
            self.assertIn("device_type", enriched_all[imsi])
            self.assertIn("icon", enriched_all[imsi])
            self.assertIn("custom_label", enriched_all[imsi])

        # Test specific vertical enrichment
        enriched_retail = enrich_existing_imsis(sample_imsis, vertical_id="retail")
        for imsi in sample_imsis:
            self.assertEqual(enriched_retail[imsi]["vertical"], "retail")
            self.assertEqual(enriched_retail[imsi]["icon"], "credit-card")



    def test_metadata_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Initial load should be empty
            meta = load_sim_metadata(tmp_path)
            self.assertEqual(meta, {})

            # Update single metadata
            imsi = "208950000000001"
            update_single_sim_metadata(
                imsi,
                {
                    "vertical": "ev_infrastructure",
                    "device_type": "EVSE Fast-Charger OCPI Gateway",
                    "custom_label": "EV Fast-Charger Demo #1",
                    "icon": "zap",
                },
                target_dir=tmp_path,
            )

            loaded = load_sim_metadata(tmp_path)
            self.assertIn(imsi, loaded)
            self.assertEqual(loaded[imsi]["custom_label"], "EV Fast-Charger Demo #1")
            self.assertEqual(loaded[imsi]["device_type"], "EVSE Fast-Charger OCPI Gateway")

            # Model creation with metadata
            ue = TenantUEMapping(
                imsi=imsi,
                imei="860123000000001",
                apn="sasetest",
                custom_label=loaded[imsi]["custom_label"],
                vertical=loaded[imsi]["vertical"],
                device_type=loaded[imsi]["device_type"],
            )
            self.assertEqual(ue.custom_label, "EV Fast-Charger Demo #1")

            # Delete single metadata
            delete_single_sim_metadata(imsi, target_dir=tmp_path)
            loaded_after_del = load_sim_metadata(tmp_path)
            self.assertNotIn(imsi, loaded_after_del)

            # Clear all metadata
            update_single_sim_metadata("208950000000002", {"custom_label": "Test"}, target_dir=tmp_path)
            self.assertEqual(len(load_sim_metadata(tmp_path)), 1)
            clear_all_sim_metadata(tmp_path)
            self.assertEqual(len(load_sim_metadata(tmp_path)), 0)

    def test_group_metadata_persistence(self):
        from src.config import (
            load_group_metadata,
            save_group_metadata,
            update_single_group_metadata,
            delete_single_group_metadata,
            DEFAULT_GROUP_DESCRIPTIONS,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            self.assertIn("restrictive", DEFAULT_GROUP_DESCRIPTIONS)
            self.assertIn("permissive", DEFAULT_GROUP_DESCRIPTIONS)

            # Initially empty
            loaded = load_group_metadata(tmp_path)
            self.assertEqual(loaded, {})

            # Update single group metadata
            grp_id = "test-group-uuid"
            update_single_group_metadata(
                grp_id,
                {
                    "name": "Custom IoT Group",
                    "description": "Custom isolation policy for factory robots",
                },
                target_dir=tmp_path,
            )

            loaded = load_group_metadata(tmp_path)
            self.assertIn(grp_id, loaded)
            self.assertEqual(loaded[grp_id]["name"], "Custom IoT Group")
            self.assertEqual(loaded[grp_id]["description"], "Custom isolation policy for factory robots")

            # Delete single group metadata
            delete_single_group_metadata(grp_id, target_dir=tmp_path)
            loaded_after_del = load_group_metadata(tmp_path)
            self.assertNotIn(grp_id, loaded_after_del)


if __name__ == "__main__":
    unittest.main()

