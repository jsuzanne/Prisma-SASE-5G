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

- **🏭 7 Industry Verticals & Enterprise IoT Fleet Simulation**:
  - **7 Industry Verticals**: *Smart City & Utilities*, *Industrial IoT & Robotics*, *Connected Healthcare*, *Logistics & Fleet Tracking*, *Retail & Smart POS*, *Agritech & Environmental*, and *Energy & Smart Grid*.
  - **Auto-Enrich Fleet**: Automatically assign realistic IoT equipment profiles, industry badges, and icons to existing SIMs in SCM inventory with a single click—no duplicate SIMs or manual data entry needed.
  - **1-Click Quick Presets**: Instant form population in the Add SIM modal with realistic 3GPP IMSIs and Luhn-compliant IMEIs.
  - **Dual View Mode**: Switch seamlessly between **Industry Fleet View** (rich equipment names, vertical badges, icons) and **Raw SCM View** (unfiltered hardware identifiers).
  - **Clean Typography**: High-contrast, scannable layout designed specifically for live demonstrations on laptops, tablets, and 2K/4K presentation screens.
- **📊 5G SASE Summary Dashboard (Strata Cloud Manager Alignment)**:
  - **4 Top KPI Cards**: Total 5G Tenants, Total Bandwidth (Mbps), Total Configured Users, and 5G Network Interconnects (VLAN attachments Up/Down).
  - **Throughput Trend Chart**: Real-time dual-curve time-series monitoring with Ingress (Purple) and Egress (Cyan) bandwidth metrics over 1h, 24h, or 7d with interactive hover tooltips.
  - **UE Mappings 11-Column Table**: Exact replica of the Strata Cloud Manager 5G SASE Summary UE table with `Time added`, `IMSI`, `IMEI`, `APN`, `IPv4 Address`, `IPv6 Address`, `Tenant`, `Tenant Status`, `Status` (🟢 Active / 🔴 Inactive), `Region`, and `Groups`.
- **📱 SIM Cards & 5G Identities Management**:
  - **SCM-Style SIM Inventory**: Real-time table displaying IMSI, IMEI, APN, Live Session IP & Status, Tenant, Subscriber Groups, and Action buttons.
  - **Edit 5G Identity Modal**: Change IMSI, IMEI, APN, and assign/move SIMs between subscriber security groups (`Permissive`, `Restrictive`, or custom groups).
- **🛡️ 5G Identity Groups & Zero-Trust Policies**:
  - **Create Custom Groups**: Define new policy groups (e.g. `VIP-Sensors`, `Field-Workers`, `Finance-eSIMs`) with interactive member SIM selection.
  - **System Group Safeguards**: Built-in system groups (`Restrictive` and `Permissive`) are strictly protected with immutable locks against accidental deletion.
- **⚡ 5G Session Telemetry (Control & User Plane Correlation)**:
  - Real-time IP allocation telemetry injection (`POST /mt/manage/5g/register/ue`) and graceful session termination (`POST /mt/manage/5g/deregister/ue`).
  - Correlates mobile IP with IMSI/IMEI identifiers for instant Zero-Trust policy enforcement without endpoint agents.
- **🔍 Live API Inspector & Debug Console**:
  - Real-time request/response payload viewer with timestamped transaction logs.
  - **1-Click Copy cURL Command** and **Copy JSON Response** buttons for instant API troubleshooting.
  - Filter by HTTP method (`GET`, `POST`, `PUT`, `DELETE`), search by endpoint path/status, and export full JSON debug logs.
- **☀️ Light & 🌙 Dark Mode Support**:
  - High-contrast enterprise-grade Light Mode and refined Dark Mode accessible via 1-click toggle in top navigation bar.
- **🎨 Universal Carrier & Private 5G Co-Branding Customizer**:
  - Real-time **Carrier Primary Accent Color** customizer (6 pre-tuned swatches + HTML5 color picker).
  - 4 Dynamic **Background Atmospheres**: *Cyber 5G Core* (Deep Space Mesh), *Carrier Atmosphere* (accent radiant glow), *Enterprise Slate* (neutral minimal), and *Obsidian Midnight*.
  - Upload custom carrier logos and customize header partner taglines with real-time preview and persistence.
- **🔍 Display & Typography Scaling for 2K/4K Displays**:
  - Fluid responsive scaling designed for large 2K / 2560px / 4K screens and stage presentations.
  - Interactive header zoom toggle (`100%`, `115%`, `130%`) with preference saved in `localStorage`.
- **🏷️ Auto-Incrementing Dynamic Versioning & Changelog**:
  - Automatic build number calculation on every push (`2.3.<commit_count>`) displayed discreetly in header and Settings.
  - Interactive Release Notes & Changelog modal powered by [`CHANGELOG.md`](file:///CHANGELOG.md).
- **🌐 Direct Strata Cloud Manager Portal Link**:
  - Direct top-bar link to [https://stratacloudmanager.paloaltonetworks.com](https://stratacloudmanager.paloaltonetworks.com).
- **⚙️ In-App Settings & Credentials Manager**:
  - Manage service account credentials (`PANW_CLIENT_ID`, `PANW_CLIENT_SECRET`, `PANW_TSG_ID`, `DEFAULT_APN`) directly from the Web UI with security masking and a live connection test button.
- **📦 1-Click JSON Demo Packs & Offline Sandbox Mode**:
  - **1-Click JSON Export & Import**: Export the entire 5G topology (SIMs, hardware IMEIs, dynamic IPs, labels, security groups) to a single portable `.json` file and restore it with one click.
  - **Built-in Trade Show Scenarios**: Out-of-the-box presets for **Retail & Smart POS** (14 SIMs: Ingenico POS, Zebra scanners, Nedap RFID gates), **Smart Factory 4.0** (MiR250 AGVs, Siemens PLCs, Fanuc robots), and **EV Charging Infrastructure** (350kW DC chargers, AC chargers, OCPP gateways).
  - **100% Offline Standalone Sandbox Engine**: Optional zero-latency simulation engine enabling sales engineers and presenters to run complete 5G security demos without internet connectivity or SCM access.
  - **Anti-503 Snapshot Fallback**: Gracefully serves persistent local snapshots if cloud microservices experience temporary outages (`no healthy upstream`), with seamless automatic reconciliation when online.
- **🧪 Automated Lifecycle Runner & Test Suite**:
  - Interactive 8-step pipeline with live terminal output.
  - 63 automated unit tests with 100% passing rate on GitHub Actions CI.

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

## 🏭 Industry Verticals & Enterprise IoT Fleet Simulation

To make live demonstrations, customer proof-of-concepts, and executive presentations highly relatable to enterprise decision-makers and OT/IoT engineers, the portal provides **7 ready-to-use Industry Verticals**:

| Vertical | Icon | Sample Equipment Profiles | Enterprise Use Case & Value |
| :--- | :---: | :--- | :--- |
| **Smart City & Utilities** | 🏙️ | Connected CCTV Camera, Air Quality Station, Smart Water Meter, Streetlight Gateway, Waste Bin Level Sensor | Urban infrastructure & municipal sensor security |
| **Industrial IoT & Robotics** | 🏭 | Automated Guided Vehicle (AGV), Robotic Arm Controller, Predictive Vibration Sensor, PLC Gateway, Remote Telemetry Unit (RTU) | Factory automation & Industry 4.0 shop floor isolation |
| **Connected Healthcare** | 🏥 | Mobile Ultrasound Scanner, Remote Telemetry Monitor, Emergency Defibrillator, Smart Infusion Pump, Asset Tracking Tag | Hospital IoT, medical device micro-segmentation & HIPAA compliance |
| **Logistics & Fleet Tracking** | 🚚 | Heavy Fleet GPS Tracker, Cold Chain Thermometer, Autonomous Forklift, Rugged Handheld Scanner, Smart Container Lock | Supply chain telematics & roaming asset tracking |
| **Retail & Smart POS** | 🛒 | Mobile POS Terminal, Digital Signage Player, Interactive Kiosk, AI Smart Shelf Camera, Inventory RFID Gateway | Payment isolation (PCI-DSS) & digital store security |
| **Agritech & Environmental** | 🌱 | Soil Moisture Probe, Weather Station, Autonomous Drone Base, Precision Irrigation Valve, Livestock Biometric Sensor | Smart farming, remote telemetry & crop protection |
| **Energy & Smart Grid** | ⚡ | Solar Inverter Gateway, EV Ultra-Fast Charger, Grid Substation RTU, Wind Turbine Anemometer, Transformer Thermal Sensor | Critical national infrastructure (CNI) & smart energy |

### ✨ Auto-Enrich Existing SIM Fleet

Instead of generating duplicate fictitious SIM entries in Strata Cloud Manager (SCM), the **"Auto-Enrich Fleet"** button enriches your **actual registered SIM cards** in SCM inventory:
1. Click **"Auto-Enrich Fleet"** in the top action bar or **SIM Inventory** tab.
2. Select an **Industry Vertical** (e.g. *Industrial IoT & Robotics*) or choose **Random / Mixed Verticals**.
3. Choose an assignment strategy (*Equally across equipment* or *Random mix*).
4. Click **"Apply Fleet Enrichment"**. All existing SIMs will immediately display realistic device types (e.g. *Autonomous Guided Vehicle (AGV)*), vertical badges, and industry icons.

> [!NOTE]
> **Zero Impact on SCM Identity Integrity**: Palo Alto Networks SCM rejects unrecognized JSON attributes. The portal stores industry metadata locally in `config/sim_metadata.json` (correlated via IMSI) and preserves pure hardware payloads for outbound SCM API calls.

### 🔄 Dual View Mode: Industry Fleet vs Raw SCM

Toggle between two display modes instantly from the **SIM Inventory** toolbar:
- 🏭 **Industry Fleet View**: Displays equipment names, vertical badges, industry icons, and high-contrast typography.
- ⚙️ **Raw SCM View**: Displays pure hardware identifiers (unfiltered IMSI, IMEI, APN) exactly as seen in the Strata Cloud Manager portal.

---

## 📖 Complete Provisioning Walkthrough (Web UI vs CLI)

Provisioning a 5G subscriber into Palo Alto Networks Prisma SASE 5G consists of two essential phases:
1. **Control Plane Provisioning**: Mapping the SIM hardware identifiers (`IMSI`, `IMEI`, `APN`) and assigning security groups.
2. **User Plane / Session Enrichment**: Injecting real-time IP allocation telemetry when the SIM connects to the 5G Core network, binding Zero-Trust security policies instantly.

Below is the step-by-step lifecycle breakdown across the **Web UI** and the **CLI**:

---

### Step 1: Monitor 5G SASE Health & Interconnects

Inspect the global health of your 5G SASE tenant, allocated bandwidth, and VLAN attachments.

| Method | How to Perform / Where to View |
| :--- | :--- |
| 🌐 **Web UI** | Navigate to the **"5G SASE Summary"** tab to view the 4 KPI cards and Ingress/Egress Throughput trends. |
| 💻 **CLI** | `python3 manage_5g.py summary` and `python3 manage_5g.py interconnect` |

---

### Step 2: Manage 5G Identity Groups (Security Policies)

Inspect or create subscriber security groups that hold Zero-Trust policy profiles (e.g. `Restrictive`, `Permissive`, `VIP-Sensors`).

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

Assign or move the SIM card to a specific security policy group (`Permissive`, `Restrictive`, etc.).

| Method | How to Perform / Where to View |
| :--- | :--- |
| 🌐 **Web UI** | In the **"SIM Inventory"** tab, click the **Edit ✏️** button on any SIM row. In the modal, choose the desired **Subscriber Group** and click **Save**. |
| 💻 **CLI** | `python3 manage_5g.py assign-group --ue-id "<IDENTITY_ID>" --group-name "Permissive"`<br>`python3 manage_5g.py update "<IDENTITY_ID>" --apn "sase" --group-id "<GROUP_ID>"` |

---

### Step 5: Activate 5G Session Telemetry (IP Allocation / Data Plane)

When the IoT device connects to the 5G Core network, the carrier network assigns an IP address (e.g. `10.56.0.200`). The 5G Core notifies Prisma SASE 5G via REST telemetry to bind security policies in real time without any device agent or VPN client.

| Method | How to Perform / Where to View |
| :--- | :--- |
| 🌐 **Web UI** | In the **"SIM Inventory"** tab, click **"⚡ Attach"** next to the SIM to open the **5G Session Control** modal. The last-used IP address and CIDR pool are auto-suggested, and the real-time Session Event Console logs the UPF telemetry stream. |
| 💻 **CLI** | `python3 manage_5g.py session-register --imsi 208950123456789 --imei 860123123456789 --apn sasetest --ipv4 10.56.0.200` |

---

### Step 6: Threat Inspection & Policy Enforcement

When a device in the `Restrictive` group attempts to access malicious or unauthorized content (e.g. `wicar.org`):

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
python3 manage_5g.py assign-group --ue-id <IDENTITY_ID> --group-name "Permissive"
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

Run the test suite covering all REST endpoints, authentication, SIM CRUD, group creation, group assignment, API debug logging, and system protections:

```bash
# Run unit tests (43 passing tests)
./.venv/bin/python -m unittest discover tests -v

# Run end-to-end automated lifecycle test script
python3 test_lifecycle.py
```

---

## 📡 REST API Documentation

Interactive Swagger documentation is available at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | System health, TSG status, version, and token preview |
| `GET` | `/api/version` | Dynamic application version & Git commit build metadata |
| `GET` | `/api/changelog` | Retrieve full changelog and release notes in Markdown |
| `GET` | `/api/config` | Read current configuration (masked secret) |
| `POST` | `/api/config` | Update `.env` credentials dynamically |
| `POST` | `/api/config/test` | Test OAuth2 connection & tenant resolution |
| `GET` | `/api/tenants` | List tenant hierarchy (Root MSP and child TSGs) |
| `GET` | `/api/presets/verticals` | List all 7 industry verticals with equipment catalog |
| `GET` | `/api/presets/random` | Generate realistic Transatel IMSI, IMEI & device preset |
| `POST` | `/api/presets/enrich` | Auto-enrich existing registered SIMs with vertical profiles |
| `POST` | `/api/metadata/clear` | Clear local SIM industry metadata overlay |
| `GET` | `/api/ues` | List registered SIM cards with dynamic IP and status |
| `POST` | `/api/ues` | Register new SIM card (optional session IP attach) |
| `PUT` | `/api/ues/{id}` | Update SIM metadata and group assignment |
| `PUT` | `/api/ues/{id}/group` | Assign SIM to a specific subscriber group |
| `DELETE` | `/api/ues/{id}` | Safely delete a SIM card mapping |
| `GET` | `/api/groups` | Query subscriber security user groups |
| `POST` | `/api/groups` | Create a new 5G subscriber identity group |
| `GET` | `/api/groups/{id}` | Get group details and member identity list |
| `PUT` | `/api/groups/{id}` | Update group name or member list |
| `DELETE` | `/api/groups/{id}` | Delete a subscriber group (system groups protected) |
| `POST` | `/api/sessions/register` | Send 5G session attach / IP telemetry event |
| `POST` | `/api/sessions/deregister` | Send 5G session terminate event |
| `GET` | `/api/metrics/summary` | 5G SASE Summary KPI stats (Tenants, Bandwidth, Configured Users, Interconnects) |
| `GET` | `/api/metrics/throughput` | Real-time Ingress & Egress Throughput Trend time-series points |
| `GET` | `/api/mode` | Get current operational mode (`live` vs `standalone`) |
| `POST` | `/api/mode` | Toggle operational mode (`{"standalone_mode": true/false}`) |
| `GET` | `/api/demo/export` | Export complete fleet snapshot as portable JSON Demo Pack |
| `POST` | `/api/demo/import` | Import and apply a complete JSON Demo Pack |
| `GET` | `/api/demo/presets` | List built-in trade show scenarios (Retail, Factory, EV Hub) |
| `POST` | `/api/demo/presets/load/{id}` | Instant 1-click loading of a built-in scenario preset |
| `GET` | `/api/debug/logs` | Query real-time API inspector debug logs with cURL and responses |
| `POST` | `/api/debug/logs/clear` | Clear in-memory debug log buffer |
| `POST` | `/api/lifecycle/run` | Execute full 8-step lifecycle test pipeline |

---

## 🔒 Security & Protection Policies

- **Protected System Groups**: The built-in security profiles (`Restrictive` and `Permissive`) are locked against accidental deletion via the UI, API, and CLI.
- **Credential Privacy**: `.env` is ignored by `.gitignore` and `.dockerignore`. Client secrets are masked in the UI and never exposed in client-side responses.
- **Zero-Config Resilience**: The container starts with zero initial dependencies. Credentials can be provided via environment variables, `.env`, or through the Web UI Settings.
- **Production Safety**: Existing production SIMs and configurations are preserved. Test creations default to the isolated APN `sasetest`.

---

## 📚 Architecture Guides

- [Operational Modes, 1-Click Demo Packs & Offline Resilience Guide](docs/OFFLINE_DEMO_AND_DEMO_PACKS.md)
- [5G Zero-Trust Subscriber Security Groups & Quarantine Architecture Guide](docs/5G_ZERO_TRUST_SECURITY_GROUPS_GUIDE.md)

---

## 📖 References

- [Strata Cloud Manager Portal](https://stratacloudmanager.paloaltonetworks.com)
- [Configure Prisma SASE 5G Documentation](https://docs.paloaltonetworks.com/sase/prisma-sase-multitenant-platform/manage-sase-5g/config-sase-5g)
- [Palo Alto Networks pan.dev SASE 5G API Reference](https://pan.dev/sase/api/manage-services-5g/post-mt-manage-5-g-register-ue/)
