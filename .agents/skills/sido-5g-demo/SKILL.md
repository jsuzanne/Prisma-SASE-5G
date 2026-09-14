---
name: sido-5g-demo
description: >-
  Interactive guide, storytelling script, and operational runbook for demonstrating
  Palo Alto Networks Prisma SASE 5G integrated with Transatel NTT 5G Core at SIDO Lyon
  and IoT/Industry 4.0 trade shows. Covers agentless zero-touch security, fleet simulation,
  subscriber policy group shifts (Permissive vs Restrictive), real-time session telemetry,
  and Strata Cloud Manager (SCM) log correlation.
---

# SIDO Lyon: Prisma SASE 5G Live Demonstration Guide

This skill provides the comprehensive pitch, storytelling narrative, live demonstration steps, and operational procedures for showcasing **Palo Alto Networks Prisma SASE 5G** with **Transatel (NTT)** mobile connectivity at IoT and Industry 4.0 events (such as SIDO Lyon).

---

## 🎯 The Storytelling & Pitch Framework

### Theme: *"The Connected Fleet, Protected by Design"*

> "Today, when enterprises deploy connected equipment in the field—whether it is maintenance tablets for field technicians, EV charging stations, industrial robots, or retail payment terminals—they face two fundamental challenges:
> 1. Connecting them reliably across the globe without friction.
> 2. Ensuring they never become a gateway for cyberattacks or lateral movement.
>
> **Transatel (NTT)** provides instant, carrier-grade global 5G connectivity.
> **Prisma SASE 5G by Palo Alto Networks** provides the invisible armor.
> 
> Without installing any antivirus, software agent, or VPN client on the device, enterprise-grade security is directly embedded into the 5G core network."

---

## 🎭 Step-by-Step Live Demo Choreography

### Step 1: The Hook (The Problem) — *Prop: iPad / Device in hand*
- **Script:** *"Imagine this is a business tablet assigned to a field technician, or the edge controller of an industrial robot. It is equipped with a Transatel 5G eSIM. The moment it powers on, it connects directly to the network. But what happens if the user clicks on a phishing email, visits an unauthorized streaming site, or gets infected? Without core network security, security teams are flying blind."*
- **Action on Screen:** Open the **SIM Inventory** tab in the Prisma SASE 5G Manager. Show the tablet's record tagged with its demo memo: `[📱 Field Tech iPad - Stand SIDO]`.

---

### Step 2: The "Permissive" Experience (Business as Usual)
- **Script:** *"Here, our iPad is assigned to the 'Permissive' subscriber group—typical for an operational employee who needs broad internet and SaaS access (Salesforce, ServiceNow, Microsoft 365). The experience is fast, native, and frictionless. Transatel's 5G core routes the traffic cleanly. The user doesn't have to launch a VPN or log in to a security agent."*
- **Action on iPad:** Browse to a standard corporate website or SaaS dashboard. Traffic flows smoothly.

---

### Step 3: The Instant Shift to Zero-Trust (The "Restrictive" Lockdown)
- **Script:** *"Now imagine this device is repurposed as an unattended Kiosk or critical EV charging controller. We reassign it to our 'Restrictive' Zero-Trust group directly in our management portal."*
- **Action on Portal:** Click **Edit** on the SIM row or click the group badge, select `Restrictive`, and click **Save**.
- **Action on iPad:** Try to access a restricted destination (e.g. YouTube, Netflix) or malware simulation test site ([wicar.org](http://wicar.org)).
- **The Result:** The **Palo Alto Networks Block Page** appears instantly on the iPad!
- **The 'Aha!' Moment:** *"Notice this: there is NO software agent, NO profile, and NO antivirus installed on this iPad. The blocking happens directly in the 5G core network in real time thanks to the API integration between Transatel and Palo Alto Networks."*

---

### Step 4: Behind the Scenes (Zero-Touch Provisioning & SCM Telemetry)
- **Script:** *"How does Strata Cloud Manager know this IP address belongs to this specific iPad? Automation. When Transatel brings a SIM online, their network API sends the IP allocation telemetry to Prisma Access in real time. Palo Alto binds the mobile IP to the IMSI and instantly enforces the security policy. True Zero-Touch provisioning for 10,000+ SIMs."*
- **Action on Screen:** 
  1. Show the **5G SASE Summary** dashboard (KPIs, active UE mappings, throughput trends).
  2. Show the **API Inspector / Debugger** tab showing the live `/mt/manage/5g/register/ue` telemetry payload.
  3. Turn to the **Strata Cloud Manager** console to show unified activity and threat logs.

---

## 🏭 Industry Verticals & Demo Presets Reference

Use these vertical presets during discussions with prospective clients at the booth:

| Vertical | Typical Equipment | Recommended Security Group | Live Pitch Angle |
| :--- | :--- | :--- | :--- |
| **⚡ EV Infrastructure** | EVSE Fast-Charger OCPI Gateway, 350kW Hub Unit | `Restrictive (Zero-Trust IoT)` | Protect charging payments and prevent malicious firmware injection into the electrical grid. |
| **🤖 Manufacturing / 4.0** | KUKA Robotic Arm, Autonomous Mobile Robot (AGV) | `Restrictive (IoT / OT)` | Prevent lateral movement from compromised floor robots into SCADA / MES networks. |
| **💳 Retail & POS** | Ingenico Smart POS, Self-Checkout Kiosk | `Restrictive (PCI-DSS Kiosk)` | Strict lockdown ensuring payment terminals can only communicate with authorized payment gateways. |
| **✈️ Aviation & Ground Ops** | Avionics Maintenance iPad, Ground Power Unit | `Permissive` (iPad) / `Restrictive` (GPU) | Mixed-fleet management: permissive for crew tablets, locked-down for tarmac IoT equipment. |
| **🚗 Automotive & Telematics** | Vehicle Telematics Unit (TCU), Fleet OBD Tracker | `Restrictive (Telemetry)` | Secure over-the-air (OTA) updates and protect CAN-bus telemetry against hijacking. |
| **🚌 Public Transport** | Bus Multi-WAN Gateway, Contactless Validator | `Permissive` (Passenger Wi-Fi) / `Restrictive` (Validator) | Network slicing / multi-group separation between public passenger Wi-Fi and ticketing telemetry. |
| **🏙️ Smart City & Utilities** | Smart Water Meter, Intelligent Streetlight Gateway | `Restrictive (Critical Infrastructure)` | Ultra-low power NB-IoT/5G telemetry with tamper-proof core security. |

---

## 💻 Portal & CLI Quick Operations

### 1. Launching the Local Demo Server
```bash
# Start container with Docker Compose (with persistent volume)
docker compose up -d --build

# Open Web UI
open http://localhost:8000
```

### 2. Auto-Populating Fleets for Live Booth Demos
- Use the **`⚡ Auto-Populate Fleet`** button in the Web UI to generate ready-to-use devices for a specific industry or a complete multi-vertical fleet.
- Or trigger via API:
```bash
# Populate 3 EV Charging Stations
curl -X POST http://localhost:8000/api/presets/populate \
  -H "Content-Type: application/json" \
  -d '{"vertical_id": "ev_infrastructure", "count": 3, "auto_attach_session": true}'

# Populate 1 device for each of the 7 verticals
curl -X POST http://localhost:8000/api/presets/populate \
  -H "Content-Type: application/json" \
  -d '{"vertical_id": "all", "auto_attach_session": true}'
```

### 3. Trade Show Offline Resilience & 1-Click Demo Packs
- **No Wi-Fi / Cloud Outage Protection**: If trade show internet is degraded or SCM cloud experiences maintenance (`503`), toggle **Standalone Sandbox Mode** in **Settings ➔ Operational Engine & Mode**.
- **1-Click Scenario Activation**: Click **Demo Packs** in the SIM Inventory toolbar and select:
  - 🛒 **Retail & Smart POS** (14 SIMs: Ingenico terminals, Zebra scanners, RFID gates).
  - 🏭 **Smart Factory 4.0** (MiR250 AGVs, Siemens PLCs, Fanuc robots).
  - ⚡ **EV Charging Hub** (350kW DC fast chargers, AC chargers, payment gateways).
- **Zero-Latency Realism**: All operations generate authentic cURL commands and simulated 3GPP/SASE 200 OK responses in the Live API Inspector console.

### 4. Resetting to Clean / Raw SCM Mode
- Click the **`Reset Metadata`** button in the UI or run:
```bash
curl -X POST http://localhost:8000/api/metadata/clear
```
