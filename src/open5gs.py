"""Open5GS 5G Core Manager and Real-Time Telemetry Client.

Supports:
- MongoDB subscriber provisioning (Open5GS v2.8.0 schema).
- Real-time session telemetry polling (SMF /pdu-info and AMF /ue-info).
- Local execution on Core VM and remote SSH/REST execution from Dev/Agent nodes.
- Mock/dry-run mode for offline testing.
"""

from typing import Dict, List, Optional, Any
import json
import logging
import os
import subprocess
import time
import urllib.request
import urllib.error

from src.models import (
    OrchestratedEndpoint,
    SecurityConfig,
    SliceConfig,
    QoSConfig,
)

logger = logging.getLogger("Open5GSClient")
PROTECTED_IMSIS = {"901700000000001", "999700000000001"}


class Open5GSClient:
    """Manages Open5GS 5G Core subscribers in MongoDB and queries SMF/AMF telemetry."""

    def __init__(
        self,
        mongo_uri: Optional[str] = None,
        smf_url: Optional[str] = None,
        amf_url: Optional[str] = None,
        ssh_host: Optional[str] = None,
        mock_mode: bool = False,
    ):
        self.mongo_uri = mongo_uri or os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
        self.smf_url = (smf_url or os.environ.get("SMF_URL", "http://127.0.0.4:9090")).rstrip("/")
        self.amf_url = (amf_url or os.environ.get("AMF_URL", "http://127.0.0.5:9090")).rstrip("/")
        self.ssh_host = ssh_host or os.environ.get("CORE_SSH_HOST", "jsuzanne@152.236.5.40")
        self.mock_mode = mock_mode or (os.environ.get("MOCK_MODE", "false").lower() == "true")
        self._mock_subscribers: Dict[str, Dict[str, Any]] = {}
        self._mock_sessions: Dict[str, Dict[str, Any]] = {}
        self._mongo_client = None

    @property
    def mongo_db(self):
        """Lazily initialize and return PyMongo database instance if available."""
        if self.mock_mode:
            return None
        if self._mongo_client is None:
            try:
                import pymongo
                self._mongo_client = pymongo.MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
            except Exception as e:
                logger.warning(f"Could not initialize PyMongo client: {e}")
                return None
        try:
            return self._mongo_client["open5gs"]
        except Exception:
            return None

    def _exec_command(self, cmd: str) -> str:
        """Execute command locally if on Core host, or over SSH if remote."""
        if self.mock_mode:
            return "{}"

        # If on Core VM (localhost)
        if os.environ.get("ROLE") == "core" or not self.ssh_host:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"Local command failed: {res.stderr.strip()}")
            return res.stdout.strip()

        # Remote execution over SSH
        ssh_cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            "-o", "StrictHostKeyChecking=accept-new",
            self.ssh_host,
            cmd,
        ]
        res = subprocess.run(ssh_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"SSH command failed on {self.ssh_host}: {res.stderr.strip()}")
        return res.stdout.strip()

    def _http_get(self, url: str) -> Optional[Dict[str, Any]]:
        """Perform HTTP GET locally or remotely over SSH curl."""
        if self.mock_mode:
            return {"items": [], "pager": {"count": 0}}

        if os.environ.get("ROLE") == "core":
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Prisma-5G-Orchestrator"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return json.loads(resp.read().decode())
            except Exception as e:
                logger.error(f"HTTP GET failed on {url}: {e}")
                return None

        # Fetch remotely via SSH curl
        out = self._exec_command(f"curl -s --max-time 5 '{url}'")
        if out:
            try:
                return json.loads(out)
            except Exception as e:
                logger.error(f"Failed to parse remote JSON from {url}: {e}")
        return None

    def build_subscriber_document(self, endpoint: OrchestratedEndpoint) -> Dict[str, Any]:
        """Generate Open5GS v2.8.0 MongoDB subscriber document."""
        sec_dict = endpoint.security.to_mongo_security()
        
        session_doc = {
            "name": endpoint.apn,
            "type": 3,  # IPv4
            "ambr": {
                "downlink": {"value": endpoint.qos.ambr_dl_mbps, "unit": 3},
                "uplink": {"value": endpoint.qos.ambr_ul_mbps, "unit": 3},
            },
            "qos": {
                "index": endpoint.qos.five_qi,
                "arp": {
                    "priority_level": 8,
                    "pre_emption_capability": 1,
                    "pre_emption_vulnerability": 1,
                },
            },
        }

        slice_doc: Dict[str, Any] = {
            "sst": endpoint.slice.sst,
            "default_indicator": True,
            "session": [session_doc],
        }
        if endpoint.slice.sd:
            slice_doc["sd"] = endpoint.slice.sd

        doc: Dict[str, Any] = {
            "imsi": str(endpoint.imsi),
            "security": sec_dict,
            "slice": [slice_doc],
            "ambr": {
                "downlink": {"value": endpoint.qos.ambr_dl_mbps, "unit": 3},
                "uplink": {"value": endpoint.qos.ambr_ul_mbps, "unit": 3},
            },
            "schema_version": 1,
            "subscriber_status": 0,
            "network_access_mode": 0,
            "subscribed_rau_tau_timer": 12,
            "access_restriction_data": 32,
            "managed_by": "stigix-orchestrator",
            "vertical_id": endpoint.vertical_id,
            "device_name": endpoint.device_name,
            "vendor": endpoint.vendor,
            "device_model": endpoint.device_model,
            "icon": endpoint.icon,
            "created_at": endpoint.created_at,
            "updated_at": endpoint.updated_at,
        }
        return doc

    def create_subscriber(self, endpoint: OrchestratedEndpoint) -> bool:
        """Insert or replace a subscriber in MongoDB open5gs.subscribers."""
        doc = self.build_subscriber_document(endpoint)
        if self.mock_mode:
            self._mock_subscribers[endpoint.imsi] = doc
            logger.info(f"[Mock] Subscriber {endpoint.imsi} created in memory.")
            return True

        if self.mongo_db is not None:
            try:
                try:
                    import bson
                    if "security" in doc and "sqn" in doc["security"]:
                        doc["security"]["sqn"] = bson.int64.Int64(doc["security"]["sqn"])
                except Exception:
                    pass
                self.mongo_db.subscribers.replace_one({"imsi": str(endpoint.imsi)}, doc, upsert=True)
                logger.info(f"Subscriber {endpoint.imsi} successfully provisioned in MongoDB via PyMongo.")
                return True
            except Exception as e:
                logger.warning(f"PyMongo create failed, falling back to CLI: {e}")

        # Ensure SQN is serialized for mongosh NumberLong
        doc_json = json.dumps(doc)
        mongo_script = f"""
            const d = {doc_json};
            d.security.sqn = NumberLong(d.security.sqn || 0);
            db.getSiblingDB("open5gs").subscribers.replaceOne(
                {{ imsi: "{endpoint.imsi}" }},
                d,
                {{ upsert: true }}
            );
        """
        cmd = f"mongosh --quiet --eval '{mongo_script}'"
        out = self._exec_command(cmd)
        logger.info(f"MongoDB response for IMSI {endpoint.imsi}: {out}")
        return True

    def get_subscriber(self, imsi: str) -> Optional[Dict[str, Any]]:
        """Retrieve a subscriber document by IMSI."""
        if self.mock_mode:
            return self._mock_subscribers.get(imsi)

        if self.mongo_db is not None:
            try:
                doc = self.mongo_db.subscribers.find_one({"imsi": str(imsi)}, {"_id": 0})
                if doc:
                    return doc
            except Exception as e:
                logger.warning(f"PyMongo get failed: {e}")

        mongo_script = f"""
            JSON.stringify(db.getSiblingDB("open5gs").subscribers.findOne({{ imsi: "{imsi}" }}))
        """
        cmd = f"mongosh --quiet --eval '{mongo_script}'"
        out = self._exec_command(cmd)
        if out and out != "null" and out != "undefined":
            try:
                return json.loads(out)
            except Exception as e:
                logger.error(f"Failed to parse subscriber JSON for IMSI {imsi}: {e}")
        return None

    def list_subscribers(self, managed_only: bool = False) -> List[Dict[str, Any]]:
        """List subscribers from MongoDB."""
        if self.mock_mode:
            return list(self._mock_subscribers.values())

        if self.mongo_db is not None:
            try:
                query = {"managed_by": "stigix-orchestrator"} if managed_only else {}
                docs = list(self.mongo_db.subscribers.find(query, {"_id": 0}))
                return docs
            except Exception as e:
                logger.warning(f"PyMongo list failed: {e}")

        query = '{ "managed_by": "stigix-orchestrator" }' if managed_only else "{}"
        mongo_script = f"""
            JSON.stringify(db.getSiblingDB("open5gs").subscribers.find({query}).toArray())
        """
        cmd = f"mongosh --quiet --eval '{mongo_script}'"
        out = self._exec_command(cmd)
        if out:
            try:
                data = json.loads(out)
                return data if isinstance(data, list) else []
            except Exception as e:
                logger.error(f"Failed to parse subscribers list: {e}")
        return []

    def delete_subscriber(self, imsi: str) -> bool:
        """Delete a subscriber by IMSI, protecting baseline lab IMSIs."""
        if imsi in PROTECTED_IMSIS:
            logger.warning(f"Protected IMSI {imsi} deletion rejected.")
            return False

        if self.mock_mode:
            self._mock_subscribers.pop(imsi, None)
            return True

        if self.mongo_db is not None:
            try:
                self.mongo_db.subscribers.delete_one({"imsi": str(imsi)})
                logger.info(f"Subscriber {imsi} deleted via PyMongo.")
                return True
            except Exception as e:
                logger.warning(f"PyMongo delete failed: {e}")

        mongo_script = f"""
            db.getSiblingDB("open5gs").subscribers.deleteOne({{
                imsi: "{imsi}",
                imsi: {{ $nin: ["901700000000001", "999700000000001"] }}
            }});
        """
        cmd = f"mongosh --quiet --eval '{mongo_script}'"
        self._exec_command(cmd)
        return True

    def get_smf_pdu_info(self) -> List[Dict[str, Any]]:
        """Fetch real-time active PDU sessions from Open5GS SMF."""
        if self.mock_mode:
            return list(self._mock_sessions.values())

        url = f"{self.smf_url}/pdu-info?page=-1"
        data = self._http_get(url)
        if data and isinstance(data, dict):
            return data.get("items", [])
        return []

    def get_core_status(self) -> Dict[str, Any]:
        """Check status of Open5GS Core services (AMF, SMF, UPF) and MongoDB."""
        if self.mock_mode:
            return {
                "mongodb": "active",
                "amf": "active",
                "smf": "active",
                "upf": "active",
                "overall": "healthy",
            }

        # 1. MongoDB Status
        mongo_s = "inactive"
        if self.client is not None:
            try:
                self.client.admin.command("ping")
                mongo_s = "active"
            except Exception:
                mongo_s = "inactive"

        # 2. AMF Status (REST API probe)
        amf_s = "inactive"
        try:
            amf_res = self._http_get(f"{self.amf_url}/ue-info?page=-1")
            if amf_res is not None:
                amf_s = "active"
        except Exception:
            amf_s = "inactive"

        # 3. SMF Status (REST API probe)
        smf_s = "inactive"
        try:
            smf_res = self._http_get(f"{self.smf_url}/pdu-info?page=-1")
            if smf_res is not None:
                smf_s = "active"
        except Exception:
            smf_s = "inactive"

        # 4. UPF Status (Inferred from SMF/PFCP and systemctl fallback)
        upf_s = "inactive"
        if smf_s == "active":
            upf_s = "active"
        else:
            try:
                out = self._exec_command("systemctl is-active open5gs-upfd 2>/dev/null || true")
                if "active" in out:
                    upf_s = "active"
            except Exception:
                pass

        all_ok = all(s == "active" for s in [amf_s, smf_s, upf_s, mongo_s])
        return {
            "amf": amf_s,
            "smf": smf_s,
            "upf": upf_s,
            "mongodb": mongo_s,
            "overall": "healthy" if all_ok else "degraded",
        }

    def get_amf_ue_info(self) -> List[Dict[str, Any]]:
        """Fetch real-time attached UEs from Open5GS AMF."""
        if self.mock_mode:
            return []

        url = f"{self.amf_url}/ue-info?page=-1"
        data = self._http_get(url)
        if data and isinstance(data, dict):
            return data.get("items", [])
        return []

    def poll_pdu_session(
        self,
        imsi: str,
        timeout_sec: int = 30,
        interval_sec: float = 1.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Poll SMF until an active PDU session with an IPv4 address is found for this IMSI.
        Returns dictionary with {ipv4, psi, dnn, sst, sd, qos_5qi} or None.
        """
        supi_target = f"imsi-{imsi}" if not imsi.startswith("imsi-") else imsi
        start_time = time.time()

        while (time.time() - start_time) < timeout_sec:
            items = self.get_smf_pdu_info()
            for item in items:
                if item.get("supi") == supi_target or item.get("supi") == imsi:
                    for pdu in item.get("pdu", []):
                        if pdu.get("ipv4"):
                            snssai = pdu.get("snssai", {})
                            qos_flows = pdu.get("qos_flows", [{}])
                            five_qi = qos_flows[0].get("5qi") if qos_flows else 9
                            return {
                                "imsi": imsi,
                                "supi": supi_target,
                                "ipv4": pdu.get("ipv4"),
                                "ipv6": pdu.get("ipv6"),
                                "psi": pdu.get("psi", 1),
                                "dnn": pdu.get("dnn"),
                                "sst": snssai.get("sst", 1),
                                "sd": snssai.get("sd"),
                                "5qi": five_qi,
                                "pdu_state": pdu.get("pdu_state", "active"),
                            }
            time.sleep(interval_sec)

        logger.warning(f"Timeout waiting for active PDU session for IMSI {imsi} ({timeout_sec}s)")
        return None
