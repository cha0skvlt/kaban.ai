#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

log() { printf '==> %s\n' "$*"; }

if docker compose ps -q 2>/dev/null | grep -q .; then
  log "Stopping Docker stack..."
  docker compose down
else
  log "Docker stack is not running"
fi

log "Done. Ollama was left running (shared system service)."
