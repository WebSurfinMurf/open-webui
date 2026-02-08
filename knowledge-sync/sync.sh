#!/bin/bash
# Quick sync script - run from host
# Usage: ./sync.sh [--force] [--dry-run] [--watch]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KNOWLEDGE_DIR="/home/administrator/projects/open-webui/docs/knowledge"

# Load API key from secrets
if [ -f "$HOME/projects/secrets/open-webui-knowledge.env" ]; then
    source "$HOME/projects/secrets/open-webui-knowledge.env"
fi

if [ -z "${OPEN_WEBUI_API_KEY:-}" ]; then
    echo "Error: OPEN_WEBUI_API_KEY not set"
    echo "Create an API key in Open WebUI: Settings → Account → API Keys"
    echo "Then add to ~/projects/secrets/open-webui-knowledge.env:"
    echo "  OPEN_WEBUI_API_KEY=your-key-here"
    exit 1
fi

export OPEN_WEBUI_API_KEY
export OPEN_WEBUI_URL="${OPEN_WEBUI_URL:-http://localhost:8000}"
export KNOWLEDGE_DIR
export CACHE_FILE="$SCRIPT_DIR/.sync_cache.json"

# Path translation: /projects/ -> /home/administrator/projects/
# This allows the same definition files to work in container and on host
export PATH_PREFIX_MAP="/projects/:/home/administrator/projects/"

# Run the sync script directly (no Docker needed)
python3 "$SCRIPT_DIR/sync_knowledge.py" "$@"
