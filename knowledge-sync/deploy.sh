#!/bin/bash
# Deploy knowledge-sync webhook service
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load API key from secrets
if [ -f "$HOME/projects/secrets/open-webui-knowledge.env" ]; then
    set -a
    source "$HOME/projects/secrets/open-webui-knowledge.env"
    set +a
fi

if [ -z "${OPEN_WEBUI_API_KEY:-}" ]; then
    echo "Error: OPEN_WEBUI_API_KEY not set"
    echo "Add to ~/projects/secrets/open-webui-knowledge.env:"
    echo "  OPEN_WEBUI_API_KEY=your-key-here"
    exit 1
fi

export OPEN_WEBUI_API_KEY

echo "Building and deploying knowledge-sync..."
docker compose down --remove-orphans 2>/dev/null || true
docker compose build --no-cache
docker compose up -d

echo ""
echo "Waiting for service to start..."
sleep 3

if docker ps | grep -q knowledge-sync; then
    echo "✅ knowledge-sync is running"
    echo ""
    echo "Endpoints:"
    echo "  - Health: https://knowledge-sync.ai-servicers.com/health"
    echo "  - Sync:   https://knowledge-sync.ai-servicers.com/sync"
    echo ""
    echo "Or locally: http://localhost:8766/sync"
else
    echo "❌ Failed to start. Check logs:"
    docker logs knowledge-sync
fi
