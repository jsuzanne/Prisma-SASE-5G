#!/bin/bash
set -e

ROLE="${ROLE:-core}"
PORT="${PORT:-8080}"
AGENT_PORT="${AGENT_PORT:-8081}"

echo "=================================================="
echo " Starting Prisma SASE 5G Orchestrator"
echo " Role: ${ROLE}"
echo "=================================================="

# Ensure directories exist
mkdir -p /app/config /app/data /app/static

if [ "${ROLE}" = "core" ]; then
    echo "[+] Starting Core Web UI & REST API on port ${PORT}..."
    exec uvicorn app:app --host 0.0.0.0 --port "${PORT}"
elif [ "${ROLE}" = "ue-agent" ]; then
    echo "[+] Starting UERANSIM Agent service on port ${AGENT_PORT}..."
    exec uvicorn app:app --host 0.0.0.0 --port "${AGENT_PORT}"
else
    echo "[+] Starting All-in-One Orchestrator on port ${PORT}..."
    exec uvicorn app:app --host 0.0.0.0 --port "${PORT}"
fi
