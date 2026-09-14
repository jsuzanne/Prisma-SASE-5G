"""Configuration loader, validator, and persistent storage for Prisma SASE 5G."""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None, override=False):
        """Fallback lightweight .env loader if python-dotenv is not installed."""
        if not dotenv_path:
            return
        p = Path(dotenv_path)
        if not p.exists():
            return
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if override or k not in os.environ:
                    os.environ[k] = v
        except Exception:
            pass

BASE_DIR = Path(__file__).resolve().parent.parent


def get_config_dir(custom_dir: Optional[Union[str, Path]] = None) -> Path:
    """Resolve the active configuration directory.
    
    Priority:
    1. Explicit custom_dir argument
    2. CONFIG_DIR environment variable
    3. BASE_DIR / 'config'
    """
    if custom_dir:
        return Path(custom_dir)
    env_dir = os.getenv("CONFIG_DIR")
    if env_dir:
        return Path(env_dir)
    return BASE_DIR / "config"


@dataclass
class Config:
    """Application configuration loaded from JSON, environment variables, or .env."""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tsg_id: Optional[str] = None
    auth_token: Optional[str] = None
    api_base_url: str = "https://api.sase.paloaltonetworks.com"
    auth_url: str = "https://auth.apps.paloaltonetworks.com/am/oauth2/access_token"
    default_apn: str = "sasetest"
    default_ip_type: str = "IPv4"
    ue_cidr_blocks: str = "10.56.0.192/27,10.56.0.224/27"

    def validate(self) -> None:
        """Validate that either a static token or OAuth2 credentials (client_id, client_secret, tsg_id) are provided."""
        if self.auth_token:
            return

        missing = []
        if not self.client_id:
            missing.append("PANW_CLIENT_ID / client_id")
        if not self.client_secret:
            missing.append("PANW_CLIENT_SECRET / client_secret")
        if not self.tsg_id:
            missing.append("PANW_TSG_ID / tsg_id")

        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                f"Configure via Settings in Web UI, config/config.json, or .env."
            )

    def to_dict(self, include_secret: bool = True) -> Dict[str, Any]:
        """Convert to standard dictionary."""
        data = asdict(self)
        if not include_secret:
            data.pop("client_secret", None)
            data.pop("auth_token", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Construct Config from a dictionary supporting camelCase, snake_case, and UPPERCASE keys."""
        return cls(
            client_id=data.get("client_id") or data.get("PANW_CLIENT_ID") or data.get("clientId"),
            client_secret=data.get("client_secret") or data.get("PANW_CLIENT_SECRET") or data.get("clientSecret"),
            tsg_id=data.get("tsg_id") or data.get("PANW_TSG_ID") or data.get("tsgId"),
            auth_token=data.get("auth_token") or data.get("PANW_AUTH_TOKEN") or data.get("authToken"),
            api_base_url=(data.get("api_base_url") or data.get("PANW_API_BASE_URL") or data.get("apiBaseUrl") or "https://api.sase.paloaltonetworks.com").rstrip("/"),
            auth_url=data.get("auth_url") or data.get("PANW_AUTH_URL") or data.get("authUrl") or "https://auth.apps.paloaltonetworks.com/am/oauth2/access_token",
            default_apn=data.get("default_apn") or data.get("DEFAULT_APN") or data.get("defaultApn") or "sasetest",
            default_ip_type=data.get("default_ip_type") or data.get("DEFAULT_IP_TYPE") or data.get("defaultIpType") or "IPv4",
            ue_cidr_blocks=data.get("ue_cidr_blocks") or data.get("PANW_UE_CIDR_BLOCKS") or data.get("UE_CIDR_BLOCKS") or data.get("ueCidrBlocks") or "10.56.0.192/27,10.56.0.224/27",
        )


def load_config(config_source: Optional[Union[str, Path]] = None) -> Config:
    """Load configuration from JSON file, .env file, or environment variables.
    
    Search order when config_source is None:
    1. CONFIG_DIR/config.json (e.g., config/config.json or /app/config/config.json)
    2. CONFIG_DIR/.env
    3. BASE_DIR/config/config.json
    4. BASE_DIR/.env
    5. CWD/.env
    6. Process environment variables (PANW_CLIENT_ID, etc.)
    """
    json_data: Dict[str, Any] = {}

    if config_source:
        p = Path(config_source)
        if p.is_dir():
            json_file = p / "config.json"
            env_file = p / ".env"
            if json_file.exists():
                try:
                    json_data = json.loads(json_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            elif env_file.exists():
                load_dotenv(dotenv_path=str(env_file), override=True)
        elif p.suffix == ".json" and p.exists():
            try:
                json_data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        elif p.exists():
            load_dotenv(dotenv_path=str(p), override=True)
    else:
        cfg_dir = get_config_dir()
        json_file = cfg_dir / "config.json"
        env_file = cfg_dir / ".env"
        base_json = BASE_DIR / "config" / "config.json"
        base_env = BASE_DIR / ".env"

        if json_file.exists():
            try:
                json_data = json.loads(json_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        elif base_json.exists():
            try:
                json_data = json.loads(base_json.read_text(encoding="utf-8"))
            except Exception:
                pass
        elif env_file.exists():
            load_dotenv(dotenv_path=str(env_file), override=True)
        elif base_env.exists():
            load_dotenv(dotenv_path=str(base_env), override=True)
        else:
            load_dotenv(override=True)

    # When JSON data exists from a saved config.json file, use its values
    client_id = json_data.get("client_id") or json_data.get("PANW_CLIENT_ID") or os.getenv("PANW_CLIENT_ID") or None
    client_secret = json_data.get("client_secret") or json_data.get("PANW_CLIENT_SECRET") or os.getenv("PANW_CLIENT_SECRET") or None
    tsg_id = json_data.get("tsg_id") or json_data.get("PANW_TSG_ID") or os.getenv("PANW_TSG_ID") or None
    auth_token = json_data.get("auth_token") or json_data.get("PANW_AUTH_TOKEN") or os.getenv("PANW_AUTH_TOKEN") or None
    api_base_url = json_data.get("api_base_url") or json_data.get("PANW_API_BASE_URL") or os.getenv("PANW_API_BASE_URL") or "https://api.sase.paloaltonetworks.com"
    auth_url = json_data.get("auth_url") or json_data.get("PANW_AUTH_URL") or os.getenv("PANW_AUTH_URL") or "https://auth.apps.paloaltonetworks.com/am/oauth2/access_token"
    default_apn = json_data.get("default_apn") or json_data.get("DEFAULT_APN") or os.getenv("DEFAULT_APN") or "sasetest"
    default_ip_type = json_data.get("default_ip_type") or json_data.get("DEFAULT_IP_TYPE") or os.getenv("DEFAULT_IP_TYPE") or "IPv4"
    ue_cidr_blocks = json_data.get("ue_cidr_blocks") or json_data.get("UE_CIDR_BLOCKS") or os.getenv("PANW_UE_CIDR_BLOCKS") or os.getenv("UE_CIDR_BLOCKS") or "10.56.0.192/27,10.56.0.224/27"

    config = Config(
        client_id=client_id,
        client_secret=client_secret,
        tsg_id=tsg_id,
        auth_token=auth_token,
        api_base_url=api_base_url.rstrip("/"),
        auth_url=auth_url,
        default_apn=default_apn,
        default_ip_type=default_ip_type,
        ue_cidr_blocks=ue_cidr_blocks,
    )
    return config


def save_config(
    config: Union[Config, Dict[str, Any]],
    target_dir: Optional[Union[str, Path]] = None,
    save_env_backup: bool = True
) -> Dict[str, Any]:
    """Persist configuration to a local config directory as config.json and optional .env.
    
    This ensures that when a Docker volume is mounted to /app/config (or ./config),
    all credentials and settings survive container recreation and upgrades.
    """
    is_custom_target = target_dir is not None
    cfg_dir = get_config_dir(target_dir)
    cfg_dir.mkdir(parents=True, exist_ok=True)

    if isinstance(config, Config):
        cfg_dict = config.to_dict(include_secret=True)
    else:
        cfg_dict = Config.from_dict(config).to_dict(include_secret=True)

    # 1. Save config.json
    json_path = cfg_dir / "config.json"
    cleaned_json = {
        "client_id": cfg_dict.get("client_id") or "",
        "client_secret": cfg_dict.get("client_secret") or "",
        "tsg_id": cfg_dict.get("tsg_id") or "",
        "api_base_url": cfg_dict.get("api_base_url") or "https://api.sase.paloaltonetworks.com",
        "auth_url": cfg_dict.get("auth_url") or "https://auth.apps.paloaltonetworks.com/am/oauth2/access_token",
        "default_apn": cfg_dict.get("default_apn") or "sasetest",
        "default_ip_type": cfg_dict.get("default_ip_type") or "IPv4",
        "ue_cidr_blocks": cfg_dict.get("ue_cidr_blocks") or "10.56.0.192/27,10.56.0.224/27",
    }
    json_path.write_text(json.dumps(cleaned_json, indent=2), encoding="utf-8")

    # 2. Save .env in config directory as companion
    env_path = cfg_dir / ".env"
    lines = [
        "# Palo Alto Networks Prisma SASE 5G Configuration",
        f"PANW_CLIENT_ID={cleaned_json['client_id']}",
        f"PANW_CLIENT_SECRET={cleaned_json['client_secret']}",
        f"PANW_TSG_ID={cleaned_json['tsg_id']}",
        f"PANW_API_BASE_URL={cleaned_json['api_base_url']}",
        f"PANW_AUTH_URL={cleaned_json['auth_url']}",
        f"DEFAULT_APN={cleaned_json['default_apn']}",
        f"DEFAULT_IP_TYPE={cleaned_json['default_ip_type']}",
        f"UE_CIDR_BLOCKS={cleaned_json['ue_cidr_blocks']}",
        "",
    ]
    env_content = "\n".join(lines)
    env_path.write_text(env_content, encoding="utf-8")

    # Only save to project root .env if saving to standard project config dir
    if save_env_backup and not is_custom_target:
        root_env = BASE_DIR / ".env"
        try:
            root_env.write_text(env_content, encoding="utf-8")
        except Exception:
            pass

    # 3. Synchronize current process environment variables if not isolated target
    if not is_custom_target:
        for k, v in {
            "PANW_CLIENT_ID": cleaned_json["client_id"],
            "PANW_CLIENT_SECRET": cleaned_json["client_secret"],
            "PANW_TSG_ID": cleaned_json["tsg_id"],
            "PANW_API_BASE_URL": cleaned_json["api_base_url"],
            "PANW_AUTH_URL": cleaned_json["auth_url"],
            "DEFAULT_APN": cleaned_json["default_apn"],
            "DEFAULT_IP_TYPE": cleaned_json["default_ip_type"],
            "UE_CIDR_BLOCKS": cleaned_json["ue_cidr_blocks"],
        }.items():
            if v:
                os.environ[k] = str(v)

    return {
        "success": True,
        "config_dir": str(cfg_dir),
        "json_path": str(json_path),
        "env_path": str(env_path),
    }


DEFAULT_SIM_METADATA: Dict[str, Dict[str, Any]] = {
    "901370001420683": {"vertical": "retail", "device_type": "Ingenico Smart POS Terminal", "icon": "credit-card", "custom_label": ""},
    "901370001420693": {"vertical": "retail", "device_type": "Interactive Self-Checkout Kiosk", "icon": "credit-card", "custom_label": None},
    "901370007299137": {"vertical": "retail", "device_type": "Zebra Handheld Barcode Scanner", "icon": "credit-card", "custom_label": "", "last_ip": "10.56.0.201"},
    "901370007299147": {"vertical": "retail", "device_type": "4K Digital Signage Edge Player", "icon": "credit-card", "custom_label": None, "last_ip": "10.56.0.200"},
    "901370007299136": {"vertical": "retail", "device_type": "Store Inventory RFID Gate", "icon": "credit-card", "custom_label": None, "last_ip": "10.56.0.199"},
    "901370001420692": {"vertical": "retail", "device_type": "Ingenico Smart POS Terminal", "icon": "credit-card", "custom_label": None},
    "901370001420700": {"vertical": "retail", "device_type": "Interactive Self-Checkout Kiosk", "icon": "credit-card", "custom_label": None},
    "901370001420701": {"vertical": "retail", "device_type": "Zebra Handheld Barcode Scanner", "icon": "credit-card", "custom_label": None, "last_ip": "10.56.0.195"},
    "208950391678715": {"vertical": "retail", "device_type": "Ingenico Smart POS Terminal", "icon": "credit-card", "custom_label": "", "last_ip": "10.56.0.194"},
    "208956167163949": {"vertical": "retail", "device_type": "4K Digital Signage Edge Player", "custom_label": "", "icon": "credit-card", "last_ip": "10.56.0.193"},
    "901370007299138": {"vertical": "retail", "device_type": "Store Inventory RFID Gate", "custom_label": "", "icon": "credit-card", "last_ip": "10.56.0.202"},
    "208954273357404": {"vertical": "retail", "device_type": "Interactive Self-Checkout Kiosk", "icon": "credit-card", "last_ip": "10.56.0.196", "custom_label": ""},
    "208956993452553": {"vertical": "retail", "device_type": "Zebra Handheld Barcode Scanner", "icon": "credit-card", "last_ip": "10.56.0.197", "custom_label": ""},
}


def get_sim_metadata_file(target_dir: Optional[Union[str, Path]] = None) -> Path:
    """Return path to sim_metadata.json in the configuration directory."""
    cfg_dir = get_config_dir(target_dir)
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "sim_metadata.json"


def load_sim_metadata(target_dir: Optional[Union[str, Path]] = None) -> Dict[str, Dict[str, Any]]:
    """Load local SIM metadata dictionary keyed by IMSI."""
    meta_file = get_sim_metadata_file(target_dir)
    if meta_file.exists():
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
            
    # Check fallback in config.json
    cfg_dir = get_config_dir(target_dir)
    cfg_json = cfg_dir / "config.json"
    if cfg_json.exists():
        try:
            data = json.loads(cfg_json.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "sim_metadata" in data and isinstance(data["sim_metadata"], dict):
                return data["sim_metadata"]
        except Exception:
            pass
            
    return {}


def save_sim_metadata(metadata: Dict[str, Dict[str, Any]], target_dir: Optional[Union[str, Path]] = None) -> None:
    """Persist local SIM metadata dictionary to sim_metadata.json."""
    meta_file = get_sim_metadata_file(target_dir)
    meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def update_single_sim_metadata(imsi: str, data: Dict[str, Any], target_dir: Optional[Union[str, Path]] = None) -> None:
    """Update or insert metadata for a specific IMSI."""
    if not imsi:
        return
    current = load_sim_metadata(target_dir)
    if imsi not in current:
        current[imsi] = {}
    current[imsi].update(data)
    save_sim_metadata(current, target_dir)


def delete_single_sim_metadata(imsi: str, target_dir: Optional[Union[str, Path]] = None) -> None:
    """Remove metadata for a specific IMSI."""
    if not imsi:
        return
    current = load_sim_metadata(target_dir)
    if imsi in current:
        del current[imsi]
        save_sim_metadata(current, target_dir)


def clear_all_sim_metadata(target_dir: Optional[Union[str, Path]] = None) -> None:
    """Clear all local SIM metadata (Cleanup / Raw SCM Reset mode)."""
    meta_file = get_sim_metadata_file(target_dir)
    if meta_file.exists():
        try:
            meta_file.write_text(json.dumps({}, indent=2), encoding="utf-8")
        except Exception:
            pass


# -----------------------------------------------------------------------------
# Local Group Metadata Storage (Name, Description, Policies)
# -----------------------------------------------------------------------------

DEFAULT_GROUP_DESCRIPTIONS = {
    "restrictive": "Strictly isolated IoT telemetry profile. High-security zero-trust policy blocking unauthorized external egress and non-industrial traffic.",
    "permissive": "Standard corporate / fleet profile. Permissive access allowing broad cloud connectivity, diagnostics, and standard enterprise applications."
}


def get_group_metadata_file(target_dir: Optional[Union[str, Path]] = None) -> Path:
    cfg_dir = get_config_dir(target_dir)
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "group_metadata.json"


def load_group_metadata(target_dir: Optional[Union[str, Path]] = None) -> Dict[str, Dict[str, Any]]:
    """Load local group metadata dictionary keyed by group_id or group_name."""
    meta_file = get_group_metadata_file(target_dir)
    if meta_file.exists():
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def save_group_metadata(metadata: Dict[str, Dict[str, Any]], target_dir: Optional[Union[str, Path]] = None) -> None:
    """Persist local group metadata dictionary to group_metadata.json."""
    meta_file = get_group_metadata_file(target_dir)
    meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def update_single_group_metadata(group_key: str, data: Dict[str, Any], target_dir: Optional[Union[str, Path]] = None) -> None:
    """Update or insert metadata for a specific group_id or group_name."""
    if not group_key:
        return
    current = load_group_metadata(target_dir)
    if group_key not in current:
        current[group_key] = {}
    current[group_key].update(data)
    save_group_metadata(current, target_dir)


def delete_single_group_metadata(group_key: str, target_dir: Optional[Union[str, Path]] = None) -> None:
    """Remove metadata for a specific group."""
    if not group_key:
        return
    current = load_group_metadata(target_dir)
    if group_key in current:
        del current[group_key]
        save_group_metadata(current, target_dir)


# -----------------------------------------------------------------------------
# Active 5G Sessions Storage (Persistent IP allocations & Telemetry)
# -----------------------------------------------------------------------------

DEFAULT_ACTIVE_5G_SESSIONS: Dict[str, Dict[str, Any]] = {
    "208956167163949": {
        "ipv4_addr": "10.56.0.193",
        "imei": "350000000000000",
        "apn": "sasetest",
        "status": "Active",
        "region": "europe-west9",
        "tenant_status": "Yes",
    },
    "208950391678715": {
        "ipv4_addr": "10.56.0.194",
        "imei": "860123391678710",
        "apn": "sasetest",
        "status": "Active",
        "region": "europe-west9",
        "tenant_status": "Yes",
    },
    "208954273357404": {
        "ipv4_addr": "10.56.0.196",
        "imei": "860123498537561",
        "apn": "sasetest",
        "status": "Active",
        "region": "europe-west9",
        "tenant_status": "Yes",
    },
    "208956993452553": {
        "ipv4_addr": "10.56.0.197",
        "imei": "860123583558530",
        "apn": "sasetest",
        "status": "Active",
        "region": "europe-west9",
        "tenant_status": "Yes",
    },
    "901370007299136": {
        "ipv4_addr": "10.56.0.199",
        "imei": "350000000000000",
        "apn": "sase",
        "status": "Active",
        "region": "europe-west9",
        "tenant_status": "Yes",
    },
    "901370007299147": {
        "ipv4_addr": "10.56.0.200",
        "imei": "350000000000000",
        "apn": "sase",
        "status": "Active",
        "region": "europe-west9",
        "tenant_status": "Yes",
    },
    "901370007299137": {
        "ipv4_addr": "10.56.0.201",
        "imei": "350000000000000",
        "apn": "sase",
        "status": "Active",
        "region": "europe-west9",
        "tenant_status": "Yes",
    },
    "901370007299138": {
        "ipv4_addr": "10.56.0.202",
        "imei": "860123176000730",
        "apn": "sase",
        "status": "Active",
        "region": "europe-west9",
        "tenant_status": "Yes",
    },
}


def get_active_sessions_file(target_dir: Optional[Union[str, Path]] = None) -> Path:
    cfg_dir = get_config_dir(target_dir)
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "active_sessions.json"


def load_active_sessions(target_dir: Optional[Union[str, Path]] = None) -> Dict[str, Dict[str, Any]]:
    """Load persistent active 5G sessions dictionary keyed by IMSI."""
    sess_file = get_active_sessions_file(target_dir)
    if sess_file.exists():
        try:
            data = json.loads(sess_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    # Initialize and return defaults
    save_active_sessions(DEFAULT_ACTIVE_5G_SESSIONS, target_dir)
    return dict(DEFAULT_ACTIVE_5G_SESSIONS)


def save_active_sessions(sessions: Dict[str, Dict[str, Any]], target_dir: Optional[Union[str, Path]] = None) -> None:
    """Persist active 5G sessions dictionary to active_sessions.json."""
    sess_file = get_active_sessions_file(target_dir)
    sess_file.write_text(json.dumps(sessions, indent=2), encoding="utf-8")


def update_single_active_session(imsi: str, data: Dict[str, Any], target_dir: Optional[Union[str, Path]] = None) -> None:
    """Update or record an active 5G session for a given IMSI."""
    if not imsi:
        return
    current = load_active_sessions(target_dir)
    if imsi not in current:
        current[imsi] = {}
    current[imsi].update(data)
    save_active_sessions(current, target_dir)


def delete_single_active_session(imsi: str, target_dir: Optional[Union[str, Path]] = None) -> None:
    """Remove / terminate an active 5G session for a given IMSI."""
    if not imsi:
        return
    current = load_active_sessions(target_dir)
    if imsi in current:
        del current[imsi]
        save_active_sessions(current, target_dir)


def get_cached_ues_file(target_dir: Optional[Union[str, Path]] = None) -> Path:
    cfg_dir = get_config_dir(target_dir)
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "cached_ues.json"


def load_cached_ues(target_dir: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    """Load cached SIM / UE list snapshot."""
    f = get_cached_ues_file(target_dir)
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def save_cached_ues(ues: List[Dict[str, Any]], target_dir: Optional[Union[str, Path]] = None) -> None:
    """Save SIM / UE list snapshot to cached_ues.json."""
    f = get_cached_ues_file(target_dir)
    f.write_text(json.dumps(ues, indent=2), encoding="utf-8")


def get_cached_groups_file(target_dir: Optional[Union[str, Path]] = None) -> Path:
    cfg_dir = get_config_dir(target_dir)
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "cached_groups.json"


def load_cached_groups(target_dir: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    """Load cached user group list snapshot."""
    f = get_cached_groups_file(target_dir)
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def save_cached_groups(groups: List[Dict[str, Any]], target_dir: Optional[Union[str, Path]] = None) -> None:
    """Save user group list snapshot to cached_groups.json."""
    f = get_cached_groups_file(target_dir)
    f.write_text(json.dumps(groups, indent=2), encoding="utf-8")


