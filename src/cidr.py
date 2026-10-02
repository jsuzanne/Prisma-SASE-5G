"""CIDR parsing, IP allocation, and validation for Prisma SASE 5G subscriber sessions."""

import ipaddress
from typing import List, Set, Optional, Dict, Any


DEFAULT_UE_CIDR_BLOCKS = "10.45.0.0/16"


def parse_cidr_blocks(cidr_str: Optional[str]) -> List[ipaddress.IPv4Network]:
    """Parse comma or semicolon-separated CIDR strings into IPv4Network objects."""
    if not cidr_str:
        cidr_str = DEFAULT_UE_CIDR_BLOCKS
    networks = []
    for item in cidr_str.replace(";", ",").split(","):
        item = item.strip()
        if item:
            try:
                net = ipaddress.ip_network(item, strict=False)
                if isinstance(net, ipaddress.IPv4Network):
                    networks.append(net)
            except Exception:
                pass
    return networks


def is_ip_in_cidr(ip_str: str, cidr_str: Optional[str] = None) -> bool:
    """Check if an IPv4 address string belongs to any of the configured CIDR blocks as a valid host."""
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        networks = parse_cidr_blocks(cidr_str)
        if not networks:
            return True
        for net in networks:
            if ip in net:
                if net.prefixlen < 31:
                    if ip == net.network_address or ip == net.broadcast_address:
                        return False
                return True
        return False
    except Exception:
        return False


def get_allocatable_ips(cidr_str: Optional[str] = None, limit: int = 200) -> List[str]:
    """Get usable host IPv4 addresses across the configured CIDR blocks."""
    networks = parse_cidr_blocks(cidr_str)
    ips: List[str] = []
    for net in networks:
        for ip in net.hosts():
            ips.append(str(ip))
            if len(ips) >= limit:
                break
        if len(ips) >= limit:
            break
    return ips


def get_next_available_ip(
    cidr_str: Optional[str] = None,
    used_ips: Optional[Set[str]] = None,
    preferred_fallback: str = "10.45.0.2"
) -> str:
    """Find the first unassigned IP within the configured CIDR blocks."""
    used = set(used_ips or set())
    allocatable = get_allocatable_ips(cidr_str)
    for ip in allocatable:
        if ip not in used:
            return ip
    # Fallback if all used or none found
    if is_ip_in_cidr(preferred_fallback, cidr_str):
        return preferred_fallback
    return allocatable[0] if allocatable else preferred_fallback
