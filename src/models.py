"""Data models for Prisma SASE 5G resources."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import time


@dataclass
class TenantUEMapping:
    """Represents a SIM Card / User Equipment (UE) mapping to a Tenant Service Group."""
    imsi: str
    imei: str
    apn: str
    tsg_id: Optional[str] = None
    root_tsg_id: Optional[str] = None
    identity_id: Optional[str] = None
    groups: List[Dict[str, Any]] = field(default_factory=list)
    tenant_name: Optional[str] = None
    ipv4_addr: Optional[str] = None
    ipv6_addr: Optional[str] = None
    status: Optional[str] = "Inactive"  # "Active" | "Inactive"
    region: Optional[str] = None       # e.g. "europe-west9"
    tenant_status: Optional[str] = "No"  # "Yes" | "No"
    create_time: Optional[int] = None
    update_time: Optional[int] = None
    vertical: Optional[str] = None
    device_type: Optional[str] = None
    custom_label: Optional[str] = None
    icon: Optional[str] = None

    def to_request_payload(self) -> Dict[str, Any]:
        """Convert to API JSON payload for POST /mt/manage/5g/tenantUEInfo."""
        payload = {
            "imsi": str(self.imsi),
            "imei": str(self.imei),
            "apn": str(self.apn),
        }
        if self.tsg_id:
            payload["tsg_id"] = str(self.tsg_id)
        if self.root_tsg_id:
            payload["root_tsg_id"] = str(self.root_tsg_id)
        return payload

    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> "TenantUEMapping":
        """Create an instance from an API JSON response object."""
        # Detect IP addresses if returned by SCM or session correlation
        ipv4 = data.get("ipv4_addr") or data.get("ipv4Addr") or data.get("ip_address") or data.get("ip")
        ipv6 = data.get("ipv6_addr") or data.get("ipv6Addr")
        
        raw_status = data.get("status")
        if raw_status:
            status = "Active" if str(raw_status).lower() in ("active", "true", "up", "1") else "Inactive"
        else:
            status = "Active" if (ipv4 or ipv6) else "Inactive"

        region = data.get("region") or data.get("compute_region") or data.get("computeRegion")
        if not region and status == "Active":
            region = "europe-west9"

        tenant_status = data.get("tenant_status") or data.get("tenantStatus")
        if tenant_status is None:
            tenant_status = "Yes" if status == "Active" else "No"
        elif isinstance(tenant_status, bool):
            tenant_status = "Yes" if tenant_status else "No"

        return cls(
            imsi=str(data.get("imsi", "")),
            imei=str(data.get("imei", "")),
            apn=str(data.get("apn", "")),
            tsg_id=data.get("tsg_id"),
            root_tsg_id=data.get("root_tsg_id"),
            identity_id=data.get("identity_id") or data.get("id"),
            groups=data.get("group", []) or data.get("groups", []),
            tenant_name=data.get("tenant_name"),
            ipv4_addr=ipv4,
            ipv6_addr=ipv6,
            status=status,
            region=region,
            tenant_status=str(tenant_status),
            create_time=data.get("create_time") or data.get("time_added"),
            update_time=data.get("update_time"),
        )


@dataclass
class UESession:
    """Represents real-time 5G subscriber session telemetry for registration/deregistration."""
    imsi: str
    imei: str
    apn: str
    ip_type: str = "IPv4"  # IPv4, IPv6, IPv4v6
    ipv4_addr: Optional[str] = None
    ipv6_addr: Optional[str] = None
    event_time: int = field(default_factory=lambda: int(time.time() * 1000))
    expiry_time: Optional[int] = None
    slice_id: Optional[str] = None
    msisdn: Optional[str] = None
    rat_type: Optional[str] = None
    cell_id: Optional[str] = None
    supi: Optional[str] = None

    def to_request_payload(self) -> Dict[str, Any]:
        """Convert to API item for POST /mt/manage/5g/register/ue or /mt/manage/5g/deregister/ue."""
        payload: Dict[str, Any] = {
            "imsi": str(self.imsi),
            "imei": str(self.imei),
            "apn": str(self.apn),
            "ipType": str(self.ip_type),
            "eventTime": int(self.event_time),
        }
        if self.ipv4_addr:
            payload["ipv4Addr"] = self.ipv4_addr
        if self.ipv6_addr:
            payload["ipv6Addr"] = self.ipv6_addr
        if self.expiry_time is not None:
            payload["expiryTime"] = int(self.expiry_time)
        if self.slice_id:
            payload["sliceId"] = self.slice_id
        if self.msisdn:
            payload["msisdn"] = self.msisdn
        if self.rat_type:
            payload["ratType"] = self.rat_type
        if self.cell_id:
            payload["cellId"] = self.cell_id
        if self.supi:
            payload["supi"] = self.supi
        return payload


@dataclass
class UserGroup:
    """Represents a named 5G subscriber group."""
    group_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    tsg_id: Optional[str] = None
    user_count: Optional[int] = None
    tenant_name: Optional[str] = None
    identity_ids: List[str] = field(default_factory=list)

    @classmethod
    def from_api_dict(cls, data: Dict[str, Any]) -> "UserGroup":
        if not isinstance(data, dict):
            return cls()
        identities = data.get("identity_id") or data.get("identityIds") or data.get("identity_ids") or []
        count = data.get("user_count") or data.get("userCount")
        if count is None and isinstance(identities, list):
            count = len(identities)
        return cls(
            group_id=str(data.get("id") or data.get("group_id") or data.get("groupId") or ""),
            name=str(data.get("name") or data.get("group_name") or data.get("groupName") or ""),
            description=data.get("description"),
            tsg_id=str(data.get("tsg_id") or data.get("tsgId") or "") if (data.get("tsg_id") or data.get("tsgId")) else None,
            user_count=count,
            identity_ids=identities if isinstance(identities, list) else [],
        )

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "UserGroup":
        return cls.from_api_dict(data)


@dataclass
class SliceConfig:
    """Represents a 5G Network Slice (S-NSSAI: SST + SD)."""
    sst: int = 1
    sd: Optional[str] = None
    default_indicator: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"sst": self.sst, "default_indicator": self.default_indicator}
        if self.sd:
            d["sd"] = self.sd
        return d


@dataclass
class QoSConfig:
    """Represents 5G QoS parameters (5QI, AMBR)."""
    five_qi: int = 9
    ambr_dl_mbps: int = 100
    ambr_ul_mbps: int = 50
    arp_priority: int = 8
    arp_preempt_cap: int = 1
    arp_preempt_vuln: int = 1

    def to_mongo_session_qos(self, dnn: str = "internet") -> Dict[str, Any]:
        """Convert to Open5GS MongoDB session QoS structure."""
        return {
            "name": dnn,
            "type": 3,  # IPv4
            "ambr": {
                "downlink": {"value": self.ambr_dl_mbps, "unit": 3},  # Unit 3 = Mbps
                "uplink": {"value": self.ambr_ul_mbps, "unit": 3},
            },
            "qos": {
                "index": self.five_qi,
                "arp": {
                    "priority_level": self.arp_priority,
                    "pre_emption_capability": self.arp_preempt_cap,
                    "pre_emption_vulnerability": self.arp_preempt_vuln,
                },
            },
        }


@dataclass
class SecurityConfig:
    """Represents 5G SIM cryptographic credentials."""
    k: str
    op: str
    op_type: str = "OPC"  # OP or OPC
    amf: str = "8000"
    sqn: int = 0

    def to_mongo_security(self) -> Dict[str, Any]:
        """Convert to Open5GS MongoDB security subdocument."""
        sec = {
            "k": self.k.upper(),
            "amf": self.amf,
            "op_type": self.op_type.upper(),
            "sqn": self.sqn,
        }
        if self.op_type.upper() == "OP":
            sec["op"] = self.op.upper()
        else:
            sec["opc"] = self.op.upper()
        return sec


@dataclass
class OrchestratedEndpoint:
    """Full lifecycle state of a 5G endpoint across Core, RAN, Prisma, and Traffic."""
    imsi: str
    imei: str
    apn: str
    vertical_id: str
    device_name: str
    vendor: str
    device_model: str
    icon: str
    security: SecurityConfig
    slice: SliceConfig
    qos: QoSConfig
    state: str = "pending"  # pending, core_ok, ran_ok, identity_ok, session_active, registered, failed, deleting
    ipv4_addr: Optional[str] = None
    ipv6_addr: Optional[str] = None
    tun_interface: Optional[str] = None
    psi: Optional[int] = None
    pid: Optional[int] = None
    prisma_group: Optional[str] = None
    prisma_identity_id: Optional[str] = None
    traffic_active: bool = False
    last_error: Optional[str] = None
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API response (hiding secret K/OPc)."""
        return {
            "imsi": self.imsi,
            "imei": self.imei,
            "apn": self.apn,
            "vertical_id": self.vertical_id,
            "device_name": self.device_name,
            "vendor": self.vendor,
            "device_model": self.device_model,
            "icon": self.icon,
            "slice": self.slice.to_dict(),
            "qos": {
                "5qi": self.qos.five_qi,
                "ambr_dl_mbps": self.qos.ambr_dl_mbps,
                "ambr_ul_mbps": self.qos.ambr_ul_mbps,
            },
            "state": self.state,
            "ipv4_addr": self.ipv4_addr,
            "ipv6_addr": self.ipv6_addr,
            "tun_interface": self.tun_interface,
            "psi": self.psi,
            "prisma_group": self.prisma_group,
            "prisma_identity_id": self.prisma_identity_id,
            "traffic_active": self.traffic_active,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

