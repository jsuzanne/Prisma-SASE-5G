"""Industry Vertical Profiles and Device Generator for 5G SASE Orchestration."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import os
import random
import secrets


def calculate_luhn_check_digit(digits: str) -> str:
    """Calculate Luhn check digit for a 14-digit IMEI payload."""
    total = 0
    for i, char in enumerate(digits):
        n = int(char)
        if i % 2 == 1:  # 2nd, 4th, 6th... digits in 1-indexed (even positions)
            n *= 2
            if n > 9:
                n = (n // 10) + (n % 10)
        total += n
    check_digit = (10 - (total % 10)) % 10
    return str(check_digit)


def generate_k() -> str:
    """Generate a random 128-bit permanent subscription key (K) in uppercase hex."""
    return secrets.token_hex(16).upper()


def generate_opc() -> str:
    """Generate a random 128-bit Operator Code (OPc) in uppercase hex."""
    return secrets.token_hex(16).upper()


def generate_imei(tac: str) -> str:
    """
    Generate a 15-digit IMEI given an 8-digit TAC prefix.
    Format: TAC (8) + SNR (6) + CD (1 Luhn Check Digit).
    """
    tac_clean = "".join(filter(str.isdigit, str(tac)))[:8].ljust(8, "0")
    snr = "".join([str(random.randint(0, 9)) for _ in range(6)])
    partial = f"{tac_clean}{snr}"
    cd = calculate_luhn_check_digit(partial)
    return f"{partial}{cd}"


def generate_imeisv(tac: str, software_version: str = "01") -> str:
    """
    Generate a 16-digit IMEISV given an 8-digit TAC prefix and 2-digit SV.
    Format: TAC (8) + SNR (6) + SV (2).
    """
    tac_clean = "".join(filter(str.isdigit, str(tac)))[:8].ljust(8, "0")
    snr = "".join([str(random.randint(0, 9)) for _ in range(6)])
    sv = "".join(filter(str.isdigit, str(software_version)))[:2].zfill(2)
    return f"{tac_clean}{snr}{sv}"


@dataclass
class VerticalProfile:
    """Defines an industry vertical template with radio, security, and traffic parameters."""
    id: str
    name: str
    vendor: str
    device_model: str
    tac_prefix: str
    category: str
    icon: str
    description: str
    apn: str
    sst: int
    sd: Optional[str]
    five_qi: int
    ambr_dl_mbps: int
    ambr_ul_mbps: int
    prisma_group: str
    traffic_profile: str
    traffic_protocol: str
    traffic_interval_sec: int
    default_payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "vendor": self.vendor,
            "device_model": self.device_model,
            "tac_prefix": self.tac_prefix,
            "category": self.category,
            "icon": self.icon,
            "description": self.description,
            "apn": self.apn,
            "slice": {
                "sst": self.sst,
                "sd": self.sd,
            },
            "qos": {
                "5qi": self.five_qi,
                "ambr_dl_mbps": self.ambr_dl_mbps,
                "ambr_ul_mbps": self.ambr_ul_mbps,
            },
            "prisma_group": self.prisma_group,
            "traffic": {
                "profile": self.traffic_profile,
                "protocol": self.traffic_protocol,
                "interval_sec": self.traffic_interval_sec,
            },
        }


VERTICAL_CATALOG: Dict[str, VerticalProfile] = {
    "smart_camera": VerticalProfile(
        id="smart_camera",
        name="Smart City 4K Surveillance Camera",
        vendor="Axis Communications",
        device_model="AXIS Q3538-LVE 4K Dome",
        tac_prefix="35412809",
        category="Smart City / Video Surveillance",
        icon="bi-camera-video",
        description="High-bandwidth 4K video surveillance streaming with zero-trust perimeter inspection.",
        apn="video.5g",
        sst=1,
        sd="000001",
        five_qi=4,  # Non-GBR Video Stream
        ambr_dl_mbps=20,
        ambr_ul_mbps=100,  # High uplink for video stream
        prisma_group="Surveillance-Cameras",
        traffic_profile="rtsp_video_stream",
        traffic_protocol="RTSP/HTTPS",
        traffic_interval_sec=5,
        default_payload={"resolution": "3840x2160", "fps": 30, "codec": "H.265"},
    ),
    "industry_plc": VerticalProfile(
        id="industry_plc",
        name="Industrial PLC & AGV Controller",
        vendor="Siemens",
        device_model="SIMATIC S7-1500 TM 5G",
        tac_prefix="86329404",
        category="Industry 4.0 / Smart Factory",
        icon="bi-cpu",
        description="Ultra-reliable low-latency controller for robotic assembly and AGVs.",
        apn="factory.io",
        sst=2,  # URLLC Slice
        sd="000002",
        five_qi=82,  # Discrete Automation Delay Critical
        ambr_dl_mbps=50,
        ambr_ul_mbps=50,
        prisma_group="Industrial-PLCs",
        traffic_profile="modbus_opcua_telemetry",
        traffic_protocol="Modbus/OPC-UA",
        traffic_interval_sec=1,
        default_payload={"cycle_time_ms": 10, "telemetry_vars": 64},
    ),
    "connected_ambulance": VerticalProfile(
        id="connected_ambulance",
        name="Connected Ambulance & Telemedicine",
        vendor="Stryker",
        device_model="LIFEPAK 15 Defibrillator/Monitor 5G",
        tac_prefix="35891207",
        category="Healthcare / Emergency",
        icon="bi-heart-pulse",
        description="Critical medical telemetry and real-time vital signs transmission to emergency departments.",
        apn="health.net",
        sst=1,
        sd="000003",
        five_qi=2,  # Conversational Video / High Priority
        ambr_dl_mbps=50,
        ambr_ul_mbps=50,
        prisma_group="Emergency-Vehicles",
        traffic_profile="medical_telemetry_dicom",
        traffic_protocol="HTTPS/DICOM",
        traffic_interval_sec=2,
        default_payload={"ecg_sample_rate": 500, "spo2": 98, "hr": 72},
    ),
    "smart_meter": VerticalProfile(
        id="smart_meter",
        name="Smart Grid Electrical Meter",
        vendor="Schneider Electric",
        device_model="PowerLogic PM8000 5G IoT",
        tac_prefix="86751203",
        category="Smart Utilities / Energy",
        icon="bi-lightning-charge",
        description="Low-power IoT telemetry reporting grid frequency, load metrics, and power quality.",
        apn="sensor.iot",
        sst=3,  # Massive IoT / eMTC Slice
        sd="000004",
        five_qi=9,  # Default IoT Best Effort
        ambr_dl_mbps=5,
        ambr_ul_mbps=5,
        prisma_group="Smart-Meters",
        traffic_profile="mqtt_sensor_heartbeat",
        traffic_protocol="MQTT/CoAP",
        traffic_interval_sec=10,
        default_payload={"voltage_v": 230.2, "current_a": 14.5, "frequency_hz": 50.0},
    ),
    "executive_user": VerticalProfile(
        id="executive_user",
        name="Executive Mobile User (Smartphone)",
        vendor="Apple",
        device_model="Apple iPhone 15 Pro 5G",
        tac_prefix="35693803",
        category="Enterprise / Human User",
        icon="bi-phone",
        description="Enterprise corporate user accessing cloud SaaS, email, and web browsing.",
        apn="internet",
        sst=1,
        sd="ffffff",
        five_qi=9,
        ambr_dl_mbps=1000,
        ambr_ul_mbps=200,
        prisma_group="Executive-VIPs",
        traffic_profile="web_cloud_browsing",
        traffic_protocol="HTTPS/DNS",
        traffic_interval_sec=3,
        default_payload={"apps": ["Office365", "Salesforce", "Internal-Intranet"]},
    ),
}


def get_vertical(vertical_id: str) -> Optional[VerticalProfile]:
    """Retrieve a vertical profile by ID."""
    return VERTICAL_CATALOG.get(vertical_id)


def list_verticals() -> List[Dict[str, Any]]:
    """Return all vertical profiles as list of dictionaries."""
    return [profile.to_dict() for profile in VERTICAL_CATALOG.values()]


def generate_device_credentials(vertical_id: str, custom_imsi: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate complete credentials (IMSI, IMEI, IMEISV, K, OPc, Slice, QoS) for a vertical.
    """
    profile = get_vertical(vertical_id) or VERTICAL_CATALOG["executive_user"]
    
    # Generate realistic credentials
    imei = generate_imei(profile.tac_prefix)
    imeisv = generate_imeisv(profile.tac_prefix)
    k = generate_k()
    opc = generate_opc()
    
    return {
        "vertical_id": profile.id,
        "vertical_name": profile.name,
        "vendor": profile.vendor,
        "device_model": profile.device_model,
        "icon": profile.icon,
        "imsi": custom_imsi or "",
        "imei": imei,
        "imeisv": imeisv,
        "apn": profile.apn,
        "k": k,
        "op": opc,
        "opc": opc,
        "op_type": "OPC",
        "amf": "8000",
        "sqn": 0,
        "slice": {
            "sst": profile.sst,
            "sd": profile.sd,
            "default_indicator": True,
        },
        "qos": {
            "5qi": profile.five_qi,
            "ambr_dl_mbps": profile.ambr_dl_mbps,
            "ambr_ul_mbps": profile.ambr_ul_mbps,
        },
        "prisma_group": profile.prisma_group,
        "traffic_profile": profile.traffic_profile,
    }
