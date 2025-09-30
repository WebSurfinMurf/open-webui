#!/usr/bin/env bash
set -euo pipefail

# Load environment
#source /home/administrator/secrets/open-webui.env

# Stop and remove existing container if exists
docker stop open-webui 2>/dev/null || true
docker rm open-webui 2>/dev/null || true

# Create data directory
mkdir -p /home/administrator/data/open-webui

# Deploy Open WebUI
docker run -d \
  --name open-webui \
  --restart unless-stopped \
  --network traefik-net \
  --add-host keycloak:172.22.0.3 \
  --env-file /home/administrator/secrets/open-webui.env \
  -v /home/administrator/data/open-webui:/app/backend/data \
  -p 8000:8080 \
  --label "traefik.enable=true" \
  --label "traefik.docker.network=traefik-net" \
  --label "traefik.http.routers.open-webui.rule=Host(\`open-webui.ai-servicers.com\`)" \
  --label "traefik.http.routers.open-webui.entrypoints=websecure" \
  --label "traefik.http.routers.open-webui.tls=true" \
  --label "traefik.http.routers.open-webui.tls.certresolver=letsencrypt" \
  --label "traefik.http.services.open-webui.loadbalancer.server.port=8080" \
  ghcr.io/open-webui/open-webui:v0.6.32

# Connect to litellm-net for middleware access
docker network connect litellm-net open-webui 2>/dev/null || echo "Note: Could not connect to litellm-net"

echo "Waiting for Open WebUI to start..."
sleep 10

# Check status
if docker ps | grep -q open-webui; then
    echo "✅ Open WebUI is running!"
    echo "Access at: https://open-webui.ai-servicers.com"
else
    echo "❌ Failed to start. Check logs: docker logs open-webui"
fi
