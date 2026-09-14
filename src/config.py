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
    standalone_mode: bool = False  # False = Live SCM Cloud API (default), True = Standalone Demo Sandbox

    def validate(self) -> None:
        """Validate that either a static token, OAuth2 credentials, or standalone mode are enabled."""
        if self.standalone_mode:
            return
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
        raw_standalone = data.get("standalone_mode") or data.get("PANW_STANDALONE_MODE") or data.get("standaloneMode") or False
        if isinstance(raw_standalone, str):
            standalone_val = raw_standalone.lower() in ("true", "1", "yes", "on")
        else:
            standalone_val = bool(raw_standalone)

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
            standalone_mode=standalone_val,
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
    raw_standalone = json_data.get("standalone_mode") if "standalone_mode" in json_data else (json_data.get("PANW_STANDALONE_MODE") or os.getenv("PANW_STANDALONE_MODE") or False)
    if isinstance(raw_standalone, str):
        standalone_mode = raw_standalone.lower() in ("true", "1", "yes", "on")
    else:
        standalone_mode = bool(raw_standalone)

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
        standalone_mode=standalone_mode,
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
        "standalone_mode": bool(cfg_dict.get("standalone_mode", False)),
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
        f"PANW_STANDALONE_MODE={'true' if cleaned_json['standalone_mode'] else 'false'}",
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
            "PANW_STANDALONE_MODE": "true" if cleaned_json["standalone_mode"] else "false",
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


def export_demo_pack(scenario_name: str = "Prisma SASE 5G Fleet Snapshot", target_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Export the complete current state (SIMs, metadata, sessions, groups) as a portable Demo Pack JSON."""
    import time
    cfg = load_config(target_dir)
    return {
        "pack_version": "1.0",
        "scenario_name": scenario_name,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tenant_info": {
            "root_tsg_id": cfg.tsg_id or "1965438697",
            "root_tsg_name": "SP-5G-POC2-Transatel",
            "active_tsg_id": "1291887562",
            "active_tenant_name": "Transatel demo",
            "default_apn": cfg.default_apn or "sasetest",
            "default_ip_type": cfg.default_ip_type or "IPv4",
            "ue_cidr_blocks": cfg.ue_cidr_blocks or "10.56.0.192/27,10.56.0.224/27",
        },
        "sim_metadata": load_sim_metadata(target_dir),
        "active_sessions": load_active_sessions(target_dir),
        "group_metadata": load_group_metadata(target_dir),
        "cached_ues": load_cached_ues(target_dir),
        "cached_groups": load_cached_groups(target_dir),
    }


def import_demo_pack(pack_data: Dict[str, Any], target_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Import and apply a Demo Pack JSON into persistent local state."""
    if not isinstance(pack_data, dict):
        raise ValueError("Invalid Demo Pack format: expected JSON root object.")

    sim_meta = pack_data.get("sim_metadata", {})
    if isinstance(sim_meta, dict):
        save_sim_metadata(sim_meta, target_dir)

    active_sess = pack_data.get("active_sessions", {})
    if isinstance(active_sess, dict):
        save_active_sessions(active_sess, target_dir)

    grp_meta = pack_data.get("group_metadata", {})
    if isinstance(grp_meta, dict):
        save_group_metadata(grp_meta, target_dir)

    cached_ues = pack_data.get("cached_ues", [])
    if isinstance(cached_ues, list):
        save_cached_ues(cached_ues, target_dir)

    cached_groups = pack_data.get("cached_groups", [])
    if isinstance(cached_groups, list):
        save_cached_groups(cached_groups, target_dir)

    # If tenant info includes default APN or CIDRs, keep them
    tenant_info = pack_data.get("tenant_info", {})
    if isinstance(tenant_info, dict) and tenant_info.get("default_apn"):
        cfg = load_config(target_dir)
        if tenant_info.get("default_apn"):
            cfg.default_apn = tenant_info["default_apn"]
        if tenant_info.get("ue_cidr_blocks"):
            cfg.ue_cidr_blocks = tenant_info["ue_cidr_blocks"]
        save_config(cfg, target_dir)

    return {
        "success": True,
        "scenario_name": pack_data.get("scenario_name", "Imported Fleet"),
        "sims_count": len(sim_meta) or len(cached_ues) or len(active_sess),
        "active_sessions_count": len(active_sess),
        "groups_count": len(cached_groups) or len(grp_meta),
    }


BUILTIN_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "retail_supermarket": {
        "id": "retail_supermarket",
        "name": "Retail & Supermarket Fleet (SIDO Live Scenario)",
        "icon": "shopping-cart",
        "vertical": "retail",
        "description": "14 SIMs across Ingenico Smart POS terminals, Self-Checkout Kiosks, Zebra Barcode Scanners, and Store RFID Gates.",
        "sim_metadata": {
            "208956167163949": {"vertical": "retail", "device_type": "4K Digital Signage Edge Player", "icon": "credit-card", "custom_label": "POS-Display-01", "last_ip": "10.56.0.193"},
            "208950391678715": {"vertical": "retail", "device_type": "Ingenico Smart POS Terminal", "icon": "credit-card", "custom_label": "Lane-POS-01", "last_ip": "10.56.0.194"},
            "208954273357404": {"vertical": "retail", "device_type": "Interactive Self-Checkout Kiosk", "icon": "credit-card", "custom_label": "SelfCheckout-A", "last_ip": "10.56.0.196"},
            "208956993452553": {"vertical": "retail", "device_type": "Zebra Handheld Barcode Scanner", "icon": "credit-card", "custom_label": "Warehouse-Gun-1", "last_ip": "10.56.0.197"},
            "901370007299136": {"vertical": "retail", "device_type": "Interactive Self-Checkout Kiosk", "icon": "credit-card", "custom_label": "SelfCheckout-B", "last_ip": "10.56.0.199"},
            "901370007299147": {"vertical": "retail", "device_type": "4K Digital Signage Edge Player", "icon": "credit-card", "custom_label": "POS-Display-02", "last_ip": "10.56.0.200"},
            "901370007299137": {"vertical": "retail", "device_type": "Zebra Handheld Barcode Scanner", "icon": "credit-card", "custom_label": "Warehouse-Gun-2", "last_ip": "10.56.0.201"},
            "901370007299138": {"vertical": "retail", "device_type": "Store Inventory RFID Gate", "icon": "credit-card", "custom_label": "Dock-RFID-East", "last_ip": "10.56.0.202"},
            "901370001420683": {"vertical": "retail", "device_type": "Ingenico Smart POS Terminal", "icon": "credit-card", "custom_label": "Spare-POS-03"},
            "901370001420693": {"vertical": "retail", "device_type": "Interactive Self-Checkout Kiosk", "icon": "credit-card", "custom_label": "Spare-Kiosk-C"},
            "901370001420692": {"vertical": "retail", "device_type": "Ingenico Smart POS Terminal", "icon": "credit-card", "custom_label": "Drive-POS-04"},
            "901370001420700": {"vertical": "retail", "device_type": "Interactive Self-Checkout Kiosk", "icon": "credit-card", "custom_label": "SelfCheckout-D"},
            "901370001420701": {"vertical": "retail", "device_type": "Zebra Handheld Barcode Scanner", "icon": "credit-card", "custom_label": "Floor-Scanner-3"}
        },
        "active_sessions": {
            "208956167163949": {"ipv4_addr": "10.56.0.193", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950391678715": {"ipv4_addr": "10.56.0.194", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208954273357404": {"ipv4_addr": "10.56.0.196", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208956993452553": {"ipv4_addr": "10.56.0.197", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "901370007299136": {"ipv4_addr": "10.56.0.199", "apn": "sase", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "901370007299147": {"ipv4_addr": "10.56.0.200", "apn": "sase", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "901370007299137": {"ipv4_addr": "10.56.0.201", "apn": "sase", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "901370007299138": {"ipv4_addr": "10.56.0.202", "apn": "sase", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"}
        }
    },
    "smart_factory": {
        "id": "smart_factory",
        "name": "Smart Factory & Industry 4.0 Fleet",
        "icon": "bot",
        "vertical": "manufacturing",
        "description": "12 SIMs across Autonomous AGV Logistics Robots, Kuka 6-Axis Arms, Siemens S7 PLCs, and Acoustic Vibration Sensors.",
        "sim_metadata": {
            "208950000000001": {"vertical": "manufacturing", "device_type": "AGV Autonomous Logistics Robot", "icon": "bot", "custom_label": "AGV-Fleet-Alpha", "last_ip": "10.56.0.193"},
            "208950000000002": {"vertical": "manufacturing", "device_type": "AGV Autonomous Logistics Robot", "icon": "bot", "custom_label": "AGV-Fleet-Beta", "last_ip": "10.56.0.194"},
            "208950000000003": {"vertical": "manufacturing", "device_type": "Kuka 6-Axis Welding Robotic Arm", "icon": "bot", "custom_label": "Arm-Cell-01", "last_ip": "10.56.0.195"},
            "208950000000004": {"vertical": "manufacturing", "device_type": "Siemens S7 Industrial PLC Gateway", "icon": "bot", "custom_label": "PLC-Line-A", "last_ip": "10.56.0.196"},
            "208950000000005": {"vertical": "manufacturing", "device_type": "High-Precision Acoustic Vibration Sensor", "icon": "bot", "custom_label": "Sensor-Turbine-1", "last_ip": "10.56.0.197"},
            "208950000000006": {"vertical": "manufacturing", "device_type": "High-Precision Acoustic Vibration Sensor", "icon": "bot", "custom_label": "Sensor-Pump-4", "last_ip": "10.56.0.198"},
            "208950000000007": {"vertical": "manufacturing", "device_type": "Machine-Vision Quality Inspection Camera", "icon": "bot", "custom_label": "Vision-QC-01", "last_ip": "10.56.0.199"},
            "208950000000008": {"vertical": "manufacturing", "device_type": "Predictive Bearing Telemetry Node", "icon": "bot", "custom_label": "Bearing-Node-2", "last_ip": "10.56.0.200"},
            "208950000000009": {"vertical": "manufacturing", "device_type": "AGV Autonomous Logistics Robot", "icon": "bot", "custom_label": "AGV-Standby-03"},
            "208950000000010": {"vertical": "manufacturing", "device_type": "Siemens S7 Industrial PLC Gateway", "icon": "bot", "custom_label": "PLC-Line-B-Backup"},
            "208950000000011": {"vertical": "manufacturing", "device_type": "Kuka 6-Axis Welding Robotic Arm", "icon": "bot", "custom_label": "Arm-Cell-02"},
            "208950000000012": {"vertical": "manufacturing", "device_type": "High-Precision Acoustic Vibration Sensor", "icon": "bot", "custom_label": "Sensor-Hydraulic-9"}
        },
        "active_sessions": {
            "208950000000001": {"ipv4_addr": "10.56.0.193", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000002": {"ipv4_addr": "10.56.0.194", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000003": {"ipv4_addr": "10.56.0.195", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000004": {"ipv4_addr": "10.56.0.196", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000005": {"ipv4_addr": "10.56.0.197", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000006": {"ipv4_addr": "10.56.0.198", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000007": {"ipv4_addr": "10.56.0.199", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000008": {"ipv4_addr": "10.56.0.200", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"}
        }
    },
    "ev_infrastructure": {
        "id": "ev_infrastructure",
        "name": "EV Infrastructure & Smart Grid Hub",
        "icon": "zap",
        "vertical": "ev_infrastructure",
        "description": "10 SIMs across 350kW Ultra-Fast Chargers, Smart Grid Load Balancers, Fleet Depot Controllers, and OCPI Payment Terminals.",
        "sim_metadata": {
            "208950000000101": {"vertical": "ev_infrastructure", "device_type": "Ultra-Fast Hub Power Unit (350kW)", "icon": "zap", "custom_label": "EVSE-Charger-01", "last_ip": "10.56.0.193"},
            "208950000000102": {"vertical": "ev_infrastructure", "device_type": "Ultra-Fast Hub Power Unit (350kW)", "icon": "zap", "custom_label": "EVSE-Charger-02", "last_ip": "10.56.0.194"},
            "208950000000103": {"vertical": "ev_infrastructure", "device_type": "EV Smart Grid Load Balancer", "icon": "zap", "custom_label": "Grid-Balancer-North", "last_ip": "10.56.0.195"},
            "208950000000104": {"vertical": "ev_infrastructure", "device_type": "Fleet Depot Charging Controller", "icon": "zap", "custom_label": "Depot-Master-Bus", "last_ip": "10.56.0.196"},
            "208950000000105": {"vertical": "ev_infrastructure", "device_type": "Payment & RFID Authorizer Gateway", "icon": "zap", "custom_label": "OCPI-Payment-01", "last_ip": "10.56.0.197"},
            "208950000000106": {"vertical": "ev_infrastructure", "device_type": "EVSE Fast-Charger OCPI Gateway", "icon": "zap", "custom_label": "EVSE-Gateway-03", "last_ip": "10.56.0.198"},
            "208950000000107": {"vertical": "ev_infrastructure", "device_type": "Ultra-Fast Hub Power Unit (350kW)", "icon": "zap", "custom_label": "EVSE-Charger-03-Standby"},
            "208950000000108": {"vertical": "ev_infrastructure", "device_type": "Fleet Depot Charging Controller", "icon": "zap", "custom_label": "Depot-Slave-Trucks"},
            "208950000000109": {"vertical": "ev_infrastructure", "device_type": "Payment & RFID Authorizer Gateway", "icon": "zap", "custom_label": "OCPI-Payment-02-Spare"},
            "208950000000110": {"vertical": "ev_infrastructure", "device_type": "EV Smart Grid Load Balancer", "icon": "zap", "custom_label": "Grid-Balancer-South"}
        },
        "active_sessions": {
            "208950000000101": {"ipv4_addr": "10.56.0.193", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000102": {"ipv4_addr": "10.56.0.194", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000103": {"ipv4_addr": "10.56.0.195", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000104": {"ipv4_addr": "10.56.0.196", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000105": {"ipv4_addr": "10.56.0.197", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"},
            "208950000000106": {"ipv4_addr": "10.56.0.198", "apn": "sasetest", "status": "Active", "region": "europe-west9", "tenant_status": "Yes"}
        }
    }
}


def get_builtin_scenario_presets() -> List[Dict[str, Any]]:
    """Return summary list of pre-configured demo fleet scenarios."""
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "icon": s["icon"],
            "vertical": s["vertical"],
            "description": s["description"],
            "sim_count": len(s.get("sim_metadata", {})),
            "active_sessions_count": len(s.get("active_sessions", {})),
        }
        for s in BUILTIN_SCENARIOS.values()
    ]


def load_builtin_scenario(preset_id: str, target_dir: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Load and apply a built-in demo scenario into local persistent state."""
    scenario = BUILTIN_SCENARIOS.get(preset_id)
    if not scenario:
        raise ValueError(f"Unknown preset ID: '{preset_id}'. Available: {list(BUILTIN_SCENARIOS.keys())}")

    pack = {
        "pack_version": "1.0",
        "scenario_name": scenario["name"],
        "sim_metadata": scenario["sim_metadata"],
        "active_sessions": scenario["active_sessions"],
        "cached_ues": [],
        "cached_groups": [],
    }
    return import_demo_pack(pack, target_dir)



