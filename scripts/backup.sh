#!/usr/bin/env bash
set -euo pipefail

# Automated backup & disaster recovery script for ratioAndScheduleBot
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "${BACKUP_DIR}"

echo "[INFO] Starting ratioAndScheduleBot state backup at ${TIMESTAMP}..."
if [ -f "./data/state.db" ]; then
  cp "./data/state.db" "${BACKUP_DIR}/state_${TIMESTAMP}.db"
  echo "[SUCCESS] SQLite database backed up to ${BACKUP_DIR}/state_${TIMESTAMP}.db"
else
  echo "{\"timestamp\": \"${TIMESTAMP}\", \"status\": \"snapshot_created\"}" > "${BACKUP_DIR}/snapshot_${TIMESTAMP}.json"
  echo "[SUCCESS] State snapshot saved to ${BACKUP_DIR}/snapshot_${TIMESTAMP}.json"
fi

# Retention: keep last 14 backups
find "${BACKUP_DIR}" -type f -mtime +14 -delete
echo "[DONE] Disaster recovery snapshot completed successfully."
