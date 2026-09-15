# 🚀 Prisma SASE 5G Management & Lifecycle Portal

[![CI & Docker Publish](https://github.com/jsuzanne/Prisma-SASE-5G/actions/workflows/ci.yml/badge.svg)](https://github.com/jsuzanne/Prisma-SASE-5G/actions)
[![Docker Image](https://img.shields.io/badge/docker-jsuzanne%2Fprisma--5g--sase-blue?logo=docker)](https://hub.docker.com/r/jsuzanne/prisma-5g-sase)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?logo=python)](https://www.python.org/)
[![Strata Cloud Manager](https://img.shields.io/badge/Palo%20Alto%20Networks-Strata%20Cloud%20Manager-orange?logo=paloaltonetworks)](https://stratacloudmanager.paloaltonetworks.com)

> [!NOTE]
> **🚀 Demonstration & Proof-of-Concept (PoC) Prototype**  
> This application is a demo prototype designed for trade shows (such as **SIDO Lyon**), customer innovation centers, and executive briefings to showcase **Palo Alto Networks Prisma SASE 5G** integrated with **Universal 5G Core networks (Public Telco MNOs, MVNOs, or Enterprise Private 5G)**. It highlights agentless Zero-Trust mobile security, multi-industry IoT fleet simulation, and real-time UPF session telemetry correlation.

A modern, high-performance **Demo & PoC Prototype** Web Application, REST API, CLI toolkit, and automated test suite for **Palo Alto Networks Prisma SASE 5G** (Strata Cloud Manager & Universal 5G Core Integration).

Enables full programmatic lifecycle management of User Equipment (UE / SIM Cards), real-time 5G session telemetry correlation, subscriber user groups, SCM monitoring KPI metrics, live API debugging, and multi-carrier co-branding.

---

## 📸 Visual Tour & Key Modules

### 1. 🏭 Multi-Vertical Industry Fleet & SIM Inventory
> **Multi-vertical IoT fleet management with live session status, IP indicators, group tags, and instant action triggers.**  
> Filter devices across 7 industry verticals (*⚡ EV Infra, 🤖 Industry 4.0, 💳 Retail POS, ✈️ Aviation, 🚗 Automotive, 🚌 Transit, 🏙️ Smart City*), view live session status (🟢 Active / 🔴 Inactive), and trigger 1-click Zero-Trust policy actions.

<p align="center">
  <img src="static/img/sim_inventory_fleet.png" alt="Prisma SASE 5G SIM Inventory & Fleet View" width="100%">
</p>

---

### 2. ⚡ 5G Session Control & Live UPF Telemetry Console
> **Real-time REST UPF user plane telemetry injection with 3-node architecture flow and live streaming event console.**  
> Attach or detach sessions on-demand with automated CIDR IP validation (`10.56.0.192/27, 10.56.0.224/27`), last-used IP memory, and live Strata Cloud Manager API correlation feedback.

<p align="center">
  <img src="static/img/session_modal_attached.png" alt="5G Session Control & IP Telemetry" width="100%">
</p>

---

### 3. 🎯 1-Click IoT Fleet Generator & eSIM Registration
> **Instant 1-click industry vertical presets with automated CIDR pool validation & 3GPP IMEI generation.**  
> Select a preset (*EVSE Charger, Factory Robot, Retail POS, Avionics iPad, Connected Bus*) to automatically generate valid 3GPP IMSIs (`20895...`), Luhn-compliant IMEIs, and dynamic security group assignments.

<p align="center">
  <img src="static/img/sim_register_retail.png" alt="1-Click Industry Presets Modal" width="100%">
</p>

---

### 4. 🔍 Live API Inspector & Real-Time Debug Console
> **Real-time SCM 5G REST API transactions, request/response JSON payloads, latencies, and 1-click copy cURL commands.**  
> Inspect every outbound API call to Palo Alto Networks Strata Cloud Manager, view precise response latencies (`233ms`), and export cURL commands for instant command-line replication.

<p align="center">
  <img src="static/img/api_inspector_console.png" alt="Live API Inspector & Debug Console" width="100%">
</p>

---

## 🌟 Key Features

* **🏭 Multi-Vertical IoT Fleet Simulation**: 7 industry verticals (*Smart City, Industry 4.0, Healthcare, Logistics, Retail POS, Agritech, Energy Grid*), 1-click **Auto-Enrich** overlay for registered SIMs, and instant toggle between **Industry Fleet View** and **Raw SCM View**.
* **📊 5G SASE Summary Dashboard**: SCM-aligned top KPI cards (Tenants, Bandwidth, Configured Users, Interconnects), interactive Ingress/Egress throughput trend chart, and complete 11-column UE mappings table.
* **📱 SIM & 5G Identity Lifecycle**: Programmatic CRUD for SIMs and IMEIs with default APN isolation (`sasetest`), multi-tenant TSG targeting, and dynamic policy group assignment.
* **🛡️ 5G Identity Groups & Security Policies**: Create custom subscriber user groups (e.g. `VIP-Sensors`, `Field-Workers`, `Finance-eSIMs`) and reassign devices on the fly for policy segmentation.
* **⚡ 5G Session Telemetry (Control & User Plane Correlation)**: Real-time REST IP telemetry injection (`/uesession/register` and `/uesession/deregister`) correlating mobile IPs with IMSI/IMEI for agentless Zero-Trust enforcement.
* **🔍 Live API Inspector & Debug Console**: In-memory ring buffer capturing all outbound HTTP transactions with latency tracking, status codes, payload inspection, and 1-click **Copy cURL** command generation.
* **🎨 Co-Branding & Display Customizer**: Real-time carrier accent colors, dynamic background atmospheres, custom logo upload, and responsive zoom scaling (`100%`, `115%`, `130%`) for 2K/4K presentation screens.
* **📦 1-Click JSON Demo Packs & Offline Sandbox**: Export/import complete fleet topologies to portable `.json` files, 1-click bulk provision to SCM, and full 100% offline standalone simulation engine for disconnected presentations.
* **⚙️ Persistent In-App Settings**: Configure service account credentials directly in the Web UI with automated host persistence (`./config/config.json`) and live connection testing.
* **🧪 Automated Test Suite**: 71 automated unit tests with 100% pass rate on GitHub Actions CI.

---

## 🚀 Quick Start with Docker Compose (Zero-Config & Persistent)

The easiest way to run the portal on any machine (Laptop, Server, NUC, Raspberry Pi):

### Option A: 1-Click Launch with `docker-compose.yml` (Recommended)

Create a `docker-compose.yml` file with the persistent `./config` volume:

```yaml
services:
  prisma-sase-5g:
    image: jsuzanne/prisma-5g-sase:latest
    container_name: prisma-sase-5g
    ports:
      - "8000:8000"
    volumes:
      # Persists config.json & credentials across container recreation / updates
      - ./config:/app/config
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```

Then start the container:

```bash
# Start container in detached mode (no .env required)
docker compose up -d
```

> [!TIP]
> **Persistent Configuration**: When you save credentials in the Web UI **Settings** tab, they are automatically saved to `./config/config.json` and `./config/.env` on your host. Recreating, updating, or restarting the Docker container will preserve all your configuration seamlessly!

### Option B: Clone Repository & Run

```bash
# 1. Clone repository
git clone git@github.com:jsuzanne/Prisma-SASE-5G.git
cd Prisma-SASE-5G

# 2. Start container with Docker Compose
docker compose up -d
```

### Option C: Direct `docker run` with Persistent Volume

```bash
mkdir -p config
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  --name prisma-sase-5g \
  jsuzanne/prisma-5g-sase:latest
```

Once running, open your browser at **[http://localhost:8000](http://localhost:8000)**.  
Credentials can be configured directly via the Web UI in the **Settings** tab.

---

## 💻 Local Development (Without Docker)

### 1. Installation

```bash
# Clone the repository
git clone git@github.com:jsuzanne/Prisma-SASE-5G.git
cd Prisma-SASE-5G

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Credentials (`.env` or via Web UI)

You can configure credentials directly in the Web UI (**Settings** tab), or create a local `.env`:

```ini
PANW_CLIENT_ID=5g-sase-service@2000000001.iam.panserviceaccount.com
PANW_CLIENT_SECRET=your-secret-here
PANW_TSG_ID=2000000001
PANW_API_BASE_URL=https://api.sase.paloaltonetworks.com
PANW_AUTH_URL=https://auth.apps.paloaltonetworks.com/am/oauth2/access_token
DEFAULT_APN=sasetest
DEFAULT_IP_TYPE=IPv4
```

### 3. Launch Web Application

```bash
python3 app.py
```
Visit **[http://localhost:8000](http://localhost:8000)**.

---

## 📖 Complete Provisioning Walkthrough (Web UI vs CLI)

Provisioning a 5G subscriber into Palo Alto Networks Prisma SASE 5G consists of two essential phases:
1. **Control Plane Provisioning**: Mapping the SIM hardware identifiers (`IMSI`, `IMEI`, `APN`) and assigning security groups.
2. **User Plane / Session Enrichment**: Injecting real-time IP allocation telemetry when the SIM connects to the 5G Core network, binding Zero-Trust security policies instantly.

---

### Step 1: Monitor 5G SASE Health & Interconnects

Inspect the global health of your 5G SASE tenant, allocated bandwidth, and VLAN attachments.

| Method | How to Perform / Where to View |
| :--- | :--- |
| 🌐 **Web UI** | Navigate to the **"5G SASE Summary"** tab to view the 4 KPI cards and Ingress/Egress Throughput trends. |
| 💻 **CLI** | `python3 manage_5g.py summary` and `python3 manage_5g.py interconnect` |

---

### Step 2: Manage 5G Identity Groups (Security Policies)

Inspect or create subscriber security groups that hold Zero-Trust policy profiles (e.g. `VIP-Sensors`, `Field-Workers`, `IoT-Devices`).

| Method | How to Perform / Where to View |
| :--- | :--- |
| 🌐 **Web UI** | In the **"Groups & Policies"** tab, click **"+ Add Group"** to define a new policy group with interactive SIM assignment. |
| 💻 **CLI** | `python3 manage_5g.py groups`<br>`python3 manage_5g.py group-create --name "VIP-Sensors" --tsg-id 2000000002` |

---

### Step 3: Provision a SIM Card / UE (Control Plane)

Register the SIM card hardware identifiers and assign it to an APN (default `sasetest`) and target Tenant Service Group.

| Method | How to Perform / Where to View |
| :--- | :--- |
| 🌐 **Web UI** | Click **"Add New SIM"** in the banner or **SIM Inventory** tab, enter or generate IMSI/IMEI, select APN `sasetest`, and click **"Create SIM"**. |
| 💻 **CLI** | `python3 manage_5g.py add --imsi 208950123456789 --imei 860123123456789 --apn sasetest` |

---

### Step 4: Edit SIM & Assign Subscriber Group

Assign or move the SIM card to a specific security policy group.

| Method | How to Perform / Where to View |
| :--- | :--- |
| 🌐 **Web UI** | In the **"SIM Inventory"** tab, click the **Edit ✏️** button on any SIM row. In the modal, choose the desired **Subscriber Group** and click **Save**. |
| 💻 **CLI** | `python3 manage_5g.py assign-group --ue-id "<IDENTITY_ID>" --group-name "VIP-Sensors"`<br>`python3 manage_5g.py update "<IDENTITY_ID>" --apn "sase" --group-id "<GROUP_ID>"` |

---

### Step 5: Activate 5G Session Telemetry (IP Allocation / Data Plane)

When the IoT device connects to the 5G Core network, the carrier network assigns an IP address (e.g. `10.56.0.200`). The 5G Core notifies Prisma SASE 5G via REST telemetry to bind security policies in real time without any device agent or VPN client.

| Method | How to Perform / Where to View |
| :--- | :--- |
| 🌐 **Web UI** | In the **"SIM Inventory"** tab, click **"⚡ Attach"** next to the SIM to open the **5G Session Control** modal. The last-used IP address and CIDR pool are auto-suggested, and the real-time Session Event Console logs the UPF telemetry stream. |
| 💻 **CLI** | `python3 manage_5g.py session-register --imsi 208950123456789 --imei 860123123456789 --apn sasetest --ipv4 10.56.0.200` |

---

### Step 6: Threat Inspection & Policy Enforcement

When a mobile subscriber attempts to access unauthorized or malicious external content:

| Component | Observation & Behavior |
| :--- | :--- |
| 📱 **Connected Device** | The browser receives the Palo Alto Networks **Zero-Trust Block Page** directly from the 5G Core user plane without requiring any local endpoint agent. |
| 🛡️ **Zero-Trust Enforcement** | Real-time URL filtering and DNS security rules inspect the mobile payload associated with the subscriber IMSI and IP session mapping. |

---

### Step 7: Terminate / Disconnect 5G Session

When the subscriber disconnects or changes cell/IP, a deregistration event is emitted.

| Method | How to Perform / Where to View |
| :--- | :--- |
| 🌐 **Web UI** | In the **"SIM Inventory"** tab, click **"⏻ Detach"** next to the active SIM (or trigger termination from the 5G Session Control modal). |
| 💻 **CLI** | `python3 manage_5g.py session-terminate --imsi 208950123456789 --imei 860123123456789 --apn sasetest --ipv4 10.56.0.200` |

---

### Step 8: Deprovision / Delete SIM Card

To decommission or remove a SIM from the tenant:

| Method | How to Perform / Where to View |
| :--- | :--- |
| 🌐 **Web UI** | In the **"SIM Inventory"** tab, click **"Delete"** next to the test SIM. |
| 💻 **CLI** | `python3 manage_5g.py delete <IDENTITY_ID>` |

---

## 🛠️ Complete CLI Command Reference (`manage_5g.py`)

Run `python3 manage_5g.py --help` to see all available CLI commands:

```bash
# General Help
python3 manage_5g.py --help

# Tenants & Hierarchy
python3 manage_5g.py tenants

# SIM / UE Inventory
python3 manage_5g.py list
python3 manage_5g.py get <IDENTITY_ID>
python3 manage_5g.py add --imsi <IMSI> --imei <IMEI> --apn sasetest
python3 manage_5g.py update <IDENTITY_ID> --apn sase --group-id <GROUP_ID>
python3 manage_5g.py delete <IDENTITY_ID>
python3 manage_5g.py bulk-delete <ID_1> <ID_2>

# 5G Subscriber Groups
python3 manage_5g.py groups
python3 manage_5g.py group-get <GROUP_ID>
python3 manage_5g.py group-create --name "VIP-Sensors" --tsg-id 2000000002
python3 manage_5g.py assign-group --ue-id <IDENTITY_ID> --group-name "VIP-Sensors"
python3 manage_5g.py group-delete <CUSTOM_GROUP_ID>

# 5G Real-time Session Telemetry
python3 manage_5g.py session-register --imsi <IMSI> --imei <IMEI> --apn sasetest --ipv4 10.56.0.200
python3 manage_5g.py session-terminate --imsi <IMSI> --imei <IMEI> --apn sasetest --ipv4 10.56.0.200

# SCM Monitoring KPIs & Interconnects
python3 manage_5g.py summary
python3 manage_5g.py interconnect

# Live API Debug Logs
python3 manage_5g.py debug-logs --limit 20
```

---

## 🧪 Automated Testing & Verification

Run the test suite covering all REST endpoints, authentication, SIM CRUD, group creation, group assignment, API debug logging, and demo packs:

```bash
# Run unit tests (71 passing tests)
./.venv/bin/python -m unittest discover tests -v

# Run end-to-end automated lifecycle test script
python3 test_lifecycle.py
```

---

## 📡 REST API Documentation

Interactive Swagger documentation is available at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

| Category | Key Endpoints | Description |
| :--- | :--- | :--- |
| **System & Health** | `GET /api/status`, `GET /api/version`, `GET /api/config` | Health checks, TSG resolution, masked configuration |
| **Tenants & Hierarchy** | `GET /api/tenants` | Multi-tenant TSG hierarchy discovery |
| **SIM / UE Lifecycle** | `GET /api/ues`, `POST /api/ues`, `PUT /api/ues/{id}`, `DELETE /api/ues/{id}` | Full programmatic hardware identity management |
| **5G User Groups** | `GET /api/groups`, `POST /api/groups`, `PUT /api/groups/{id}`, `DELETE /api/groups/{id}` | Subscriber security policy groups |
| **5G Session Telemetry** | `POST /api/sessions/register`, `POST /api/sessions/deregister` | Real-time UPF mobile IP telemetry attachment |
| **Monitoring & KPIs** | `GET /api/metrics/summary`, `GET /api/metrics/throughput` | Bandwidth trends, interconnects, top metrics |
| **Industry Presets** | `GET /api/presets/verticals`, `POST /api/presets/enrich`, `GET /api/presets/random` | Fleet generation and auto-enrichment overlays |
| **Demo Packs & SCM Sync** | `GET /api/demo/export`, `POST /api/demo/import`, `POST /api/demo/bulk-provision` | Portable JSON snapshots & 1-click cloud sync |
| **Live API Inspector** | `GET /api/debug/logs`, `POST /api/debug/logs/clear` | Real-time transaction buffer & cURL generation |

---

## 🔒 Security & Privacy Policies

- **Credential Privacy**: `.env` is ignored by `.gitignore` and `.dockerignore`. Client secrets are masked in the UI and never exposed in client-side responses.
- **Zero-Config Resilience**: The container starts with zero initial dependencies. Credentials can be provided via environment variables, `.env`, or through the Web UI Settings.
- **Production Safety**: Existing production SIMs and configurations are preserved. Test creations default to the isolated APN `sasetest`.

---

## 📚 Architecture Guides

- [Operational Modes, 1-Click Demo Packs & Offline Resilience Guide](docs/OFFLINE_DEMO_AND_DEMO_PACKS.md)
- [5G Zero-Trust Subscriber Security Groups & Quarantine Architecture Guide](docs/5G_ZERO_TRUST_SECURITY_GROUPS_GUIDE.md)
- [SIDO Trade Show Demo Script (FR)](docs/DEMO_SCRIPT_CIO_STAND.FR.md) / [Demo Script (EN)](docs/DEMO_SCRIPT_CIO_STAND.EN.md)

---

## 📖 References

- [Strata Cloud Manager Portal](https://stratacloudmanager.paloaltonetworks.com)
- [Configure Prisma SASE 5G Documentation](https://docs.paloaltonetworks.com/sase/prisma-sase-multitenant-platform/manage-sase-5g/config-sase-5g)
- [Palo Alto Networks pan.dev SASE 5G API Reference](https://pan.dev/sase/api/manage-services-5g/post-mt-manage-5-g-register-ue/)
