"""Unit tests for API Debug Logger and Inspector."""

import unittest
from fastapi.testclient import TestClient

from src.debug_logger import APIDebugLogger, sanitize_headers, generate_curl_command
from app import app

client = TestClient(app)


class TestAPIDebugLogger(unittest.TestCase):
    """Test APIDebugLogger ring buffer and helpers."""

    def setUp(self):
        self.logger = APIDebugLogger(max_capacity=5)

    def test_sanitize_headers(self):
        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisToken",
            "X-Pan-Secret": "supersecretpassword123",
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        sanitized = sanitize_headers(headers)
        self.assertTrue(sanitized["Authorization"].startswith("Bearer eyJhbG..."))
        self.assertTrue(sanitized["Authorization"].endswith("oken"))
        self.assertNotIn("doNotLeakThisToken", sanitized["Authorization"])
        self.assertEqual(sanitized["Content-Type"], "application/json")
        self.assertTrue("..." in sanitized["X-Pan-Secret"])

    def test_generate_curl_command(self):
        curl = generate_curl_command(
            method="POST",
            url="https://api.sase.paloaltonetworks.com/mt/manage/5g/register/ue",
            headers={"Content-Type": "application/json", "Authorization": "Bearer token123"},
            body={"imsi": "208950123456789", "imei": "860123123456789"},
        )
        self.assertIn("curl -X POST", curl)
        self.assertIn("https://api.sase.paloaltonetworks.com/mt/manage/5g/register/ue", curl)
        self.assertIn("-H 'Content-Type: application/json'", curl)
        self.assertIn("208950123456789", curl)

    def test_record_and_circular_buffer(self):
        for i in range(10):
            self.logger.record(
                method="GET",
                url=f"https://api.example.com/item/{i}",
                path=f"/item/{i}",
                response_status=200,
                duration_ms=10.5,
            )

        # Max capacity is 5
        self.assertEqual(self.logger.count(), 5)
        logs = self.logger.get_logs(limit=10)
        self.assertEqual(len(logs), 5)
        # Newest should be item/9
        self.assertEqual(logs[0]["path"], "/item/9")

    def test_filter_and_search(self):
        self.logger.record(
            method="POST",
            url="https://api.example.com/ue",
            path="/ue",
            request_body={"imsi": "208950999999999"},
            response_status=201,
            duration_ms=25.0,
        )
        self.logger.record(
            method="DELETE",
            url="https://api.example.com/ue/123",
            path="/ue/123",
            response_status=404,
            duration_ms=12.0,
        )

        post_logs = self.logger.get_logs(method="POST")
        self.assertEqual(len(post_logs), 1)
        self.assertEqual(post_logs[0]["method"], "POST")

        status_logs = self.logger.get_logs(status_code=404)
        self.assertEqual(len(status_logs), 1)
        self.assertEqual(status_logs[0]["response_status"], 404)

        search_logs = self.logger.get_logs(search="208950999999999")
        self.assertEqual(len(search_logs), 1)
        self.assertEqual(search_logs[0]["request_body"]["imsi"], "208950999999999")

    def test_set_capacity(self):
        logger = APIDebugLogger(max_capacity=10)
        self.assertEqual(logger.max_capacity, 10)
        logger.set_capacity(50)
        self.assertEqual(logger.max_capacity, 50)
        # Clamped min/max
        logger.set_capacity(5)
        self.assertEqual(logger.max_capacity, 10)  # min 10
        logger.set_capacity(5000)
        self.assertEqual(logger.max_capacity, 1000)  # max 1000


class TestDebugLogEndpoints(unittest.TestCase):
    """Test FastAPI /api/debug/logs endpoints."""

    def test_get_debug_logs_endpoint(self):
        resp = client.get("/api/debug/logs")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("logs", data)

    def test_clear_and_export_debug_logs(self):
        # Clear
        del_resp = client.delete("/api/debug/logs")
        self.assertEqual(del_resp.status_code, 200)
        self.assertTrue(del_resp.json()["success"])

        # Check count 0
        get_resp = client.get("/api/debug/logs")
        self.assertEqual(get_resp.json()["count"], 0)

        # Export
        exp_resp = client.get("/api/debug/logs/export")
        self.assertEqual(exp_resp.status_code, 200)
        self.assertIn("transactions", exp_resp.json())


if __name__ == "__main__":
    unittest.main()
