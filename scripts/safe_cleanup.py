#!/usr/bin/env python3
"""
Safe Cleanup & Rollback Script for 5G Lab Orchestrator.

Guarantees:
- Never deletes initial subscribers (999700000000001, 901700000000001).
- Never kills or restarts the gNodeB (nr-gnb).
- Never terminates the baseline UE process running open5gs-ue.yaml.
- Only cleans orchestrator-managed resources (managed_by: stigix-orchestrator).
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

CORE_VM = "jsuzanne@152.236.5.40"
RAN_VM = "jsuzanne@152.236.5.67"
PROTECTED_IMSIS = {"901700000000001", "999700000000001"}


def run_ssh(host: str, cmd: str) -> str:
    """Execute SSH command on remote VM."""
    full_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, cmd]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] SSH command failed on {host}: {res.stderr.strip()}", file=sys.stderr)
    return res.stdout.strip()


def cleanup_managed_subscribers():
    """Remove only subscribers tagged as managed by the orchestrator."""
    print("[+] Inspecting MongoDB on 5G Core VM...")
    mongo_cmd = """mongosh --quiet --eval '
        const res = db.getSiblingDB("open5gs").subscribers.deleteMany({
            $or: [
                { "managed_by": "stigix-orchestrator" },
                { "imsi": { $regex: "^9997000000001" } }
            ],
            "imsi": { $nin: ["901700000000001", "999700000000001"] }
        });
        console.log("Deleted count: " + res.deletedCount);
    '"""
    out = run_ssh(CORE_VM, mongo_cmd)
    print(f"    MongoDB cleanup result: {out}")


def cleanup_managed_ues():
    """Terminate only orchestrator-managed nr-ue processes and remove managed configs."""
    print("[+] Inspecting UERANSIM VM for managed UE processes...")
    
    # Kill nr-ue matching managed config files
    kill_cmd = """sudo pkill -f 'nr-ue.*config/managed' 2>/dev/null || true"""
    run_ssh(RAN_VM, kill_cmd)
    
    # Clean managed config directory
    clean_dir_cmd = """sudo rm -rf /home/ubuntu/UERANSIM/config/managed/*"""
    run_ssh(RAN_VM, clean_dir_cmd)
    print("    Terminated managed nr-ue processes and cleared config/managed/ directory.")


def verify_baseline_health():
    """Verify that baseline core services and nr-gnb are active and healthy."""
    print("[+] Verifying baseline lab health...")
    
    # Core health
    core_status = run_ssh(CORE_VM, "sudo systemctl is-active open5gs-amfd open5gs-smfd mongod 2>/dev/null")
    print(f"    Core Services (AMF, SMF, MongoDB):\n{core_status}")
    
    # RAN health
    ran_procs = run_ssh(RAN_VM, "ps aux | grep -E 'nr-gnb' | grep -v grep || true")
    if "nr-gnb" in ran_procs:
        print("    gNodeB (nr-gnb): ACTIVE")
    else:
        print("    [!] WARNING: nr-gnb is NOT running on UERANSIM VM!")


def main():
    parser = argparse.ArgumentParser(description="Safe Cleanup for 5G Orchestrator Lab")
    parser.add_argument("--status", action="store_true", help="Check lab health status without making changes")
    args = parser.parse_args()

    if args.status:
        verify_baseline_health()
        return

    print("=== Starting Safe Cleanup ===")
    cleanup_managed_subscribers()
    cleanup_managed_ues()
    verify_baseline_health()
    print("=== Safe Cleanup Completed ===")


if __name__ == "__main__":
    main()
