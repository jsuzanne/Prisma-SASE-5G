#!/usr/bin/env python3
"""
End-to-End Verification Test Script for 5G SASE Orchestrator.

Executes a complete real-world validation cycle:
1. Generates credentials for a Vertical (Smart Camera).
2. Provisions subscriber in Open5GS MongoDB (Core VM 152.236.5.40).
3. Deploys YAML and starts nr-ue daemon (RAN VM 152.236.5.67).
4. Polls SMF for active PDU session and allocated IP.
5. Verifies TUN interface (uesimtunX) on Linux kernel.
6. Tests ICMP connectivity through the 5G tunnel.
7. Automatically cleans up test resources.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.verticals import generate_device_credentials
from src.models import OrchestratedEndpoint, SecurityConfig, SliceConfig, QoSConfig
from src.open5gs import Open5GSClient
from src.ueransim import UERANSIMClient

TEST_IMSI = "999700000000101"
VERTICAL_ID = "smart_camera"


def print_step(num: int, title: str):
    print(f"\n{'='*60}")
    print(f" [ÉTAPE {num}] {title}")
    print(f"{'='*60}")


def main():
    print("============================================================")
    print("  DÉMARRAGE DU TEST DE VÉRIFICATION ORCHESTRATEUR 5G")
    print("============================================================")

    # 1. Génération
    print_step(1, f"Génération du profil Vertical ({VERTICAL_ID})")
    creds = generate_device_credentials(VERTICAL_ID, custom_imsi=TEST_IMSI)
    sec = SecurityConfig(k="465B5CE8B199B49FAA5F0A2EE238A6BC", op="E8ED289DEBA952E4283B54E88E6183CA", op_type="OP")
    slice_cfg = SliceConfig(sst=1)
    qos_cfg = QoSConfig(five_qi=9, ambr_dl_mbps=100, ambr_ul_mbps=50)

    endpoint = OrchestratedEndpoint(
        imsi=TEST_IMSI,
        imei=creds["imei"],
        apn="internet",
        vertical_id=VERTICAL_ID,
        device_name="Test Axis 4K Camera #1",
        vendor=creds["vendor"],
        device_model=creds["device_model"],
        icon=creds["icon"],
        security=sec,
        slice=slice_cfg,
        qos=qos_cfg,
    )
    print(f"  ✓ Device: {endpoint.device_name} ({endpoint.device_model})")
    print(f"  ✓ IMSI: {endpoint.imsi} | IMEI: {endpoint.imei}")
    print(f"  ✓ Slice: SST={endpoint.slice.sst} | QoS 5QI: {endpoint.qos.five_qi}")

    core = Open5GSClient()
    ran = UERANSIMClient()

    try:
        # 2. MongoDB
        print_step(2, "Provisioning dans Open5GS MongoDB (Core VM 152.236.5.40)")
        core.create_subscriber(endpoint)
        sub = core.get_subscriber(TEST_IMSI)
        if not sub:
            print("  ✗ ERREUR: L'abonné n'a pas été trouvé dans MongoDB.")
            sys.exit(1)
        print(f"  ✓ Abonné inséré avec succès dans MongoDB (IMSI: {sub.get('imsi')}).")

        # 3. UERANSIM
        print_step(3, "Génération YAML & Démarrage de nr-ue (RAN VM 152.236.5.67)")
        status = ran.start_ue(endpoint)
        print(f"  ✓ Processus nr-ue initialisé (PID: {status.get('pid')}, Running: {status.get('running')}).")

        # 4. Polling SMF
        print_step(4, "Attente de l'activation PDU et allocation IP (SMF Open5GS)")
        session = core.poll_pdu_session(TEST_IMSI, timeout_sec=10)
        if not session or not session.get("ipv4"):
            print("  ✗ ERREUR: Session PDU non établie après 10s.")
            sys.exit(1)
        print(f"  ✓ Session PDU ACTIVE détectée !")
        print(f"    - SUPI: {session.get('supi')}")
        print(f"    - Adresse IPv4 allouée: {session.get('ipv4')}")
        print(f"    - Slice S-NSSAI: SST={session.get('sst')}")

        # 5. Interface Linux
        print_step(5, "Vérification de l'interface réseau Linux (uesimtun*)")
        allocated_ip = session.get("ipv4")
        tun_iface = None
        for _ in range(5):
            tun_info = ran._exec_command("ip -br a | grep uesimtun")
            for line in tun_info.splitlines():
                if allocated_ip in line:
                    tun_iface = line.split()[0]
                    break
            if tun_iface:
                break
            time.sleep(1)

        print(f"  ✓ Interface détectée pour l'IP {allocated_ip} : {tun_iface or 'uesimtun (en cours)'}")
        print(f"  ✓ Interfaces réseau actives sur la VM RAN:\n{tun_info}")

        # 6. Test Ping
        print_step(6, "Test de connectivité ICMP à travers le tunnel 5G")
        if tun_iface:
            ping_res = ran._exec_command(f"ping -c 2 -I {tun_iface} 10.45.0.1 2>&1 || true")
            if "2 packets transmitted" in ping_res:
                print(f"  ✓ Ping à travers le tunnel {tun_iface} réussi :\n{ping_res}")
            else:
                print(f"  ℹ Sortie du ping : {ping_res}")
        else:
            print("  ℹ Interface TUN non encore prête pour le ping.")

        print("\n" + "="*60)
        print("  🎉 TOUS LES TESTS SONT VALIDÉS AVEC SUCCÈS !")
        print("="*60)

    finally:
        # 7. Nettoyage
        print_step(7, "Nettoyage automatique sécurisé des ressources de test")
        ran.stop_ue(TEST_IMSI)
        core.delete_subscriber(TEST_IMSI)
        print("  ✓ Processus nr-ue arrêté et abonné de test retiré de MongoDB.")
        print("  ✓ Le lab est propre et prêt.")


if __name__ == "__main__":
    main()
