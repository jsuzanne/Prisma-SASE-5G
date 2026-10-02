"""Verticals, equipment catalog presets, and 3GPP compliant identifier generators for Prisma SASE 5G."""

import random
from typing import Dict, List, Any, Optional


def compute_luhn_checksum(digits_without_check: str) -> str:
    """Calculate Luhn algorithm check digit for a 14-digit IMEI prefix."""
    digits = [int(d) for d in digits_without_check]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            doubled = d * 2
            total += doubled if doubled < 10 else (doubled - 9)
        else:
            total += d
    check_digit = (10 - (total % 10)) % 10
    return str(check_digit)


def generate_transatel_imsi() -> str:
    """Generate a valid 15-digit Transatel IMSI (MCC=208 France, MNC=95 Transatel)."""
    # MCC 208, MNC 95 + 10 random digits
    suffix = "".join([str(random.randint(0, 9)) for _ in range(10)])
    return f"20895{suffix}"


def generate_valid_imei(tac_prefix: str = "860123") -> str:
    """Generate a valid 15-digit IMEI with a realistic TAC and valid Luhn checksum."""
    # TAC is 8 digits, SNR is 6 digits -> 14 digits total before Luhn check
    tac_full = (tac_prefix + "".join([str(random.randint(0, 9)) for _ in range(8 - len(tac_prefix))]))[:8]
    snr = "".join([str(random.randint(0, 9)) for _ in range(6)])
    prefix14 = tac_full + snr
    check = compute_luhn_checksum(prefix14)
    return prefix14 + check


VERTICALS_CATALOG: Dict[str, Dict[str, Any]] = {
    "ev_infrastructure": {
        "id": "ev_infrastructure",
        "name": "EV Infrastructure",
        "icon": "zap",
        "color": "amber",
        "badge_class": "text-amber-400 bg-amber-500/10 border-amber-500/30",
        "description": "Charging stations, high-power hubs, and grid telemetry units",
        "suggested_group": "Restrictive",
        "equipment_types": [
            "EVSE Fast-Charger OCPI Gateway",
            "Ultra-Fast Hub Power Unit (350kW)",
            "EV Smart Grid Load Balancer",
            "Fleet Depot Charging Controller",
            "Payment & RFID Authorizer Gateway",
        ],
    },
    "manufacturing": {
        "id": "manufacturing",
        "name": "Manufacturing / Industry 4.0",
        "icon": "bot",
        "color": "cyan",
        "badge_class": "text-cyan-400 bg-cyan-500/10 border-cyan-500/30",
        "description": "Robotics, autonomous vehicles (AGV), PLC telemetry, and rugged tablets",
        "suggested_group": "Restrictive",
        "equipment_types": [
            "KUKA Industrial Robotic Arm",
            "Autonomous Mobile Robot (AGV/AMR)",
            "Rugged Factory Floor iPad Pro",
            "Siemens S7 PLC Edge Gateway",
            "Predictive Vibration Sensor Gateway",
        ],
    },
    "retail": {
        "id": "retail",
        "name": "Retail & Smart Commerce",
        "icon": "credit-card",
        "color": "emerald",
        "badge_class": "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
        "description": "Smart POS terminals, interactive self-checkouts, and digital signage",
        "suggested_group": "Restrictive",
        "equipment_types": [
            "Ingenico Smart POS Terminal",
            "Interactive Self-Checkout Kiosk",
            "Zebra Handheld Barcode Scanner",
            "4K Digital Signage Edge Player",
            "Store Inventory RFID Gate",
        ],
    },
    "aviation": {
        "id": "aviation",
        "name": "Aviation & Ground Ops",
        "icon": "plane",
        "color": "blue",
        "badge_class": "text-blue-400 bg-blue-500/10 border-blue-500/30",
        "description": "Line maintenance tablets, baggage logistics, and ground support equipment",
        "suggested_group": "Permissive",
        "equipment_types": [
            "Avionics Line Maintenance iPad",
            "Tarmac Ground Power Unit (GPU) IoT",
            "Baggage Logistics Handheld Terminal",
            "Aircraft Refueling Flow Meter",
            "Crew Electronic Flight Bag (EFB)",
        ],
    },
    "automotive": {
        "id": "automotive",
        "name": "Automotive & Telematics",
        "icon": "car",
        "color": "purple",
        "badge_class": "text-purple-400 bg-purple-500/10 border-purple-500/30",
        "description": "Telematics control units (TCU), OBD dongles, and fleet tracking",
        "suggested_group": "Restrictive",
        "equipment_types": [
            "Vehicle Telematics Control Unit (TCU)",
            "Commercial Fleet OBD-II Tracker",
            "Connected In-Vehicle Infotainment (IVI)",
            "Autonomous Driving Test Sensor Unit",
            "EV Battery Management Edge Unit",
        ],
    },
    "public_transport": {
        "id": "public_transport",
        "name": "Public Transport & Fleet",
        "icon": "bus",
        "color": "rose",
        "badge_class": "text-rose-400 bg-rose-500/10 border-rose-500/30",
        "description": "Buses, trains, passenger Wi-Fi gateways, and ticketing validators",
        "suggested_group": "Restrictive",
        "equipment_types": [
            "Bus Onboard Multi-WAN Router",
            "Contactless Ticketing & NFC Validator",
            "Passenger Real-Time Info Display",
            "CCTV Security Live Streaming Unit",
            "Driver Telematics Tablet",
        ],
    },
    "smart_city": {
        "id": "smart_city",
        "name": "Smart City & Utilities",
        "icon": "building-2",
        "color": "indigo",
        "badge_class": "text-indigo-400 bg-indigo-500/10 border-indigo-500/30",
        "description": "Smart metering, street lighting controllers, environmental sensors",
        "suggested_group": "Restrictive",
        "equipment_types": [
            "Smart Water & Gas Meter Concentrator",
            "Intelligent LED Streetlight Gateway",
            "Air Quality & Noise Sensor Station",
            "Smart Parking Space Detector",
            "Traffic Flow AI Camera Streamer",
        ],
    },
}


def get_all_verticals() -> List[Dict[str, Any]]:
    """Return list of all available verticals with their equipment options."""
    return list(VERTICALS_CATALOG.values())


def get_random_preset(vertical_id: Optional[str] = None) -> Dict[str, Any]:
    """Generate a realistic SIM template with random IMSI, IMEI, device type, and suggested group."""
    if not vertical_id or vertical_id not in VERTICALS_CATALOG:
        v_key = random.choice(list(VERTICALS_CATALOG.keys()))
    else:
        v_key = vertical_id

    v_data = VERTICALS_CATALOG[v_key]
    equipment = random.choice(v_data["equipment_types"])
    imsi = generate_transatel_imsi()
    imei = generate_valid_imei()

    return {
        "imsi": imsi,
        "imei": imei,
        "apn": "sasetest",
        "vertical_id": v_key,
        "vertical_name": v_data["name"],
        "icon": v_data["icon"],
        "device_type": equipment,
        "suggested_group": v_data["suggested_group"],
    }


def generate_fleet_devices(
    vertical_id: Optional[str] = None,
    count: int = 3,
    start_ip_suffix: int = 210,
) -> List[Dict[str, Any]]:
    """
    Generate a list of realistic IoT devices ready for batch registration.
    If vertical_id is 'all' or None, generates 1 device per available vertical (7 verticals).
    If vertical_id is specified (e.g. 'ev_infrastructure'), generates `count` devices for that vertical.
    """
    devices = []
    if vertical_id in [None, "all", ""]:
        # 1 device for each of the 7 verticals
        for i, (v_key, v_data) in enumerate(VERTICALS_CATALOG.items()):
            eq = random.choice(v_data["equipment_types"])
            devices.append({
                "imsi": generate_transatel_imsi(),
                "imei": generate_valid_imei(),
                "apn": "sasetest",
                "vertical": v_key,
                "vertical_name": v_data["name"],
                "device_type": eq,
                "icon": v_data["icon"],
                "custom_label": None,
                "suggested_group": v_data["suggested_group"],
                "session_ip": f"10.45.0.{start_ip_suffix + i}",
            })
    else:
        v_data = VERTICALS_CATALOG.get(vertical_id)
        if not v_data:
            v_data = list(VERTICALS_CATALOG.values())[0]
            vertical_id = v_data["id"]

        equipment_list = list(v_data["equipment_types"])
        random.shuffle(equipment_list)

        for i in range(count):
            eq = equipment_list[i % len(equipment_list)]
            devices.append({
                "imsi": generate_transatel_imsi(),
                "imei": generate_valid_imei(),
                "apn": "sasetest",
                "vertical": vertical_id,
                "vertical_name": v_data["name"],
                "device_type": eq,
                "icon": v_data["icon"],
                "custom_label": None,
                "suggested_group": v_data["suggested_group"],
                "session_ip": f"10.45.0.{start_ip_suffix + i}",
            })
    return devices


def enrich_existing_imsis(
    imsis: List[str],
    vertical_id: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Generate realistic industry metadata for an existing list of IMSIs.
    If vertical_id is 'all' or None: distributes the IMSIs across the 7 available verticals.
    If vertical_id is specific (e.g. 'ev_infrastructure'): assigns equipment types from that vertical.
    """
    result = {}
    vertical_keys = list(VERTICALS_CATALOG.keys())

    for i, imsi in enumerate(imsis):
        if vertical_id and vertical_id != "all" and vertical_id in VERTICALS_CATALOG:
            v_key = vertical_id
        else:
            v_key = vertical_keys[i % len(vertical_keys)]

        v_data = VERTICALS_CATALOG[v_key]
        equipment_list = v_data["equipment_types"]
        eq_name = equipment_list[i % len(equipment_list)]

        result[str(imsi)] = {
            "vertical": v_key,
            "device_type": eq_name,
            "icon": v_data["icon"],
            "custom_label": None,
        }
    return result



