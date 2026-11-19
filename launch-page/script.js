/* ============================================================
   Stigix × Prisma SASE 5G — Launch Portal Interactions
   ============================================================ */

(function () {
  'use strict';

  // 1. Native <dialog> Triggers & Mandatory Light-Dismiss Fallback
  const triggers = document.querySelectorAll('[data-dialog-target]');
  triggers.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-dialog-target');
      const dialog = document.getElementById(targetId);
      if (dialog && typeof dialog.showModal === 'function') {
        dialog.showModal();
      }
    });
  });

  const dialogs = document.querySelectorAll('dialog.portal-dialog');
  dialogs.forEach((dialog) => {
    // Reset returnValue on close to avoid stale values leaking across invocations
    dialog.addEventListener('close', () => {
      dialog.returnValue = '';
    });
  });

  // Fallback for browsers that do not yet support declarative closedby="any"
  if (typeof HTMLDialogElement !== 'undefined' && !('closedBy' in HTMLDialogElement.prototype)) {
    dialogs.forEach((dialog) => {
      dialog.addEventListener('click', (event) => {
        if (event.target !== dialog) return;
        const rect = dialog.getBoundingClientRect();
        const isDialogContent =
          rect.top <= event.clientY &&
          event.clientY <= rect.top + rect.height &&
          rect.left <= event.clientX &&
          event.clientX <= rect.left + rect.width;
        if (isDialogContent) return;
        dialog.close();
      });
    });
  }

  // 2. Design Style Mode Switcher (Prisma AIRS vs Stigix Blueprint)
  const styleBtn = document.getElementById('btn-style-toggle');
  const styleLabel = document.getElementById('style-mode-label');
  if (styleBtn && styleLabel) {
    styleBtn.addEventListener('click', () => {
      const html = document.documentElement;
      const current = html.getAttribute('data-style-mode') || 'airs';
      const next = current === 'airs' ? 'stigix' : 'airs';
      html.setAttribute('data-style-mode', next);
      styleLabel.textContent = next === 'airs' ? 'Design: Prisma AIRS' : 'Design: Stigix.io';
    });
  }

  // 3. Scrollspy for Right-Hand "ON THIS PAGE" Navigation Rail
  const tocLinks = document.querySelectorAll('.page-toc__link');
  const sections = ['environments', 'architecture', 'components', 'walkthroughs']
    .map((id) => document.getElementById(id))
    .filter(Boolean);

  if ('IntersectionObserver' in window && sections.length > 0) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const activeId = '#' + entry.target.id;
            tocLinks.forEach((link) => {
              link.classList.toggle('is-active', link.getAttribute('href') === activeId);
            });
          }
        });
      },
      { rootMargin: '-20% 0px -65% 0px', threshold: 0.05 }
    );
    sections.forEach((sec) => observer.observe(sec));
  }

  // 4. Bilingual FR / EN Toggle
  const i18n = {
    fr: {
      eyebrow: 'Private 5G Core · UERANSIM RAN · Prisma SASE 5G · Stigix Traffic Engine',
      hero_title: '5G Zero-Trust SASE & Traffic Validation Lab',
      hero_subtitle:
        'Portail de lancement unifié pour orchestrer de bout en bout vos équipements 5G (UE/eSIM), piloter les VMs 5G Core (Open5GS) & Radio (UERANSIM), synchroniser les identités Palo Alto Networks Prisma SASE 5G et injecter du trafic applicatif & menaces L4/L7 avec Stigix.',
      sec_env_title: 'Playground Environments',
      sec_env_meta: '2 PLATEFORMES ACTIVES · TUNNELS CLOUDFLARE ZERO-TRUST',
      orch_desc:
        "Pilote central des <strong>VMs 5G Core (Open5GS)</strong> et <strong>5G RAN (UERANSIM)</strong> couplé à <strong>Palo Alto Networks Strata Cloud Manager (SCM)</strong>. Permet de provisionner des flottes d'équipements 5G par verticale métier en un clic et d'automatiser la corrélation IP ⇄ Identité SASE.",
      orch_b1:
        '<strong>VM 5G Core (Open5GS + MongoDB) :</strong> Création automatique des abonnés SIM (IMSI, clés K/OPc, profil QoS 5QI, Slice S-NSSAI SST/SD) et télémétrie SMF/AMF en temps réel.',
      orch_b2:
        '<strong>VM 5G RAN (UERANSIM Agent) :</strong> Génération dynamique des YAML radio, démarrage des démons <code>nr-ue</code> et montée des interfaces tunnels dédiées <code>uesimtunX</code>.',
      orch_b3:
        '<strong>Corrélation Prisma SASE 5G :</strong> Réconciliation continue à 4 sources (SCM ⇄ Mongo ⇄ SMF ⇄ RAN) et binding IP dynamique (<code>/uesession/register</code>) pour appliquer les politiques Zero-Trust sans agent.',
      btn_launch_orch: 'Lancer 5G Orchestrator',
      lab_desc:
        "Plateforme de génération de trafic applicatif L4/L7, de simulation d'attaques et d'observabilité réseau <strong>Stigix</strong> rattachée au plan utilisateur 5G. Génère des flux réalistes directement à travers les tunnels radio <code>uesimtun*</code> vers Prisma SASE 5G.",
      lab_b1:
        '<strong>Génération de Trafic SaaS & Vertical :</strong> Flux HTTPS/SaaS, Custom TCP, flux industriels (Modbus/MQTT/RTSP), VoIP RTP (calcul MOS/Jitter) et rejeu Stateful PCAP.',
      lab_b2:
        "<strong>Validation Sécurité & Zero-Trust :</strong> Audit de filtrage d'URL, DNS Tunneling, téléchargement EICAR, scénarios Command & Control (C2) et tests AI Security / DLP pour vérifier le blocage dans SCM.",
      lab_b3:
        '<strong>Web Wireshark & Sondes DEM :</strong> Capture de paquets en direct sur les interfaces 5G, analyse protocolaire dans le navigateur et mesure de performance bout-en-bout.',
      btn_launch_lab: 'Lancer Stigix 5G Lab',
      btn_details: 'Architecture & Rôles',
      sec_arch_title: 'Architecture Diagrams & Call Flows',
      sec_arch_meta: 'CLIQUEZ SUR UN NŒUD OU UNE TUILE POUR INSPECTER LES SCHÉMAS',
      flow_banner_title: 'CHAÎNE DE TRAITEMENT BOUT-EN-BOUT (RAN ➔ CORE ➔ PRISMA SASE 5G ➔ STIGIX TRAFFIC)',
      flow_1_desc: "Émule l'antenne gNodeB et les modems 5G (UE). Crée une interface tunnel Linux dédiée par carte SIM active.",
      flow_2_desc: 'Authentifie les SIMs (K/OPc), établit les sessions PDU IPv4, applique le Slicing (SST/SD) et route le trafic GTP-U.',
      flow_3_desc: "Corrèle l'IP dynamique de session avec l'identité 5G (IMSI/IMEI) et applique les règles Zero-Trust par groupe.",
      flow_4_desc: "Injecte du trafic métier et des menaces dans chaque tunnel UE pour démontrer l'inspection et le blocage en temps réel.",
      tile_1_title: 'Topologie 5G Core & RAN',
      tile_1_sub: 'Architecture bi-VM Open5GS, UERANSIM & Tunnels N2/N3/N6',
      tile_2_title: 'Cycle de Vie Zero-Trust (7 Étapes)',
      tile_2_sub: 'Du provisionnement SIM au binding IP dynamique dans SCM',
      tile_3_title: 'Réconciliateur Ground-Truth',
      tile_3_sub: 'Synchronisation temps réel SCM ⇄ MongoDB ⇄ SMF/AMF ⇄ RAN',
      tile_4_title: 'Slicing 5G & Verticales IoT',
      tile_4_sub: 'Profils Industry 4.0, Smart City, Santé, Retail POS & EV Infra',
      sec_comp_title: "Rôle des Composants de l'Infrastructure",
      sec_comp_meta: 'GUIDE EXPLICATIF DES BRIQUES TECHNIQUES DU LAB',
      comp_1_desc:
        "Cerveau d'orchestration hébergé sur la VM Core (exposé via <code>5gorchestrator.stigix.io</code>). Il unifie en une seule interface Web et API REST la création des cartes SIM dans le cœur 5G, le pilotage à distance des modems radio et l'enregistrement des identités/sessions dans Prisma SASE 5G.",
      comp_2_desc:
        "Cœur de réseau mobile 5G Standalone (3GPP Release 17). La base <strong>MongoDB</strong> stocke les abonnés (IMSI, clés K/OPc, QoS 5QI, débit AMBR). L'<strong>AMF</strong> gère l'attachement radio (N1/N2), le <strong>SMF</strong> alloue les IP de session PDU (<code>10.45.0.x</code>) et l'<strong>UPF</strong> achemine les paquets utilisateur (N3/N6).",
      comp_3_desc:
        "Simulateur d'accès radio 5G hébergeant la station de base <code>nr-gnb</code> et le micro-service <strong>RAN Agent</strong>. À chaque demande de l'Orchestrator, l'agent génère le fichier YAML du terminal, lance un processus <code>nr-ue</code> supervisé et monte une interface réseau dédiée (<code>uesimtun0</code>, <code>uesimtun1</code>…).",
      comp_4_desc:
        "Solution cloud Palo Alto Networks gérée depuis <strong>Strata Cloud Manager</strong>. Permet d'appliquer des politiques de sécurité Zero-Trust granulaires basées sur l'identité matérielle et SIM (<strong>IMSI, IMEI, APN, Groupe d'abonnés</strong>) sans aucun agent logiciel requis sur les objets connectés (IoT/OT).",
      comp_5_desc:
        "Accessible sur <code>stigix5glab.stigix.io</code>, cette instance <strong>Stigix</strong> génère du trafic applicatif continu et des scénarios d'attaque (EICAR, C2, DNS Tunneling, URL Filtering, DLP) à travers l'infrastructure 5G afin de peupler les tableaux de bord SCM et prouver l'efficacité des règles de sécurité en direct.",
      comp_6_desc:
        'Expose de manière sécurisée en HTTPS les interfaces de contrôle du lab (<code>5gorchestrator.stigix.io</code> et <code>stigix5glab.stigix.io</code>) via des tunnels sortants chiffrés <code>cloudflared</code>, sans ouvrir aucun port entrant public (MongoDB 27017 et Open5GS 9090 restent isolés en loopback local).',
      sec_walk_title: 'Guided Walkthroughs & Demo Scenarios',
      sec_walk_meta: 'PARCOURS DE DÉMONSTRATION RECOMMANDÉS (SIDO / EXECUTIVE BRIEFINGS)',
      walk_1_title: 'Scénario 1 · Onboarding Flotte 5G en 1 Clic',
      walk_1_desc:
        'Ouvrez <strong>5G Orchestrator</strong>, sélectionnez un preset métier (ex: <em>Robot Industry 4.0</em> ou <em>Borne EVSE</em>) et cliquez sur <strong>Register & Attach</strong>. Observez le provisionnement simultané dans MongoDB (Open5GS), le démarrage du modem <code>nr-ue</code> sur la VM RAN et la montée de la session IP dans Prisma SASE 5G.',
      walk_2_title: 'Scénario 2 · Bascule Zero-Trust (Permissive ➔ Restrictive)',
      walk_2_desc:
        "Dans <strong>5G Orchestrator</strong>, déplacez une SIM active d'un groupe <em>Permissive-IoT</em> vers un groupe <em>Quarantine / Restrictive</em>. Sans toucher au terminal 5G ni couper sa session radio, Prisma SASE 5G adapte instantanément la politique de filtrage appliquée à son flux IP.",
      walk_3_title: 'Scénario 3 · Génération de Trafic & Audit de Menaces',
      walk_3_desc:
        'Ouvrez <strong>Stigix 5G Lab</strong> pour lancer des flux applicatifs SaaS, des tests de prévention de menaces (EICAR, C2, DNS Tunneling) ou inspecter les paquets GTP/IP avec <strong>Web Wireshark</strong>, puis corrélez les journaux de sécurité dans Strata Cloud Manager.'
    },
    en: {
      eyebrow: 'Private 5G Core · UERANSIM RAN · Prisma SASE 5G · Stigix Traffic Engine',
      hero_title: '5G Zero-Trust SASE & Traffic Validation Lab',
      hero_subtitle:
        'Unified launchpad to orchestrate end-to-end 5G User Equipment (UE/eSIM), drive the 5G Core (Open5GS) & Radio (UERANSIM) VMs, synchronize Palo Alto Networks Prisma SASE 5G identities, and inject L4/L7 application & threat traffic with Stigix.',
      sec_env_title: 'Playground Environments',
      sec_env_meta: '2 ACTIVE LAB PLATFORMS · CLOUDFLARE ZERO-TRUST TUNNELS',
      orch_desc:
        'Central control plane driving both the <strong>5G Core VM (Open5GS)</strong> and <strong>5G RAN VM (UERANSIM)</strong> paired with <strong>Palo Alto Networks Strata Cloud Manager (SCM)</strong>. Provision multi-vertical 5G fleets in 1 click and automate live IP ⇄ SASE Identity correlation.',
      orch_b1:
        '<strong>5G Core VM (Open5GS + MongoDB):</strong> Automated SIM subscriber provisioning (IMSI, K/OPc keys, 5QI QoS, S-NSSAI SST/SD slice) and live SMF/AMF session telemetry.',
      orch_b2:
        '<strong>5G RAN VM (UERANSIM Agent):</strong> Dynamic radio YAML templating, supervised <code>nr-ue</code> daemon lifecycle, and dedicated Linux <code>uesimtunX</code> tunnel interfaces.',
      orch_b3:
        '<strong>Prisma SASE 5G Correlation:</strong> Continuous 4-way ground-truth reconciliation (SCM ⇄ Mongo ⇄ SMF ⇄ RAN) and real-time IP binding (<code>/uesession/register</code>) for agentless Zero-Trust enforcement.',
      btn_launch_orch: 'Launch 5G Orchestrator',
      lab_desc:
        '<strong>Stigix</strong> L4/L7 application traffic generator, threat simulator, and deep network observability suite bound to the 5G user plane. Drives realistic traffic directly over <code>uesimtun*</code> radio tunnels into Prisma SASE 5G.',
      lab_b1:
        '<strong>SaaS & Vertical Traffic Generation:</strong> Enterprise HTTPS/SaaS flows, Custom TCP, industrial protocols (Modbus/MQTT/RTSP), VoIP RTP (MOS/Jitter scoring), and Stateful PCAP replay.',
      lab_b2:
        '<strong>Security & Zero-Trust Validation:</strong> On-demand URL filtering audits, DNS tunneling, EICAR malware payloads, Command & Control (C2) scenarios, and AI/DLP security validation.',
      lab_b3:
        '<strong>Web Wireshark & DEM Probes:</strong> Live packet capture on 5G interfaces, in-browser protocol dissection, and end-to-end latency/loss benchmarking.',
      btn_launch_lab: 'Launch Stigix 5G Lab',
      btn_details: 'Architecture & Roles',
      sec_arch_title: 'Architecture Diagrams & Call Flows',
      sec_arch_meta: 'CLICK ANY NODE OR TILE TO INSPECT TECHNICAL BLUEPRINTS',
      flow_banner_title: 'END-TO-END PROCESSING PIPELINE (RAN ➔ CORE ➔ PRISMA SASE 5G ➔ STIGIX TRAFFIC)',
      flow_1_desc: 'Emulates the 5G gNodeB base station and 5G UE modems. Spawns a dedicated Linux TUN interface per active SIM.',
      flow_2_desc: 'Authenticates SIMs (K/OPc), establishes IPv4 PDU sessions, enforces S-NSSAI slicing, and routes GTP-U user plane packets.',
      flow_3_desc: 'Binds dynamic session IPs to 5G hardware/SIM identities (IMSI/IMEI) and enforces group-based Zero-Trust rules.',
      flow_4_desc: 'Injects enterprise application traffic and threat signatures through UE tunnels to validate real-time inspection.',
      tile_1_title: '5G Core & RAN Topology',
      tile_1_sub: 'Dual-VM Open5GS, UERANSIM & N2/N3/N6 Tunnel Architecture',
      tile_2_title: '7-Step Zero-Trust Lifecycle',
      tile_2_sub: 'From SIM creation to dynamic IP session binding in SCM',
      tile_3_title: 'Ground-Truth Reconciler',
      tile_3_sub: 'Real-time state sync across SCM ⇄ MongoDB ⇄ SMF/AMF ⇄ RAN',
      tile_4_title: '5G Slicing & IoT Verticals',
      tile_4_sub: 'Industry 4.0, Smart City, Healthcare, Retail POS & EV Infra',
      sec_comp_title: 'Infrastructure Component Roles',
      sec_comp_meta: 'TECHNICAL BREAKDOWN OF EVERY LAB BUILDING BLOCK',
      comp_1_desc:
        'Central orchestration brain hosted on the Core VM (exposed at <code>5gorchestrator.stigix.io</code>). Unifies Open5GS subscriber creation, remote UERANSIM modem control, and Prisma SASE 5G identity/session binding into one Web UI and REST API.',
      comp_2_desc:
        '3GPP Release 17 5G Standalone Packet Core. <strong>MongoDB</strong> stores subscriber credentials (IMSI, K/OPc, 5QI QoS, AMBR). <strong>AMF</strong> handles N1/N2 radio attach, <strong>SMF</strong> allocates PDU session IPs (<code>10.45.0.x</code>), and <strong>UPF</strong> forwards user plane traffic (N3/N6).',
      comp_3_desc:
        '5G Radio Access simulator running the <code>nr-gnb</code> base station and the <strong>RAN Agent</strong> microservice. On request from the Orchestrator, it generates the UE YAML, spawns a supervised <code>nr-ue</code> daemon, and brings up a dedicated <code>uesimtunX</code> tunnel.',
      comp_4_desc:
        'Palo Alto Networks cloud security managed via <strong>Strata Cloud Manager</strong>. Enforces granular Zero-Trust security policies based on hardware and SIM identity (<strong>IMSI, IMEI, APN, Subscriber Group</strong>) with zero software agent required on IoT/OT endpoints.',
      comp_5_desc:
        'Hosted at <code>stigix5glab.stigix.io</code>, this <strong>Stigix</strong> instance generates continuous application traffic and threat scenarios (EICAR, C2, DNS Tunneling, URL Filtering, DLP) across the 5G network to populate SCM dashboards and prove real-time security enforcement.',
      comp_6_desc:
        'Securely publishes the lab control interfaces (<code>5gorchestrator.stigix.io</code> and <code>stigix5glab.stigix.io</code>) over outbound encrypted <code>cloudflared</code> tunnels with zero inbound firewall ports opened (MongoDB 27017 and Open5GS 9090 remain isolated on local loopback).',
      sec_walk_title: 'Guided Walkthroughs & Demo Scenarios',
      sec_walk_meta: 'RECOMMENDED DEMO FLOWS FOR CUSTOMER BRIEFINGS & TRADE SHOWS',
      walk_1_title: 'Scenario 1 · 1-Click 5G Fleet Onboarding',
      walk_1_desc:
        'Open <strong>5G Orchestrator</strong>, pick an industry preset (e.g. <em>Industry 4.0 Robot</em> or <em>EVSE Charger</em>), and click <strong>Register & Attach</strong>. Watch simultaneous provisioning in Open5GS MongoDB, <code>nr-ue</code> daemon launch on the RAN VM, and live IP session binding in Prisma SASE 5G.',
      walk_2_title: 'Scenario 2 · Zero-Trust Policy Shift (Permissive ➔ Restrictive)',
      walk_2_desc:
        'In <strong>5G Orchestrator</strong>, move an active SIM from a <em>Permissive-IoT</em> group to a <em>Quarantine / Restrictive</em> group. Without touching the 5G endpoint or dropping its radio session, Prisma SASE 5G immediately enforces the stricter security policy on its live IP flow.',
      walk_3_title: 'Scenario 3 · Traffic Generation & Threat Prevention Audit',
      walk_3_desc:
        'Open <strong>Stigix 5G Lab</strong> to fire enterprise SaaS flows, trigger threat prevention audits (EICAR, C2, DNS Tunneling), or inspect live GTP/IP packets in <strong>Web Wireshark</strong>, then correlate threat logs in Strata Cloud Manager.'
    }
  };

  let currentLang = 'fr';
  const langBtn = document.getElementById('btn-lang-toggle');
  const langLabel = document.getElementById('lang-mode-label');

  if (langBtn && langLabel) {
    langBtn.addEventListener('click', () => {
      currentLang = currentLang === 'fr' ? 'en' : 'fr';
      document.documentElement.lang = currentLang;
      langLabel.textContent = currentLang === 'fr' ? 'FR / EN' : 'EN / FR';
      const dict = i18n[currentLang];
      document.querySelectorAll('[data-i18n]').forEach((el) => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) {
          el.innerHTML = dict[key];
        }
      });
    });
  }
})();
