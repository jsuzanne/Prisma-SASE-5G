"""FastAPI Web Application for Prisma SASE 5G Management & Lifecycle.

Provides REST APIs and serves a responsive single-page web application for:
- Viewing Tenant Hierarchy (Root MSP, Transatel demo, tenant-1)
- Managing SIM Cards / UEs (Inventory, Group Badges, Add, Delete)
- 5G Session Telemetry (Register Session IP, Deregister)
- Subscriber User Groups Explorer (Permissive, Restrictive)
- Interactive Full Lifecycle Test Runner
- In-App Settings & Credentials Manager (.env)
"""

import os
import time
import random
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import (
    Config,
    load_config,
    save_config,
    get_config_dir,
    load_sim_metadata,
    save_sim_metadata,
    update_single_sim_metadata,
    delete_single_sim_metadata,
    clear_all_sim_metadata,
    load_group_metadata,
    save_group_metadata,
    update_single_group_metadata,
    delete_single_group_metadata,
    DEFAULT_GROUP_DESCRIPTIONS,
    load_active_sessions,
    save_active_sessions,
    update_single_active_session,
    delete_single_active_session,
    load_cached_ues,
    save_cached_ues,
    load_cached_groups,
    save_cached_groups,
    export_demo_pack,
    import_demo_pack,
    get_builtin_scenario_presets,
    load_builtin_scenario,
)
from src.auth import PANWAuthManager
from src.models import TenantUEMapping, UESession
from src.client import Prisma5GClient
from src.debug_logger import api_debug_logger
from src.presets import (
    VERTICALS_CATALOG,
    get_all_verticals,
    get_random_preset,
    generate_transatel_imsi,
    generate_valid_imei,
    generate_fleet_devices,
    enrich_existing_imsis,
)
from src.version import get_version_info

# Project base and config directories
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = get_config_dir()
ENV_PATH = CONFIG_DIR / ".env"

_current_version_info = get_version_info()

app = FastAPI(
    title="Prisma SASE 5G Manager",
    description="Full Lifecycle Management & Demo Portal for Palo Alto Networks Prisma SASE 5G",
    version=_current_version_info["version"],
)

# Enable CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory if it exists
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Serve favicon.ico or favicon.png."""
    ico_path = static_dir / "favicon.ico"
    if ico_path.exists():
        return FileResponse(ico_path, media_type="image/x-icon")
    svg_path = static_dir / "favicon.svg"
    if svg_path.exists():
        return FileResponse(svg_path, media_type="image/svg+xml")
    png_path = static_dir / "favicon.png"
    if png_path.exists():
        return FileResponse(png_path, media_type="image/png")
    return HTMLResponse(status_code=204, content="")


def get_current_client(custom_config: Optional[Config] = None) -> Prisma5GClient:
    """Instantiate a client using current configuration."""
    cfg = custom_config or load_config()
    return Prisma5GClient(cfg)


from src.cidr import (
    DEFAULT_UE_CIDR_BLOCKS,
    parse_cidr_blocks,
    is_ip_in_cidr,
    get_allocatable_ips,
    get_next_available_ip,
)


# -----------------------------------------------------------------------------
# Pydantic Request & Response Models
# -----------------------------------------------------------------------------

class ConfigUpdateModel(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tsg_id: Optional[str] = None
    api_base_url: Optional[str] = "https://api.sase.paloaltonetworks.com"
    default_apn: Optional[str] = "sasetest"
    default_ip_type: Optional[str] = "IPv4"
    ue_cidr_blocks: Optional[str] = "10.56.0.192/27,10.56.0.224/27"


class ConfigTestModel(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    tsg_id: Optional[str] = None
    api_base_url: Optional[str] = "https://api.sase.paloaltonetworks.com"


class CreateUEModel(BaseModel):
    imsi: str
    imei: str
    apn: str = "sasetest"
    tsg_id: Optional[str] = None
    session_ip: Optional[str] = None  # If provided, auto-registers 5G session
    vertical: Optional[str] = None
    device_type: Optional[str] = None
    custom_label: Optional[str] = None
    icon: Optional[str] = None
    group_id: Optional[str] = None


class UpdateUEModel(BaseModel):
    imsi: Optional[str] = None
    imei: Optional[str] = None
    apn: Optional[str] = None
    tsg_id: Optional[str] = None
    group_id: Optional[str] = None  # target group id, or "" / "none" to unassign
    vertical: Optional[str] = None
    device_type: Optional[str] = None
    custom_label: Optional[str] = None
    icon: Optional[str] = None


class CreateGroupModel(BaseModel):
    group_name: str
    description: Optional[str] = None
    tsg_id: Optional[str] = None
    identity_ids: Optional[List[str]] = None


class UpdateGroupModel(BaseModel):
    group_name: Optional[str] = None
    description: Optional[str] = None
    identity_ids: Optional[List[str]] = None
    tsg_id: Optional[str] = None


class AssignGroupModel(BaseModel):
    group_id: Optional[str] = None
    tsg_id: Optional[str] = None


class UpdateUEGroupsModel(BaseModel):
    group_ids: List[str] = Field(default_factory=list, description="Target list of group IDs this SIM should belong to")
    tsg_id: Optional[str] = None


class RegisterSessionModel(BaseModel):
    imsi: str
    imei: str
    apn: str = "sasetest"
    ip_type: str = "IPv4"
    ipv4_addr: str = "10.56.0.195"
    slice_id: Optional[str] = None
    msisdn: Optional[str] = None


class DeregisterSessionModel(BaseModel):
    imsi: str
    imei: str
    apn: str = "sasetest"
    ipv4_addr: str = "10.56.0.195"


class AutoPopulateModel(BaseModel):
    vertical: Optional[str] = "all"  # vertical id or "all"
    count: Optional[int] = 3
    tsg_id: Optional[str] = None
    auto_session: bool = True
    overwrite: bool = True


class EnrichFleetModel(BaseModel):
    vertical: Optional[str] = "all"  # vertical id or "all"
    overwrite: bool = True  # whether to overwrite already enriched SIMs
    tsg_id: Optional[str] = None


class OperationalModeModel(BaseModel):
    standalone_mode: bool = False


class BulkProvisionModel(BaseModel):
    pack_data: Optional[Dict[str, Any]] = None
    attach_sessions: bool = True
    target_tsg_id: Optional[str] = None


# -----------------------------------------------------------------------------
# API Endpoints: System, Operational Mode & Demo Packs
# -----------------------------------------------------------------------------

@app.get("/api/version")
def get_app_version():
    """Get current application version and git build metadata."""
    return get_version_info()


@app.get("/api/changelog")
def get_changelog():
    """Retrieve application changelog markdown."""
    changelog_file = BASE_DIR / "CHANGELOG.md"
    if changelog_file.exists():
        return {"content": changelog_file.read_text(encoding="utf-8")}
    return {"content": "# Changelog\n\nNo changelog available."}


@app.get("/api/status")
def get_system_status():
    """Get system health, authentication state, connected TSG info, and version."""
    v_info = get_version_info()
    try:
        config = load_config()
        has_creds = bool(config.client_id and config.client_secret and config.tsg_id)
        
        token_preview = None
        auth_error = None
        if has_creds and not config.standalone_mode:
            try:
                auth = PANWAuthManager(config)
                token = auth.get_access_token()
                token_preview = f"{token[:8]}...{token[-6:]}" if token else None
            except Exception as e:
                auth_error = str(e)
        elif config.standalone_mode:
            token_preview = "standalone-sandbox"

        return {
            "status": "standalone" if config.standalone_mode else ("healthy" if (has_creds and not auth_error) else "needs_config"),
            "authenticated": bool(token_preview) or config.standalone_mode,
            "auth_error": auth_error if not config.standalone_mode else None,
            "token_preview": token_preview,
            "client_id": config.client_id,
            "tsg_id": config.tsg_id,
            "api_base_url": config.api_base_url,
            "default_apn": config.default_apn,
            "default_ip_type": config.default_ip_type,
            "standalone_mode": bool(config.standalone_mode),
            "version": v_info["version"],
            "version_info": v_info,
        }
    except Exception as exc:
        return {
            "status": "error",
            "authenticated": False,
            "auth_error": str(exc),
            "standalone_mode": False,
            "version": v_info["version"],
            "version_info": v_info,
        }


@app.get("/api/mode")
def get_operational_mode():
    """Get current operational mode (Live SCM Cloud vs Standalone Demo Sandbox)."""
    cfg = load_config()
    return {
        "success": True,
        "standalone_mode": bool(cfg.standalone_mode),
        "mode": "standalone" if cfg.standalone_mode else "live",
        "description": "100% Offline Zero-Latency Demo Sandbox" if cfg.standalone_mode else "Live Strata Cloud Manager API (Default)",
    }


@app.post("/api/mode")
def set_operational_mode(payload: OperationalModeModel):
    """Switch operational mode between Live SCM Cloud (default) and Standalone Demo Sandbox."""
    cfg = load_config()
    cfg.standalone_mode = payload.standalone_mode
    save_config(cfg)
    return {
        "success": True,
        "standalone_mode": cfg.standalone_mode,
        "mode": "standalone" if cfg.standalone_mode else "live",
        "message": f"Operational mode switched to {'Standalone Demo Sandbox (100% Offline)' if cfg.standalone_mode else 'Live SCM Cloud API'}",
    }


@app.get("/api/demo/export")
def export_demo_fleet(scenario_name: Optional[str] = "Prisma SASE 5G Demo Fleet"):
    """Export complete fleet state (SIMs, metadata, sessions, groups) as a portable Demo Pack JSON file."""
    import json
    pack = export_demo_pack(scenario_name=scenario_name or "Prisma SASE 5G Demo Fleet")
    content = json.dumps(pack, indent=2)
    filename = f"prisma_5g_demo_pack_{pack.get('tenant_info', {}).get('default_apn', 'fleet')}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/demo/import")
def import_demo_fleet(payload: Dict[str, Any], push_to_scm: bool = False):
    """Import a Demo Pack JSON into persistent local state, with optional immediate SCM Bulk Provisioning."""
    try:
        # Check if payload wraps pack or is direct pack
        pack_data = payload.get("pack") if ("pack" in payload and isinstance(payload.get("pack"), dict)) else payload
        push_flag = payload.get("push_to_scm", push_to_scm) if isinstance(payload, dict) else push_to_scm
        
        res = import_demo_pack(pack_data)
        
        scm_result = None
        if push_flag:
            try:
                client = get_current_client()
                scm_result = client.bulk_provision_fleet(pack_data, attach_sessions=True)
            except Exception as scm_err:
                scm_result = {"success": False, "error": str(scm_err)}

        return {
            "success": True,
            "data": res,
            "scm_provisioning": scm_result,
            "message": f"Successfully imported demo pack '{res.get('scenario_name')}' with {res.get('sims_count')} SIM(s) and {res.get('active_sessions_count')} active session(s)." + (f" SCM Bulk Sync: {scm_result.get('sims_provisioned_count', 0)} SIM(s) pushed to SCM." if scm_result else ""),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/demo/bulk-provision")
def bulk_provision_to_scm(payload: Optional[BulkProvisionModel] = None):
    """Bulk provision a full demo pack or the active local fleet directly to Strata Cloud Manager."""
    try:
        req = payload or BulkProvisionModel()
        pack = req.pack_data
        if not pack:
            pack = export_demo_pack(scenario_name="Active 5G Fleet Snapshot")
        
        client = get_current_client()
        result = client.bulk_provision_fleet(
            pack_data=pack,
            attach_sessions=req.attach_sessions,
            target_tsg_id=req.target_tsg_id,
        )
        return {
            "success": result.get("success", False),
            "data": result,
            "message": f"SCM Bulk Provisioning complete: {result.get('sims_provisioned_count', 0)} SIM(s) provisioned, {result.get('groups_configured_count', 0)} group(s) synchronized, {result.get('sessions_attached_count', 0)} session(s) attached.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/demo/presets")
def list_demo_presets():
    """List built-in scenario presets (Retail, Industry 4.0, EV Hub)."""
    return {
        "success": True,
        "presets": get_builtin_scenario_presets(),
    }


@app.post("/api/demo/presets/load/{preset_id}")
def load_demo_preset(preset_id: str):
    """Instantly load and activate a built-in demo scenario preset."""
    try:
        res = load_builtin_scenario(preset_id)
        return {
            "success": True,
            "data": res,
            "message": f"Successfully loaded '{res.get('scenario_name')}' with {res.get('sims_count')} SIM cards.",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/config")
def get_app_config():
    """Get current configuration with masked client secret for the Settings UI."""
    try:
        cfg = load_config()
        secret_masked = None
        if cfg.client_secret:
            secret_masked = f"••••••••{cfg.client_secret[-4:]}" if len(cfg.client_secret) >= 4 else "••••••••"

        json_file = CONFIG_DIR / "config.json"
        env_file = CONFIG_DIR / ".env"
        root_env = BASE_DIR / ".env"
        config_exists = json_file.exists() or env_file.exists() or root_env.exists()

        return {
            "client_id": cfg.client_id or "",
            "has_secret": bool(cfg.client_secret),
            "secret_masked": secret_masked,
            "tsg_id": cfg.tsg_id or "",
            "api_base_url": cfg.api_base_url,
            "default_apn": cfg.default_apn,
            "default_ip_type": cfg.default_ip_type,
            "ue_cidr_blocks": cfg.ue_cidr_blocks or DEFAULT_UE_CIDR_BLOCKS,
            "config_dir": str(CONFIG_DIR),
            "config_file_exists": config_exists,
            "json_exists": json_file.exists(),
            "env_file_exists": config_exists,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/config")
def update_app_config(payload: ConfigUpdateModel):
    """Update persistent JSON and .env configuration files securely from the Settings UI."""
    try:
        current_cfg = load_config()
        
        # Keep existing secret if empty/not provided
        new_secret = payload.client_secret if (payload.client_secret and payload.client_secret.strip()) else current_cfg.client_secret
        new_client_id = payload.client_id if payload.client_id is not None else current_cfg.client_id
        new_tsg_id = payload.tsg_id if payload.tsg_id is not None else current_cfg.tsg_id
        new_api_base = payload.api_base_url or "https://api.sase.paloaltonetworks.com"
        new_apn = payload.default_apn or "sasetest"
        new_ip_type = payload.default_ip_type or "IPv4"
        new_cidr = payload.ue_cidr_blocks.strip() if payload.ue_cidr_blocks else current_cfg.ue_cidr_blocks

        save_result = save_config(
            Config(
                client_id=new_client_id,
                client_secret=new_secret,
                tsg_id=new_tsg_id,
                api_base_url=new_api_base,
                default_apn=new_apn,
                default_ip_type=new_ip_type,
                ue_cidr_blocks=new_cidr,
                standalone_mode=current_cfg.standalone_mode,
            ),
            target_dir=CONFIG_DIR,
            save_env_backup=True,
        )

        return {
            "success": True,
            "message": "Configuration saved to persistent config/config.json and .env successfully",
            "details": save_result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {exc}")


@app.get("/api/cidr/info")
def get_cidr_info():
    """Get active UE CIDR blocks, allocatable IPs, and next suggested IP."""
    try:
        cfg = load_config()
        active_sess = load_active_sessions()
        used_ips = {s.get("ipv4_addr") for s in active_sess.values() if s.get("ipv4_addr")}
        allocatable = get_allocatable_ips(cfg.ue_cidr_blocks, limit=100)
        next_ip = get_next_available_ip(cfg.ue_cidr_blocks, used_ips)
        return {
            "success": True,
            "configured_cidrs": cfg.ue_cidr_blocks,
            "ue_cidr_blocks": cfg.ue_cidr_blocks,
            "total_allocatable": len(allocatable),
            "allocatable_count": len(allocatable),
            "allocatable_ips": allocatable,
            "next_available_ip": next_ip,
            "used_ips": list(used_ips),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@app.get("/api/cidr/validate")
def validate_ip_cidr(ip: str):
    """Validate if an IP is within the configured UE CIDR blocks."""
    cfg = load_config()
    valid = is_ip_in_cidr(ip, cfg.ue_cidr_blocks)
    return {
        "success": True,
        "ip": ip,
        "valid": valid,
        "is_valid": valid,
        "configured_cidrs": cfg.ue_cidr_blocks,
        "ue_cidr_blocks": cfg.ue_cidr_blocks,
        "message": f"IP {ip} is {'valid within' if valid else 'OUTSIDE'} configured CIDR block(s) ({cfg.ue_cidr_blocks})"
    }


@app.post("/api/config/test")
def test_app_config(payload: ConfigTestModel):
    """Test OAuth2 credentials and connectivity against PANW endpoints."""
    current_cfg = load_config()
    
    effective_secret = payload.client_secret.strip() if (payload.client_secret and payload.client_secret.strip()) else current_cfg.client_secret
    effective_client_id = payload.client_id.strip() if (payload.client_id and payload.client_id.strip()) else current_cfg.client_id
    effective_tsg_id = payload.tsg_id.strip() if (payload.tsg_id and payload.tsg_id.strip()) else current_cfg.tsg_id
    effective_api_base = payload.api_base_url or current_cfg.api_base_url or "https://api.sase.paloaltonetworks.com"

    test_cfg = Config(
        client_id=effective_client_id,
        client_secret=effective_secret,
        tsg_id=effective_tsg_id,
        api_base_url=effective_api_base,
    )
    try:
        auth = PANWAuthManager(test_cfg)
        token = auth.get_access_token()
        
        # Test basic hierarchy query
        client = Prisma5GClient(test_cfg)
        tenants = client.list_tenants(effective_tsg_id)

        return {
            "success": True,
            "message": "Authentication and API connectivity verified successfully!",
            "token_preview": f"{token[:8]}...{token[-6:]}",
            "tenants_count": len(tenants),
            "tenants": tenants,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# -----------------------------------------------------------------------------
# API Endpoints: Tenants & Hierarchy
# -----------------------------------------------------------------------------

@app.get("/api/tenants")
def list_tenants():
    """Get discovered Tenant Service Groups (Root MSP and Child Tenants)."""
    try:
        client = get_current_client()
        tenants = client.list_tenants()
        return {
            "success": True,
            "count": len(tenants),
            "data": tenants,
            "fallback": False,
        }
    except Exception as exc:
        config = load_config()
        root_id = config.tsg_id or "1965438697"
        fallback_tenants = [
            {"tsg_id": root_id, "tsg_name": "SP-5G-POC2-Transatel", "hierarchy_level": "Root MSP"},
            {"tsg_id": "1291887562", "tsg_name": "Transatel demo", "hierarchy_level": "Child Tenant"}
        ]
        return {
            "success": True,
            "count": len(fallback_tenants),
            "data": fallback_tenants,
            "fallback": True,
            "source": "offline_cache",
        }


# -----------------------------------------------------------------------------
# API Endpoints: Presets & Vertical Metadata (Enterprise IoT Fleet Demo)
# -----------------------------------------------------------------------------

@app.get("/api/presets/verticals")
def get_vertical_presets():
    """Get list of all supported industry verticals, icons, and typical equipment presets."""
    return {
        "success": True,
        "data": get_all_verticals(),
    }


@app.get("/api/presets/random")
def get_random_sim_preset(vertical_id: Optional[str] = None):
    """Generate a realistic SIM preset with 3GPP-compliant IMSI/IMEI for a vertical."""
    return {
        "success": True,
        "data": get_random_preset(vertical_id),
    }


@app.post("/api/metadata/clear")
def clear_metadata():
    """Clear all local SIM metadata (Cleanup / Raw SCM Reset mode)."""
    clear_all_sim_metadata()
    return {
        "success": True,
        "message": "All local SIM business metadata cleared successfully (Raw SCM mode)",
    }


@app.post("/api/presets/enrich")
@app.post("/api/presets/populate")
def auto_enrich_existing_fleet(payload: EnrichFleetModel):
    """
    Enrich existing SIM cards already registered in SCM with realistic industry vertical metadata
    (replaces generic '5G Connected Device' with realistic equipment types, icons, and demo labels).
    """
    try:
        client = get_current_client()
        resp = client.list_tenant_ues(tsg_id=payload.tsg_id)
        models = resp.get("models", [])
        
        if not models:
            return {
                "success": True,
                "count": 0,
                "message": "No existing SIMs found in SCM inventory to enrich.",
                "data": [],
            }

        existing_imsis = [str(m.imsi) for m in models if m.imsi]
        local_meta = load_sim_metadata()
        
        # Filter if not overwriting
        imsis_to_enrich = [imsi for imsi in existing_imsis if payload.overwrite or imsi not in local_meta]
        
        enrichment_map = enrich_existing_imsis(imsis_to_enrich, vertical_id=payload.vertical)
        
        for imsi, meta_dict in enrichment_map.items():
            existing_meta = local_meta.get(imsi, {})
            # Preserve existing custom_label (Demo Memo / Device tag) and last_ip
            if existing_meta.get("custom_label"):
                meta_dict["custom_label"] = existing_meta["custom_label"]
            if existing_meta.get("last_ip"):
                meta_dict["last_ip"] = existing_meta["last_ip"]
            update_single_sim_metadata(imsi, meta_dict)

        return {
            "success": True,
            "count": len(enrichment_map),
            "message": f"Successfully enriched {len(enrichment_map)} existing SIM(s) with industry metadata.",
            "data": [
                {"imsi": imsi, **meta_dict}
                for imsi, meta_dict in enrichment_map.items()
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))




# -----------------------------------------------------------------------------
# API Endpoints: SIM Cards / UEs
# -----------------------------------------------------------------------------

def synthesize_fallback_ues(tsg_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Synthesize complete resilient SIM list from local session & metadata caches when SCM is unreachable."""
    local_meta = load_sim_metadata()
    active_sess = load_active_sessions()
    cached = load_cached_ues()
    if cached:
        res = []
        for c in cached:
            imsi_str = str(c.get("imsi", ""))
            sess = active_sess.get(imsi_str)
            meta = local_meta.get(imsi_str, {})
            ipv4 = sess.get("ipv4_addr") if sess else c.get("ipv4_addr")
            status = sess.get("status") if sess else c.get("status", "Active" if ipv4 else "Inactive")
            item = dict(c)
            item["ipv4_addr"] = ipv4
            item["status"] = status
            item["last_ip"] = meta.get("last_ip") or ipv4 or item.get("last_ip")
            if meta.get("custom_label") is not None:
                item["custom_label"] = meta.get("custom_label")
            if meta.get("device_type"):
                item["device_type"] = meta.get("device_type")
            if meta.get("vertical"):
                item["vertical"] = meta.get("vertical")
            if meta.get("icon"):
                item["icon"] = meta.get("icon")
            res.append(item)
        return res

    res_data = []
    seen = set()
    for imsi, sess in active_sess.items():
        imsi_str = str(imsi)
        seen.add(imsi_str)
        meta = local_meta.get(imsi_str, {})
        dev_type = meta.get("device_type") or "Generic 5G Device"
        
        if "Scanner" in dev_type:
            grp = ["IT-engineering"]
        elif any(k in dev_type for k in ["Smart", "RFID", "Player", "Kiosk", "POS"]):
            grp = ["IoT-Smart-Sensors"]
        else:
            grp = ["Permissive"]

        res_data.append({
            "identity_id": f"id_{imsi_str}",
            "imsi": imsi_str,
            "imei": sess.get("imei") or meta.get("imei") or "350000000000000",
            "apn": sess.get("apn") or "sasetest",
            "tsg_id": tsg_id or "1291887562",
            "root_tsg_id": "1965438697",
            "tenant_name": "Transatel demo",
            "groups": grp,
            "ipv4_addr": sess.get("ipv4_addr"),
            "ipv6_addr": None,
            "status": sess.get("status", "Active"),
            "region": sess.get("region", "europe-west9"),
            "tenant_status": "Yes",
            "create_time": "2026-09-13T20:00:00Z",
            "vertical": meta.get("vertical", "retail"),
            "device_type": dev_type,
            "custom_label": meta.get("custom_label", ""),
            "icon": meta.get("icon", "credit-card"),
            "last_ip": sess.get("ipv4_addr") or meta.get("last_ip"),
        })

    for imsi, meta in local_meta.items():
        imsi_str = str(imsi)
        if imsi_str not in seen:
            seen.add(imsi_str)
            res_data.append({
                "identity_id": f"id_{imsi_str}",
                "imsi": imsi_str,
                "imei": meta.get("imei") or "350000000000000",
                "apn": "sase",
                "tsg_id": tsg_id or "1291887562",
                "root_tsg_id": "1965438697",
                "tenant_name": "Transatel demo",
                "groups": ["Restrictive"],
                "ipv4_addr": None,
                "ipv6_addr": None,
                "status": "Inactive",
                "region": "europe-west9",
                "tenant_status": "No",
                "create_time": "2026-09-13T20:00:00Z",
                "vertical": meta.get("vertical", "retail"),
                "device_type": meta.get("device_type", "Generic 5G Device"),
                "custom_label": meta.get("custom_label", ""),
                "icon": meta.get("icon", "credit-card"),
                "last_ip": meta.get("last_ip"),
            })

    save_cached_ues(res_data)
    return res_data


@app.get("/api/ues")
def list_ues(tsg_id: Optional[str] = None):
    """List registered SIM cards (UE mappings) enriched with local business metadata."""
    local_meta = load_sim_metadata()
    active_sess = load_active_sessions()
    try:
        client = get_current_client()
        resp = client.list_tenant_ues(tsg_id=tsg_id)
        
        items = resp.get("data", [])
        models = resp.get("models", [])
        
        if not models:
            fallback_data = synthesize_fallback_ues(tsg_id=tsg_id)
            return {
                "success": True,
                "total_items": len(fallback_data),
                "data": fallback_data,
                "fallback": True,
                "source": "offline_cache",
                "cloud_status": "503_or_empty",
            }

        # Convert models to rich json list
        res_data = []
        for m in models:
            imsi_str = str(m.imsi)
            imei_str = str(m.imei) if m.imei else ""
            sess_info = active_sess.get(imsi_str) or (active_sess.get(imei_str) if imei_str else None)
            ipv4 = m.ipv4_addr or (sess_info["ipv4_addr"] if sess_info else None)
            status = m.status if (m.ipv4_addr and m.status) else (sess_info["status"] if sess_info else ("Active" if ipv4 else "Inactive"))
            region = m.region or (sess_info["region"] if sess_info else ("europe-west9" if status == "Active" else None))
            tenant_status = "Yes" if status == "Active" else (m.tenant_status or "No")
            
            meta = local_meta.get(imsi_str, {})

            res_data.append({
                "identity_id": m.identity_id,
                "imsi": m.imsi,
                "imei": m.imei,
                "apn": m.apn,
                "tsg_id": m.tsg_id,
                "root_tsg_id": m.root_tsg_id,
                "tenant_name": m.tenant_name,
                "groups": m.groups or [],
                "ipv4_addr": ipv4,
                "ipv6_addr": m.ipv6_addr,
                "status": status,
                "region": region,
                "tenant_status": tenant_status,
                "create_time": m.create_time,
                "vertical": meta.get("vertical"),
                "device_type": meta.get("device_type"),
                "custom_label": meta.get("custom_label"),
                "icon": meta.get("icon"),
                "last_ip": meta.get("last_ip") or ipv4 or (sess_info.get("ipv4_addr") if sess_info else None),
            })

        save_cached_ues(res_data)
        return {
            "success": True,
            "total_items": resp.get("totalItems", len(res_data)),
            "data": res_data,
            "fallback": False,
        }
    except Exception as exc:
        fallback_data = synthesize_fallback_ues(tsg_id=tsg_id)
        return {
            "success": True,
            "total_items": len(fallback_data),
            "data": fallback_data,
            "fallback": True,
            "source": "offline_cache",
            "cloud_status": "503_upstream_unavailable",
            "cloud_error": str(exc),
        }


@app.post("/api/ues")
def create_ue(payload: CreateUEModel):
    """Register a new SIM card (UE mapping) with optional 5G session attach and business metadata."""
    try:
        clean_imsi = str(payload.imsi).strip()
        clean_imei = str(payload.imei).strip()
        if len(clean_imsi) != 15 or not clean_imsi.isdigit():
            raise HTTPException(status_code=400, detail=f"IMSI must be exactly 15 digits (received {len(clean_imsi)} digits: '{clean_imsi}')")
        if len(clean_imei) != 15 or not clean_imei.isdigit():
            raise HTTPException(status_code=400, detail=f"IMEI must be exactly 15 digits (received {len(clean_imei)} digits: '{clean_imei}')")

        client = get_current_client()
        
        # 1. Register SIM mapping in SCM
        create_resp = client.create_tenant_ue(
            imsi=clean_imsi,
            imei=clean_imei,
            apn=payload.apn,
            tsg_id=payload.tsg_id,
        )
        data_obj = create_resp.get("data", {})
        created_id = data_obj.get("id") or data_obj.get("identity_id")

        # 2. Save local business metadata (vertical, device type, custom memo label, icon)
        meta_dict = {}
        if payload.vertical:
            meta_dict["vertical"] = payload.vertical
        if payload.device_type:
            meta_dict["device_type"] = payload.device_type
        if payload.custom_label:
            meta_dict["custom_label"] = payload.custom_label
        if payload.icon:
            meta_dict["icon"] = payload.icon
            
        if meta_dict:
            update_single_sim_metadata(str(payload.imsi), meta_dict)

        # 3. If group_id is provided, assign the SIM to the group immediately
        group_assign_result = None
        if payload.group_id and created_id:
            try:
                group_assign_result = client.assign_ue_to_group(
                    ue_identity_id=created_id,
                    target_group_id=payload.group_id,
                    tsg_id=payload.tsg_id,
                )
            except Exception as g_err:
                group_assign_result = {"error": str(g_err)}

        session_result = None
        # 4. If session_ip provided, auto-register 5G session telemetry
        if payload.session_ip:
            try:
                sess = UESession(
                    imsi=payload.imsi,
                    imei=payload.imei,
                    apn=payload.apn,
                    ip_type="IPv4",
                    ipv4_addr=payload.session_ip,
                )
                sess_resp = client.register_ue_session(sess)
                update_single_sim_metadata(str(payload.imsi), {"last_ip": payload.session_ip})
                update_single_active_session(str(payload.imsi), {
                    "ipv4_addr": payload.session_ip,
                    "imei": payload.imei,
                    "apn": payload.apn,
                    "status": "Active",
                    "region": "europe-west9",
                    "tenant_status": "Yes",
                })
                session_result = {
                    "registered": True,
                    "status_code": sess_resp.get("status_code"),
                    "ip": payload.session_ip,
                }
            except Exception as s_exc:
                session_result = {
                    "registered": False,
                    "error": str(s_exc),
                }

        return {
            "success": True,
            "identity_id": created_id,
            "data": data_obj,
            "group_assignment": group_assign_result,
            "session_result": session_result,
            "message": f"SIM {payload.imsi} registered successfully with APN '{payload.apn}'",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/api/ues/{identity_id}")
def update_ue(identity_id: str, payload: UpdateUEModel):
    """Update SIM card hardware mapping details (IMSI, IMEI, APN), metadata, and/or group assignment."""
    try:
        client = get_current_client()
        
        # 1. Update basic SIM mapping in SCM if hardware fields changed
        update_res = None
        if payload.imsi or payload.imei or payload.apn:
            update_res = client.update_tenant_ue(
                identity_id=identity_id,
                imsi=payload.imsi,
                imei=payload.imei,
                apn=payload.apn,
                tsg_id=payload.tsg_id,
            )

        # 2. Update local business metadata if provided
        meta_dict = {}
        if payload.vertical is not None:
            meta_dict["vertical"] = payload.vertical
        if payload.device_type is not None:
            meta_dict["device_type"] = payload.device_type
        if payload.custom_label is not None:
            meta_dict["custom_label"] = payload.custom_label
        if payload.icon is not None:
            meta_dict["icon"] = payload.icon

        target_imsi = payload.imsi
        if not target_imsi:
            # Look up IMSI from SCM or existing list
            try:
                ue_obj = client.get_tenant_ue(identity_id)
                target_imsi = ue_obj.get("imsi") if isinstance(ue_obj, dict) else getattr(ue_obj, "imsi", None)
            except Exception:
                pass

        if target_imsi and meta_dict:
            update_single_sim_metadata(str(target_imsi), meta_dict)

        # 3. Update group assignment if group_id field is specified
        group_res = None
        if payload.group_id is not None:
            target_gid = payload.group_id.strip()
            if target_gid.lower() in ("none", "", "null"):
                target_gid = None
            group_res = client.assign_ue_to_group(
                ue_identity_id=identity_id,
                target_group_id=target_gid,
                tsg_id=payload.tsg_id,
            )

        return {
            "success": True,
            "identity_id": identity_id,
            "data": update_res,
            "group_assignment": group_res,
            "message": f"SIM {identity_id} updated successfully",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/api/ues/{identity_id}/group")
def assign_ue_group(identity_id: str, payload: AssignGroupModel):
    """Assign or move a SIM card to a specific subscriber user group."""
    try:
        client = get_current_client()
        target_gid = payload.group_id.strip() if payload.group_id else None
        if target_gid and target_gid.lower() in ("none", "null", ""):
            target_gid = None

        res = client.assign_ue_to_group(
            ue_identity_id=identity_id,
            target_group_id=target_gid,
            tsg_id=payload.tsg_id,
        )
        return {
            "success": True,
            "identity_id": identity_id,
            "data": res,
            "message": f"SIM {identity_id} group membership updated",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/api/ues/{identity_id}/groups")
def set_ue_groups(identity_id: str, payload: UpdateUEGroupsModel):
    """Set the exact list of subscriber groups a SIM belongs to, adding/removing as needed."""
    try:
        client = get_current_client()
        target_group_ids = set(payload.group_ids or [])

        # Query all groups for the TSG
        groups_resp = client.list_user_groups(tsg_id=payload.tsg_id)
        all_groups = groups_resp.get("models", [])

        changes = []
        for g in all_groups:
            gid = str(g.group_id)
            if not gid:
                continue

            # Fetch current members
            try:
                g_detail = client.get_user_group(gid)
                d_arr = g_detail.get("data", [])
                g_data = d_arr[0] if d_arr and isinstance(d_arr, list) else g_detail.get("data", {})
                current_members = list(g_data.get("identity_id") or [])
                g_name = g_data.get("group_name") or g.name
                g_tsg = g_data.get("tsg_id") or g.tsg_id
            except Exception:
                current_members = list(g.identity_ids or [])
                g_name = g.name
                g_tsg = g.tsg_id

            should_be_member = gid in target_group_ids or (g_name and g_name.lower() in [x.lower() for x in target_group_ids])
            is_current_member = identity_id in current_members

            if should_be_member and not is_current_member:
                current_members.append(identity_id)
                res = client.update_user_group(
                    group_id=gid,
                    group_name=g_name,
                    identity_ids=current_members,
                    tsg_id=g_tsg,
                )
                changes.append({"group_id": gid, "action": "added", "result": res})
            elif not should_be_member and is_current_member:
                current_members = [i for i in current_members if i != identity_id]
                res = client.update_user_group(
                    group_id=gid,
                    group_name=g_name,
                    identity_ids=current_members,
                    tsg_id=g_tsg,
                )
                changes.append({"group_id": gid, "action": "removed", "result": res})

        return {
            "success": True,
            "identity_id": identity_id,
            "target_groups": list(target_group_ids),
            "changes": changes,
            "message": f"Updated group memberships for SIM {identity_id}"
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/ues/{identity_id}")
def delete_ue(identity_id: str, imsi: Optional[str] = None):
    """Safely delete a SIM card mapping by identity ID and clean up local metadata."""
    try:
        client = get_current_client()
        
        # If imsi not provided directly, try to get it
        if not imsi:
            try:
                ue_obj = client.get_tenant_ue(identity_id)
                imsi = ue_obj.get("imsi") if isinstance(ue_obj, dict) else getattr(ue_obj, "imsi", None)
            except Exception:
                pass

        resp = client.delete_tenant_ue(identity_id)
        if imsi:
            delete_single_sim_metadata(str(imsi))
            delete_single_active_session(str(imsi))
            
        return {
            "success": True,
            "identity_id": identity_id,
            "data": resp,
            "message": f"SIM {identity_id} deleted successfully",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -----------------------------------------------------------------------------
# API Endpoints: Subscriber User Groups
# -----------------------------------------------------------------------------

def synthesize_fallback_groups(tsg_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Synthesize complete resilient group list when SCM is unreachable."""
    cached = load_cached_groups()
    if cached:
        return cached

    group_meta = load_group_metadata()
    default_groups = [
        {
            "group_id": "iot-smart-sensors",
            "name": "IoT-Smart-Sensors",
            "raw_name": "IoT-Smart-Sensors",
            "description": group_meta.get("iot-smart-sensors", {}).get("description") or "Dedicated zero-trust profile for smart metering nodes and grid sensors with low bandwidth and strict egress rules.",
            "tsg_id": tsg_id or "1965438697",
            "tenant_name": "Transatel demo",
            "user_count": 6,
            "identity_ids": ["901370007299136", "901370007299147", "901370007299138", "208956167163949", "208950391678715"]
        },
        {
            "group_id": "it-engineering",
            "name": "IT-engineering",
            "raw_name": "IT-engineering",
            "description": group_meta.get("it-engineering", {}).get("description") or "Engineering diagnostics, remote SSH / telemetry tunnels, and enterprise device maintenance.",
            "tsg_id": tsg_id or "1965438697",
            "tenant_name": "Transatel demo",
            "user_count": 2,
            "identity_ids": ["208956993452553", "901370007299137"]
        },
        {
            "group_id": "permissive",
            "name": "Permissive",
            "raw_name": "Permissive",
            "description": group_meta.get("permissive", {}).get("description") or "Standard corporate / fleet profile. Permissive access allowing broad cloud connectivity, diagnostics, and standard enterprise applications.",
            "tsg_id": tsg_id or "1965438697",
            "tenant_name": "Transatel demo",
            "user_count": 2,
            "identity_ids": ["208954273357404", "208950999999999"]
        },
        {
            "group_id": "restrictive",
            "name": "Restrictive",
            "raw_name": "Restrictive",
            "description": group_meta.get("restrictive", {}).get("description") or "Strictly isolated IoT telemetry profile. High-security zero-trust policy blocking unauthorized external egress and non-industrial traffic.",
            "tsg_id": tsg_id or "1965438697",
            "tenant_name": "Transatel demo",
            "user_count": 4,
            "identity_ids": ["901370001420683", "901370001420693", "901370001420692", "901370001420700", "901370001420701"]
        }
    ]
    save_cached_groups(default_groups)
    return default_groups


@app.get("/api/groups")
def list_groups(tsg_id: Optional[str] = None):
    """List 5G subscriber user groups (e.g. Permissive, Restrictive) enriched with metadata."""
    group_meta = load_group_metadata()
    try:
        client = get_current_client()
        resp = client.list_user_groups(tsg_id=tsg_id)
        models = resp.get("models", [])
        
        if not models:
            fallback_groups = synthesize_fallback_groups(tsg_id=tsg_id)
            return {
                "success": True,
                "count": len(fallback_groups),
                "data": fallback_groups,
                "fallback": True,
                "source": "offline_cache",
                "cloud_status": "503_or_empty",
            }

        group_list = []
        for g in models:
            gid = str(g.group_id or "")
            gname = str(g.name or "")
            meta = group_meta.get(gid) or group_meta.get(gname.lower()) or group_meta.get(gname) or {}

            desc = meta.get("description") or g.description
            if not desc:
                desc = DEFAULT_GROUP_DESCRIPTIONS.get(gname.lower(), "5G Zero-Trust subscriber group policy profile")

            custom_name = meta.get("name") or g.name

            group_list.append({
                "group_id": g.group_id,
                "name": custom_name,
                "raw_name": g.name,
                "description": desc,
                "tsg_id": g.tsg_id,
                "tenant_name": g.tenant_name,
                "user_count": g.user_count,
                "identity_ids": g.identity_ids or [],
            })
        save_cached_groups(group_list)
        return {
            "success": True,
            "count": len(group_list),
            "data": group_list,
            "fallback": False,
        }
    except Exception as exc:
        fallback_groups = synthesize_fallback_groups(tsg_id=tsg_id)
        return {
            "success": True,
            "count": len(fallback_groups),
            "data": fallback_groups,
            "fallback": True,
            "source": "offline_cache",
            "cloud_status": "503_upstream_unavailable",
            "cloud_error": str(exc),
        }


@app.post("/api/groups")
def create_group(payload: CreateGroupModel):
    """Create a new 5G subscriber identity group in Strata Cloud Manager."""
    try:
        client = get_current_client()
        resp = client.create_user_group(
            group_name=payload.group_name,
            tsg_id=payload.tsg_id,
            identity_ids=payload.identity_ids or [],
        )
        new_id = resp.get("id") or resp.get("group_id") or resp.get("data", {}).get("id")
        if payload.description:
            key = str(new_id) if new_id else payload.group_name.lower()
            update_single_group_metadata(key, {"description": payload.description, "name": payload.group_name})
            if new_id and payload.group_name:
                update_single_group_metadata(payload.group_name.lower(), {"description": payload.description, "name": payload.group_name})

        return {
            "success": True,
            "data": resp,
            "message": f"Group '{payload.group_name}' created successfully",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/groups/{group_id}")
def get_group(group_id: str):
    """Get details and member identity IDs for a specific 5G user group."""
    try:
        client = get_current_client()
        resp = client.get_user_group(group_id)
        return {
            "success": True,
            "data": resp,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/api/groups/{group_id}")
def update_group(group_id: str, payload: UpdateGroupModel):
    """Update a 5G user group's name, description, and/or member identity list."""
    try:
        client = get_current_client()
        resp = client.update_user_group(
            group_id=group_id,
            group_name=payload.group_name,
            identity_ids=payload.identity_ids,
            tsg_id=payload.tsg_id,
        )

        meta_updates = {}
        if payload.description is not None:
            meta_updates["description"] = payload.description
        if payload.group_name is not None:
            meta_updates["name"] = payload.group_name

        if meta_updates:
            update_single_group_metadata(str(group_id), meta_updates)
            if payload.group_name:
                update_single_group_metadata(payload.group_name.lower(), meta_updates)

        return {
            "success": True,
            "data": resp or {"status": "success", "group_id": group_id},
            "message": f"Group '{payload.group_name or group_id}' updated successfully",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/groups/{group_id}")
def delete_group(group_id: str):
    """Delete a 5G subscriber user group from Strata Cloud Manager."""
    try:
        client = get_current_client()
        resp = client.delete_user_group(group_id)
        delete_single_group_metadata(str(group_id))
        return {
            "success": True,
            "group_id": group_id,
            "data": resp,
            "message": f"Group '{group_id}' deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))





# -----------------------------------------------------------------------------
# API Endpoints: 5G Session Telemetry (Registration & Termination)
# -----------------------------------------------------------------------------

@app.post("/api/sessions/register")
def register_session(payload: RegisterSessionModel):
    """Register real-time 5G session telemetry (IP allocation)."""
    try:
        cfg = load_config()
        if payload.ipv4_addr and not is_ip_in_cidr(payload.ipv4_addr, cfg.ue_cidr_blocks):
            raise HTTPException(
                status_code=400,
                detail=f"IP {payload.ipv4_addr} is not within any configured UE CIDR block ({cfg.ue_cidr_blocks}). Please allocate an IP inside the configured CIDR range."
            )

        client = get_current_client()
        session = UESession(
            imsi=payload.imsi,
            imei=payload.imei,
            apn=payload.apn,
            ip_type=payload.ip_type,
            ipv4_addr=payload.ipv4_addr,
            slice_id=payload.slice_id,
            msisdn=payload.msisdn,
        )
        try:
            resp = client.register_ue_session(session)
        except Exception as api_err:
            resp = {"status_code": 200, "data": {"status": "Simulated Session Attached (Offline Snapshot Resilience)"}, "fallback": True}

        if payload.ipv4_addr:
            update_single_sim_metadata(str(payload.imsi), {"last_ip": payload.ipv4_addr})
        update_single_active_session(str(payload.imsi), {
            "ipv4_addr": payload.ipv4_addr,
            "imei": payload.imei,
            "apn": payload.apn,
            "status": "Active",
            "region": "europe-west9",
            "tenant_status": "Yes",
        })
        return {
            "success": True,
            "status_code": resp.get("status_code", 200),
            "data": resp.get("data"),
            "message": f"5G Session registered for IMSI {payload.imsi} with IP {payload.ipv4_addr}",
            "fallback": resp.get("fallback", False),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/sessions/deregister")
def deregister_session(payload: DeregisterSessionModel):
    """Terminate / deregister real-time 5G subscriber session."""
    try:
        client = get_current_client()
        session = UESession(
            imsi=payload.imsi,
            imei=payload.imei,
            apn=payload.apn,
            ip_type="IPv4",
            ipv4_addr=payload.ipv4_addr,
        )
        try:
            resp = client.deregister_ue_session(session)
        except Exception as api_err:
            resp = {"status_code": 200, "data": {"status": "Simulated Session Detached (Offline Snapshot Resilience)"}, "fallback": True}

        if payload.ipv4_addr:
            update_single_sim_metadata(str(payload.imsi), {"last_ip": payload.ipv4_addr})
        delete_single_active_session(str(payload.imsi))
        return {
            "success": True,
            "status_code": resp.get("status_code", 200),
            "data": resp.get("data"),
            "message": f"5G Session terminated for IMSI {payload.imsi} on IP {payload.ipv4_addr}",
            "fallback": resp.get("fallback", False),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# -----------------------------------------------------------------------------
# API Endpoints: Full Lifecycle Test Runner
# -----------------------------------------------------------------------------

@app.post("/api/lifecycle/run")
def run_lifecycle():
    """Execute the full 8-step lifecycle test and return complete results."""
    steps_log = []
    start_time = time.time()
    
    def log_step(step_num: int, title: str, status: str, details: str, duration_ms: int = 0):
        steps_log.append({
            "step": step_num,
            "title": title,
            "status": status,  # "success", "warning", "error"
            "details": details,
            "duration_ms": duration_ms,
        })

    config = load_config()
    client = Prisma5GClient(config)

    # Step 1: Config & Auth
    s1_start = time.time()
    try:
        token = client.auth.get_access_token()
        log_step(1, "Authentication & Configuration", "success", 
                 f"Acquired OAuth2 token ({token[:8]}...) for TSG {config.tsg_id} on {config.api_base_url}",
                 int((time.time() - s1_start) * 1000))
    except Exception as exc:
        log_step(1, "Authentication & Configuration", "error", str(exc))
        return {"success": False, "steps": steps_log, "total_duration_ms": int((time.time() - start_time) * 1000)}

    # Step 2: Read Info & Hierarchy
    s2_start = time.time()
    child_tsg_id = None
    try:
        tenants = client.list_tenants()
        for t in tenants:
            if t.get("parent_id") and not child_tsg_id:
                child_tsg_id = str(t.get("id"))
        
        ues = client.list_tenant_ues()
        groups = client.list_user_groups()
        log_step(2, "Read Tenant Info & Inventory", "success",
                 f"Discovered {len(tenants)} tenants, {ues.get('totalItems', 0)} registered SIMs, {len(groups.get('models', []))} user groups.",
                 int((time.time() - s2_start) * 1000))
    except Exception as exc:
        log_step(2, "Read Tenant Info & Inventory", "warning", f"Notice during inventory read: {exc}")

    # Step 3: Create Test SIM
    s3_start = time.time()
    random_suffix = f"{random.randint(100000000, 999999999)}"
    test_imsi = f"208950{random_suffix}"
    test_imei = f"860123{random_suffix}"
    test_apn = config.default_apn or "sasetest"
    created_id = None

    try:
        create_resp = client.create_tenant_ue(
            imsi=test_imsi,
            imei=test_imei,
            apn=test_apn,
            tsg_id=child_tsg_id,
        )
        data_obj = create_resp.get("data", {})
        created_id = data_obj.get("id") or data_obj.get("identity_id")
        log_step(3, "Register Test SIM (UE)", "success",
                 f"Created Test SIM (IMSI: {test_imsi}, APN: {test_apn}, ID: {created_id}) in TSG {child_tsg_id or config.tsg_id}",
                 int((time.time() - s3_start) * 1000))
    except Exception as exc:
        log_step(3, "Register Test SIM (UE)", "error", str(exc))
        return {"success": False, "steps": steps_log, "total_duration_ms": int((time.time() - start_time) * 1000)}

    # Step 4: Verify test SIM exists
    s4_start = time.time()
    try:
        time.sleep(1)
        if created_id:
            client.get_tenant_ue(created_id)
        log_step(4, "Verify SIM in Control Plane", "success",
                 f"Confirmed test SIM {created_id} is active and indexed.",
                 int((time.time() - s4_start) * 1000))
    except Exception as exc:
        log_step(4, "Verify SIM in Control Plane", "warning", f"Eventual consistency notice: {exc}")

    # Step 5: 5G Session Registration
    s5_start = time.time()
    session = UESession(
        imsi=test_imsi,
        imei=test_imei,
        apn=test_apn,
        ip_type="IPv4",
        ipv4_addr="10.56.0.195",
    )
    try:
        sess_resp = client.register_ue_session(session)
        log_step(5, "Register 5G Subscriber Session", "success",
                 f"Session telemetry enriched with IP 10.56.0.195 (HTTP {sess_resp.get('status_code')})",
                 int((time.time() - s5_start) * 1000))
    except Exception as exc:
        log_step(5, "Register 5G Subscriber Session", "warning", f"Session telemetry notice: {exc}")

    # Step 6: 5G Session Termination
    s6_start = time.time()
    try:
        term_resp = client.deregister_ue_session(session)
        log_step(6, "Terminate 5G Subscriber Session", "success",
                 f"Session termination telemetry accepted (HTTP {term_resp.get('status_code')})",
                 int((time.time() - s6_start) * 1000))
    except Exception as exc:
        log_step(6, "Terminate 5G Subscriber Session", "warning", f"Session termination notice: {exc}")

    # Step 7: Delete Test SIM
    s7_start = time.time()
    try:
        if created_id:
            client.delete_tenant_ue(created_id)
            log_step(7, "Delete Test SIM (UE)", "success",
                     f"Safely deleted test SIM ID: {created_id}",
                     int((time.time() - s7_start) * 1000))
        else:
            log_step(7, "Delete Test SIM (UE)", "warning", "No created ID returned to delete")
    except Exception as exc:
        log_step(7, "Delete Test SIM (UE)", "error", f"Failed to delete test SIM: {exc}")

    # Step 8: Verify Clean State
    s8_start = time.time()
    try:
        time.sleep(1)
        final_list = client.list_tenant_ues()
        found = any(str(u.get("identity_id") or u.get("id")) == str(created_id) for u in final_list.get("data", []))
        log_step(8, "Verify Clean State", "success" if not found else "warning",
                 "Test SIM completely removed from tenant inventory." if not found else "Item propagating removal.",
                 int((time.time() - s8_start) * 1000))
    except Exception as exc:
        log_step(8, "Verify Clean State", "warning", str(exc))

    total_duration = int((time.time() - start_time) * 1000)
    all_ok = all(s["status"] != "error" for s in steps_log)

    return {
        "success": all_ok,
        "total_duration_ms": total_duration,
        "steps": steps_log,
        "test_imsi": test_imsi,
        "test_apn": test_apn,
    }


# -----------------------------------------------------------------------------
# API Endpoints: 5G SASE Summary & Monitoring Telemetry
# -----------------------------------------------------------------------------

@app.get("/api/metrics/summary")
def get_metrics_summary():
    """Get 5G SASE Summary KPI stats matching Strata Cloud Manager."""
    try:
        client = get_current_client()
        summary = client.get_monitoring_summary()
        return {
            "success": True,
            "data": summary,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "data": {
                "total_5g_tenants": 2,
                "total_bandwidth_mbps": 100,
                "total_configured_users": 200,
                "interconnects_count": 1,
                "interconnects_up": 1,
                "interconnects_down": 0,
                "compute_region": "europe-west9",
                "interconnect_items": [
                    {
                        "bandwidth": 100,
                        "computeRegion": "europe-west9",
                        "status": "Successful",
                        "vlanAttachmentCount": 1,
                        "vlanAttachmentStatusEntry": {"down": 0, "up": 1},
                    }
                ],
            },
        }


@app.get("/api/metrics/throughput")
def get_throughput_metrics(
    time_range: str = "7d",
    region: str = "europe-west9"
):
    """Get Ingress and Egress throughput time-series points dynamically scaled by active 5G sessions."""
    try:
        now = datetime.now()
        active_sess = load_active_sessions()
        active_count = len(active_sess)

        if time_range == "1h":
            # 7 points spaced by 10 minutes rolling up to current minute
            times = [(now - timedelta(minutes=60 - 10 * i)).strftime("%H:%M") for i in range(7)]
            base_points = [
                {"time": times[0], "in": 1.5, "eg": 3.4, "sess_ratio": 0.2},
                {"time": times[1], "in": 3.8, "eg": 12.8, "sess_ratio": 0.4},
                {"time": times[2], "in": 8.2, "eg": 34.0, "sess_ratio": 0.6},
                {"time": times[3], "in": 14.5, "eg": 66.2, "sess_ratio": 0.9},
                {"time": times[4], "in": 9.0, "eg": 38.5, "sess_ratio": 0.6},
                {"time": times[5], "in": 4.2, "eg": 18.0, "sess_ratio": 0.4},
                {"time": times[6], "in": 2.5, "eg": 12.2, "sess_ratio": 0.3},
            ]
        elif time_range == "24h":
            # 9 points spanning the last 24 hours rolling up to current local time
            times = [(now - timedelta(hours=24 - 3 * i)).strftime("%H:%M") for i in range(8)]
            times.append(now.strftime("%b %d"))
            base_points = [
                {"time": times[0], "in": 0.0, "eg": 0.0, "sess_ratio": 0.0},
                {"time": times[1], "in": 0.0, "eg": 0.0, "sess_ratio": 0.0},
                {"time": times[2], "in": 0.0, "eg": 0.0, "sess_ratio": 0.0},
                {"time": times[3], "in": 0.8, "eg": 2.4, "sess_ratio": 0.2},
                {"time": times[4], "in": 4.5, "eg": 18.0, "sess_ratio": 0.5},
                {"time": times[5], "in": 16.8, "eg": 84.5, "sess_ratio": 1.0},
                {"time": times[6], "in": 7.2, "eg": 32.0, "sess_ratio": 0.6},
                {"time": times[7], "in": 3.6, "eg": 14.5, "sess_ratio": 0.4},
                {"time": times[8], "in": 2.5, "eg": 16.0, "sess_ratio": 0.3},
            ]
        else:  # default "7d" (Past 7 days matching Strata Cloud Manager)
            # 8 daily points from 7 days ago to today formatted as MM/DD (e.g. 09/05, 09/06, ..., 09/12)
            dates = [(now - timedelta(days=7 - i)).strftime("%m/%d") for i in range(8)]
            base_points = [
                {"time": dates[0], "in": 0.0, "eg": 0.0, "sess_ratio": 0.0},
                {"time": dates[1], "in": 0.0, "eg": 0.0, "sess_ratio": 0.0},
                {"time": dates[2], "in": 0.0, "eg": 0.0, "sess_ratio": 0.0},
                {"time": dates[3], "in": 0.0, "eg": 0.0, "sess_ratio": 0.0},
                {"time": dates[4], "in": 2.8, "eg": 10.2, "sess_ratio": 0.3},
                {"time": dates[5], "in": 18.5, "eg": 112.5, "sess_ratio": 1.0},  # SCM Peak
                {"time": dates[6], "in": 8.2, "eg": 52.0, "sess_ratio": 0.6},
                {"time": dates[7], "in": 2.5, "eg": 16.0, "sess_ratio": 0.4},
            ]

        points = []
        for p in base_points:
            # Active session bonus on latest traffic points
            if active_count > 0:
                bonus_in = round(active_count * 1.5 * p["sess_ratio"], 1)
                bonus_eg = round(active_count * 5.0 * p["sess_ratio"], 1)
                in_val = round(p["in"] + bonus_in, 1)
                eg_val = round(p["eg"] + bonus_eg, 1)
                pt_sess = max(1, int(round(active_count * p["sess_ratio"]))) if p["sess_ratio"] > 0 else 0
            else:
                in_val = p["in"]
                eg_val = p["eg"]
                pt_sess = 0

            points.append({
                "time": p["time"],
                "ingress_kbps": in_val,
                "egress_kbps": eg_val,
                "sessions": pt_sess,
            })

        peak_in = max((p["ingress_kbps"] for p in points), default=0.0)
        peak_eg = max((p["egress_kbps"] for p in points), default=0.0)
        max_y = max(120, int(peak_eg * 1.15)) if peak_eg > 115 else 120

        return {
            "success": True,
            "time_range": time_range,
            "region": region,
            "active_sessions_count": active_count,
            "unit": "Kbps",
            "max_y": max_y,
            "peak_ingress": peak_in,
            "peak_egress": peak_eg,
            "points": points,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# -----------------------------------------------------------------------------
# Debug Logger & Live API Inspector Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/debug/logs")
def get_debug_logs(
    limit: int = 50,
    search: Optional[str] = None,
    method: Optional[str] = None,
    status_code: Optional[int] = None,
):
    """Retrieve recorded API transactions."""
    logs = api_debug_logger.get_logs(
        limit=limit,
        search=search,
        method=method,
        status_code=status_code,
    )
    return {
        "success": True,
        "count": len(logs),
        "total_buffered": api_debug_logger.count(),
        "logs": logs,
    }


@app.get("/api/debug/logs/export")
def export_debug_logs():
    """Export all debug logs as downloadable JSON."""
    logs = api_debug_logger.get_logs(limit=150)
    return JSONResponse(
        content={"exported_at": time.time(), "total": len(logs), "transactions": logs},
        headers={"Content-Disposition": f"attachment; filename=prisma_5g_api_logs_{int(time.time())}.json"}
    )


@app.get("/api/debug/logs/{log_id}")
def get_debug_log_detail(log_id: str):
    """Retrieve single transaction log details."""
    log = api_debug_logger.get_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail=f"Log transaction '{log_id}' not found")
    return {"success": True, "log": log}


@app.delete("/api/debug/logs")
def clear_debug_logs():
    """Clear all recorded debug logs."""
    cleared = api_debug_logger.clear()
    return {"success": True, "cleared_count": cleared}


# -----------------------------------------------------------------------------
# Frontend Single Page App Delivery
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Serve the single-page application interface."""
    index_file = BASE_DIR / "templates" / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Template index.html not found")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
