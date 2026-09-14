# Changelog

All notable changes to **Prisma SASE 5G Manager** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.6] - 2026-09-14

### Added & Improved
- **Dashboard Real-Time Refresh Status & Auto-Refresh Interval Engine**:
  - **Live Sync Status Badge in Top Navbar**: Added real-time timestamp display (`HH:MM:SS`) with dynamic relative elapsed time ticker (`(just now)`, `(15s ago)`, `(2m ago)`) and glowing status beacon (🟢 Fresh < 60s, 🟡 Aging 1-3m, ⚪ Muted > 3m).
  - **Configurable Auto-Refresh Interval**: Added periodic background refresh dropdown selector in navbar (`Off`, `15s`, `30s`, `1m`, `5m`) with local persistence and tab-visibility awareness.
  - **Per-Section Sync Indicators**: Added synchronized timestamp labels in **5G SASE Summary** (`Updated: HH:MM:SS`), **SIM Inventory** (`Synced: HH:MM:SS`), and **Security Groups & Rules** toolbars.
  - **Individual Groups Quick Refresh**: Added direct quick-refresh button `refreshGroups()` for Security Policy Groups.
  - **Light Mode High-Contrast Styling**: Tailored CSS tokens for the sync badge, auto-refresh dropdown, and timestamp indicators across light and dark themes.

---

## [2.3.5] - 2026-09-14

### Added & Improved
- **1-Click SCM Cloud Bulk Provisioning & Fleet Synchronization**:
  - **Automated SCM Cloud Provisioning Pipeline**: Added `bulk_provision_fleet` in `Prisma5GClient` and `POST /api/demo/bulk-provision` to automatically create missing SCM user groups (`POST /mt/manage/5g/userGroup`), register SIM hardware identifiers (`POST /mt/manage/5g/tenantUEInfo`), assign member identities to security groups (`PUT /mt/manage/5g/userGroup/{id}`), and inject active 5G session telemetry (`POST /mt/manage/5g/register/ue`).
  - **Import with Instant Cloud Sync**: Added `[x] Also Bulk Provision to SCM Cloud upon import` checkbox in Demo Packs modal to automatically sync imported topologies with Palo Alto Networks Strata Cloud Manager.
  - **1-Click Active Fleet Push**: Added `🚀 Push Active Fleet to SCM Cloud` button in Demo Packs modal for on-demand cloud deployment.
  - **Automated Test Coverage**: Added `tests/test_bulk_provision.py` bringing total automated test suite to 66 passing tests.

---

## [2.3.4] - 2026-09-14

### Added & Improved
- **1-Click JSON Demo Packs & 100% Offline Standalone Sandbox Mode**:
  - **1-Click Demo Pack Import/Export**: Export the complete 5G fleet setup (SIM cards, live sessions, IP allocations, policy groups) into a single portable `.json` file and restore it instantly with one click.
  - **Built-in Trade Show Scenarios**: Out-of-the-box presets for **Retail & POS**, **Smart Factory 4.0 (Robotics & AGVs)**, and **EV Charging Hub**.
  - **100% Offline Standalone Sandbox Mode**: Optional toggle in Settings allowing sales engineers and presenters to perform full, zero-latency 5G security demos without internet or SCM connectivity.
  - **Real-time Live API Simulation**: Standalone mode generates realistic 3GPP and Palo Alto SASE responses while feeding full cURL requests and 200 OK responses to the live API Inspector.
  - **Default Setting**: Live SCM Cloud API remains the strict default operational mode.

---

## [2.3.3] - 2026-09-14

### Added & Improved
- **Offline & Cloud Outage Resilience (Anti-503 Snapshot Fallback)**:
  - Added automatic graceful fallback when Palo Alto SCM 5G microservices return `503 Service Unavailable` (`no healthy upstream`).
  - Automatically serves persistent local snapshots for SIM inventory (`/api/ues`), user groups (`/api/groups`), and tenant hierarchy (`/api/tenants`) using `active_sessions.json` and `sim_metadata.json`.
  - Added discreet UI resilience indicator (`⚡ Local Snapshot`) in the SIM Inventory toolbar when offline cache is serving data.
  - Transparent simulated session attach/detach and group updates in offline demo mode.

---

## [2.3.2] - 2026-09-13

### Added & Improved
- **Interactive Multi-Column Sorting in Group Modals**:
  - Added interactive column headers (`Selection/Assigned`, `IMSI`, `IP Address`, `Device Label`, `APN`) in **Create 5G Identity Group** and **Edit 5G Identity Group** modals.
  - Clicking any column header triggers sorting (`▲` / `▼`) while seamlessly preserving all selected checkbox states.
- **Dynamic 5G Session Modal Button Prominence**:
  - Context-aware action buttons: clicking **Detach** highlights the Detach action as primary (vibrant rose gradient), while clicking **Attach** highlights Attach (vibrant amber gradient).
  - Replaced native browser confirm popups on SIM row detachment with the full 5G Session Telemetry window & live log console.
- **Refined Group Modal Layout**:
  - Rebalanced modal width and eliminated excessive white space between IP and APN columns.
  - Aligned SIM card fields: `[Checkbox] [IMSI] [IP Address] [Device Label] [APN]` omitting generic equipment type text.

---

## [2.3.1] - 2026-09-12

### Added
- **Interactive Column Sorting**:
  - Full interactive column sorting (ascending `▲` / descending `▼`) across all 11 columns of **5G Summary ➔ UE Mappings** (Time, IMSI, IMEI, APN, IPv4 numerical octets, IPv6, Tenant, Tenant Status, Status, Region, Groups).
  - Column sorting in **SIM Inventory** across both *Industry Fleet View* and *Raw SCM View*.
  - Visual sort indicators and active column highlighting with graceful handling of non-sortable action buttons.

### Changed & Fixed
- **Unlocked Security Groups**:
  - Removed hardcoded `Built-in` restrictions on system groups (`Permissive`, `Restrictive`, `Restrictive-Updated`), enabling standard editing, renaming, and deletion.
- **Light Mode UI Polish**:
  - Fixed high-contrast text rendering on table headers upon mouse hover (`thead th:hover`) in Light Mode, preventing white-on-light illegibility.
- **Custom Demo Memo & Session Telemetry Safeguards**:
  - Automatic preservation of custom demo labels (`custom_label`, e.g. `iphone`, `ipad`) and last-known IP allocations during fleet re-enrichment or vertical shifts.
  - Synchronized default active 5G session allocations with live Strata Cloud Manager (SCM) state.

---

## [2.3.0] - 2026-09-12

### Changed & Streamlined
- **5G Session Lifecycle & Dataplane Telemetry Alignment**:
  - Streamlined UI by focusing real-time operations on the native 5G Session Telemetry lifecycle (`[⚡ Attach]` and `[⏻ Detach]`).
  - Removed redundant Fast-Path Sync modal and button to avoid operator confusion with Cloud Identity Engine (CIE) directory group recalculation.
  - Reinforced sub-2-second emergency threat containment and quarantine via instant 5G session detachment / lease invalidation on the SASE enforcement dataplane.

---

## [2.2.0] - 2026-09-12

### Added
- **Light & Dark Theme Switcher**:
  - Added an interactive theme toggle button in the top navigation bar menu next to the font size selector.
  - Introduced a clean, high-contrast, enterprise-grade **Light Mode** styling while preserving 100% of the fine-tuned Dark Mode.
  - Implemented persistent theme storage via `localStorage` with zero-flash early initialization.
- **Universal Carrier & MSSP Background & Color Customizer**:
  - Added real-time **Carrier Primary Accent Color** picker with 6 quick swatches (Transatel NTT Purple, PANW Orange, Telco Orange, Cyber Cyan, Emerald Green, Telecom Crimson) and custom HTML5 color picker.
  - Added dynamic **Background Atmosphere** engine supporting *Cyber 5G Core* (Deep Space Mesh), *Carrier Atmosphere* (accent-tinted radiant glow), *Enterprise Slate* (neutral minimal), and *Obsidian Midnight*.
  - Updated live header co-branding preview and header partner badge with dynamic accent border, glow, and subtitle colors.

---

## [2.1.0] - 2026-09-11

### Added
- **Interactive 5G Session Modal & Navbar Streamlining**:
  - Removed standalone 5G Sessions tab to streamline navigation into 5 clean core views (*5G Summary*, *SIM Inventory*, *Groups & Policies*, *Lifecycle*, *Settings*).
  - Transformed 5G Session control into an on-demand modal popup (`#modal-session`) accessible directly from any SIM card in the SIM Inventory via `[⚡ Attach]` / `[⏻ Detach]`.
  - Added live 3-node architecture flow (*IoT Device ➔ Telecom 5G Core UPF ➔ Prisma SASE*) and real-time **Session Event Console** directly inside the modal.
  - Automatically re-suggests the last-used IP address when re-attaching a detached SIM.
- **Configurable UE CIDR IP Pool Allocation**:
  - Configurable UE CIDR block settings (`config/config.json` and Settings tab) enforcing valid IP ranges (e.g. `10.56.0.192/27, 10.56.0.224/27`).
  - Added real-time frontend CIDR validator and *"Next Free IP"* selector during SIM creation and session registration.
- **Subscriber Policy Group Descriptions & Editing**:
  - Dedicated Group Edit Modal to update group names, descriptions, and member SIM assignments.
  - Clear group purpose & description visible directly in the Groups & Policies list table.
  - Default SIM selection starts unchecked in Add Group modal.
- **Dynamic Session-Correlated 5G Throughput & Telemetry**:
  - Dynamically scale 5G SASE Summary throughput curve (Ingress / Egress Kbps) and peak bandwidth based on live active SIM sessions.
  - Added real-time active SIM session counter badge in SVG throughput trend crosshair tooltip.
  - Automatic throughput chart re-rendering when sessions attach, terminate, or when running the automated 8-stage lifecycle test.
  - Idle baseline keepalives (~0 Kbps) displayed when no active subscriber sessions are connected.

### Fixed
- Fixed tab container nesting in `templates/index.html` ensuring reliable tab switching across all views.

---

## [2.0.0] - 2026-09-11

### Added
- **5G IoT Industry Presets & Fleet Auto-Enrichment**:
  - Added 7 industry verticals: *Smart City & Utilities*, *Industrial IoT & Robotics*, *Connected Healthcare*, *Logistics & Fleet Tracking*, *Retail & Smart POS*, *Agritech & Environmental*, and *Energy & Smart Grid*.
  - **Auto-Enrich Fleet** feature to automatically assign industry device profiles to existing SIMs in SCM inventory without creating duplicates.
  - Realistic Transatel NTT IMSI generator (`generate_transatel_imsi`) and Luhn-compliant IMEI generator (`generate_valid_imei`).
  - Dual SIM table view switch (*Industry Fleet View* vs. *Raw SCM View*).
  - Clear, high-contrast typography in the SIM table optimized for small and large screens.
- **English Localization**:
  - Full English translation across all UI components, modals, CLI prompts, and API response messages.
- **Unit Test Suite**:
  - Added `tests/test_presets_and_metadata.py` validating preset integrity, Luhn algorithms, and metadata correlation.

---

## [1.3.0] - 2026-09-10

### Added
- **Persistent Configuration Storage**:
  - Added persistent configuration directory (`config/config.json`) and Docker volume mount support.
  - Optional `.env` file support for 1-click zero-config installations.
- **Active 5G Sessions Alignment**:
  - Aligned 3 live active SIM sessions with SCM telemetry.
  - Cache invalidation and instant refresh button for SIM inventory with spinning animations.

### Fixed
- Protected client secret and credentials handling across frontend and backend.
- Made 5G Summary refresh button explicitly invalidate server cache.

---

## [1.2.0] - 2026-09-10

### Added
- **Display & Typography Scaling**:
  - Dynamic font size scaling controls (*Standard 100%*, *Comfortable 115%*, *Large 130%*) for 2K/4K high-resolution monitors and presentation displays.
- **MSSP & Carrier Co-Branding**:
  - Top header co-branding for Transatel (NTT) and Aeris Communications with custom branding presets.
- **Strata Cloud Manager (SCM) 11-Column UE Mappings Table**:
  - Replicated exact SCM portal layout with dynamic SIM IP allocation and active status correlation.
- **Branding Assets**:
  - Modern SVG, PNG, and ICO favicons with PANW Flame and 5G Core styling.

### Fixed
- Fixed UE mappings rendering error and added interactive tenant switcher dropdown in the active hierarchy banner.
- Resolved header responsiveness issues to keep all right-side status indicators permanently visible without horizontal scrolling.

---

## [1.1.0] - 2026-09-10

### Added
- **Live API Inspector & Debug Console**:
  - Real-time logging of HTTP request/response payloads with 1-click cURL clipboard copy.
- **5G Identity Groups Management**:
  - SCM-aligned SIM Group assignment and dynamic group creation/deletion.
  - Protected built-in system groups (`Restrictive` and `Permissive`).
- **5G SASE Summary Dashboard**:
  - Real-time throughput trend charts, connected device breakdown, and active alerts overview.

### Fixed
- Resolved SCM 400 validation by requiring and auto-assigning initial SIM identities when creating 5G groups.
- Added credential fallback in `/api/config/test` when secret is left empty.

---

## [1.0.0] - 2026-09-09

### Added
- **Initial Release of Prisma SASE 5G Toolkit**:
  - Complete Python SDK client for Palo Alto Networks Strata Cloud Manager (SCM) 5G UE APIs.
  - CLI management tool (`manage_5g.py`) with lifecycle test automation (`test_lifecycle.py`).
  - FastAPI asynchronous web server (`app.py`) with interactive UI.
  - CI/CD automated pipeline via GitHub Actions (`.github/workflows/ci.yml`) publishing multi-architecture Docker images (`linux/amd64`, `linux/arm64`) to Docker Hub (`jsuzanne/prisma-5g-sase:latest`).
