#!/usr/bin/env bash
set -euo pipefail

# Load environment
#source ~/projects/secrets/open-webui.env

# Stop and remove existing container if exists
docker stop open-webui 2>/dev/null || true
docker rm open-webui 2>/dev/null || true

# Create data directory
mkdir -p /opt/open-webui/data

# Deploy Open WebUI
docker run -d \
  --name open-webui \
  --restart unless-stopped \
  --network traefik-proxy \
  --env-file ~/projects/secrets/open-webui.env \
  -v /opt/open-webui/data:/app/backend/data \
  -p 8000:8080 \
  --label "traefik.enable=true" \
  --label "traefik.docker.network=traefik-proxy" \
  --label "traefik.http.routers.open-webui.rule=Host(\`open-webui.ai-servicers.com\`)" \
  --label "traefik.http.routers.open-webui.entrypoints=websecure" \
  --label "traefik.http.routers.open-webui.tls=true" \
  --label "traefik.http.routers.open-webui.tls.certresolver=letsencrypt" \
  --label "traefik.http.services.open-webui.loadbalancer.server.port=8080" \
  ghcr.io/open-webui/open-webui:main

echo "Waiting for Open WebUI to start..."
sleep 10

# Check status
if docker ps | grep -q open-webui; then
    echo "✅ Open WebUI is running!"
    echo "Access at: https://open-webui.ai-servicers.com"
else
    echo "❌ Failed to start. Check logs: docker logs open-webui"
fi
