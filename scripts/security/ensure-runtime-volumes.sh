#!/usr/bin/env bash
set -euo pipefail

N8N_VOLUME_NAME="${N8N_VOLUME_NAME:-agent_workspace_n8n_data}"

if docker volume inspect "${N8N_VOLUME_NAME}" >/dev/null 2>&1; then
  echo "[OK] docker volume exists: ${N8N_VOLUME_NAME}"
else
  echo "[info] creating docker volume: ${N8N_VOLUME_NAME}"
  docker volume create "${N8N_VOLUME_NAME}" >/dev/null
  echo "[OK] docker volume created: ${N8N_VOLUME_NAME}"
fi
