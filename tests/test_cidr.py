"""
Unit tests for CIDR allocation and validation in Prisma SASE 5G.
"""
import unittest
from src.cidr import (
    DEFAULT_UE_CIDR_BLOCKS,
    parse_cidr_blocks,
    is_ip_in_cidr,
    get_allocatable_ips,
    get_next_available_ip
)

class TestCIDRModule(unittest.TestCase):
    def test_default_cidr_blocks(self):
        self.assertIn("10.45.0.0/16", DEFAULT_UE_CIDR_BLOCKS)

    def test_parse_cidr_blocks(self):
        cidrs = parse_cidr_blocks("10.45.0.0/16, 10.56.0.0/24")
        self.assertEqual(len(cidrs), 2)
        self.assertEqual(str(cidrs[0]), "10.45.0.0/16")
        self.assertEqual(str(cidrs[1]), "10.56.0.0/24")

    def test_is_ip_in_cidr(self):
        cidr_str = "10.45.0.0/16"
        # Valid host IPs in 10.45.0.0/16
        self.assertTrue(is_ip_in_cidr("10.45.0.1", cidr_str))
        self.assertTrue(is_ip_in_cidr("10.45.0.17", cidr_str))
        self.assertTrue(is_ip_in_cidr("10.45.0.254", cidr_str))
        self.assertTrue(is_ip_in_cidr("10.45.255.254", cidr_str))

        # Invalid: network / broadcast addresses
        self.assertFalse(is_ip_in_cidr("10.45.0.0", cidr_str)) # Network address
        self.assertFalse(is_ip_in_cidr("10.45.255.255", cidr_str)) # Broadcast address

        # Invalid: out of range
        self.assertFalse(is_ip_in_cidr("10.58.0.195", cidr_str))
        self.assertFalse(is_ip_in_cidr("192.168.1.1", cidr_str))
        self.assertFalse(is_ip_in_cidr("invalid-ip", cidr_str))

    def test_get_allocatable_ips(self):
        ips = get_allocatable_ips("10.45.0.0/16", limit=10)
        self.assertEqual(len(ips), 10)
        self.assertEqual(ips[0], "10.45.0.1")
        self.assertEqual(ips[1], "10.45.0.2")
        self.assertEqual(ips[2], "10.45.0.3")

    def test_get_next_available_ip(self):
        cidr_str = "10.45.0.0/16"
        used_ips = {"10.45.0.1", "10.45.0.2"}
        next_ip = get_next_available_ip(cidr_str, used_ips)
        self.assertEqual(next_ip, "10.45.0.3")

if __name__ == "__main__":
    unittest.main()
