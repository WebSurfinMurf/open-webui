#!/usr/bin/env bash
set -euo pipefail

echo "Deploying Open WebUI with internal network access..."

# Stop and remove existing container if exists
docker stop open-webui-internal 2>/dev/null || true
docker rm open-webui-internal 2>/dev/null || true

# Create data directory
mkdir -p /home/administrator/data/open-webui-internal

# Create environment file for internal access (no auth)
cat > /home/administrator/secrets/open-webui-internal.env << 'EOF'
# WebUI Settings
WEBUI_NAME="AI Servicers Chat (Internal)"
WEBUI_URL=http://open-webui.linuxserver.lan:8001
WEBUI_SECRET_KEY=your_secret_key_here
DEFAULT_USER_ROLE=admin

# Disable external authentication
ENABLE_SIGNUP=true
ENABLE_LOGIN_FORM=true
ENABLE_OAUTH_SIGNUP=false
DEFAULT_MODELS=gpt-5-mini,gpt-4o-mini,claude-opus-4.1,gemini-2.5-flash

# Admin account (auto-created on first run)
WEBUI_AUTH=false

# OpenAI API settings (point directly to LiteLLM - no middleware)
OPENAI_API_BASE_URL=http://litellm:4000/v1
OPENAI_API_KEY=sk-e0b742bc6575adf26c7d356c49c78d8fd08119fcde1d6e188d753999b5f956fc

# Disable telemetry
SCARF_NO_ANALYTICS=true
DO_NOT_TRACK=true
ANONYMIZED_TELEMETRY=false

# Features
ENABLE_RAG_WEB_SEARCH=false
ENABLE_IMAGE_GENERATION=false
ENABLE_COMMUNITY_SHARING=false
EOF

# Deploy Open WebUI for internal access
docker run -d \
  --name open-webui-internal \
  --restart unless-stopped \
  --network traefik-net \
  --env-file /home/administrator/secrets/open-webui-internal.env \
  -v /home/administrator/data/open-webui-internal:/app/backend/data \
  -p 8001:8080 \
  --label "traefik.enable=true" \
  --label "traefik.docker.network=traefik-net" \
  --label "traefik.http.routers.open-webui-internal.rule=Host(\`open-webui.linuxserver.lan\`)" \
  --label "traefik.http.routers.open-webui-internal.entrypoints=web" \
  --label "traefik.http.services.open-webui-internal.loadbalancer.server.port=8080" \
  ghcr.io/open-webui/open-webui:main

# Connect to litellm-net for middleware access
docker network connect litellm-net open-webui-internal 2>/dev/null || echo "Note: Could not connect to litellm-net"

echo "Waiting for Open WebUI Internal to start..."
sleep 10

# Check status
if docker ps | grep -q open-webui-internal; then
    echo "✅ Open WebUI Internal is running!"
    echo ""
    echo "Access methods:"
    echo "  Internal (no auth): http://open-webui.linuxserver.lan"
    echo "  Direct port (no auth): http://linuxserver.lan:8001"
    echo "  Direct IP (no auth): http://192.168.1.100:8001"
    echo ""
    echo "This instance has NO authentication - only use on trusted internal network!"
    echo ""
    echo "Default admin account (if auth is enabled):"
    echo "  Username: administrator"
    echo "  Password: admin"
else
    echo "❌ Failed to start. Check logs: docker logs open-webui-internal"
fi