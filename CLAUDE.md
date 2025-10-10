# Open WebUI Deployment

## Overview
Open WebUI - A user-friendly interface for AI models with Keycloak SSO integration and MCP tool execution support.

**Last Updated**: 2025-10-10
**Status**: ✅ Running with MCP middleware integration and Keycloak SSO

## Configuration
- **Location**: `/home/administrator/projects/open-webui/`
- **Data**: `/home/administrator/data/open-webui/`
- **Secrets**: `$HOME/projects/secrets/open-webui.env` (symlink)
- **Access**: https://open-webui.ai-servicers.com
- **Local Port**: 8000
- **Docker Image**: ghcr.io/open-webui/open-webui:main

## Features
- ✅ **Keycloak SSO Integration**: Full OAuth2/OIDC authentication
- ✅ **Traefik Reverse Proxy**: HTTPS with Let's Encrypt
- ✅ **LiteLLM Integration**: Access to 19 LLM models through unified API
- ✅ **Multi-Provider Support**: OpenAI (GPT-5), Anthropic (Claude Opus 4.1), Google (Gemini 2.5)
- ✅ **Persistent Storage**: User data and conversations saved

## Keycloak SSO Configuration
Successfully integrated with Keycloak at https://keycloak.ai-servicers.com

### Client Settings
- **Client ID**: `open-webui`
- **Client Protocol**: openid-connect
- **Access Type**: confidential
- **Valid Redirect URIs**: `https://open-webui.ai-servicers.com/oauth/oidc/callback`

### Network Configuration (Updated 2025-10-10)
- **Primary Network**: keycloak-net (for proper DNS resolution)
- **Additional Networks**: litellm-net, traefik-net
- **Keycloak Connection**: Internal Docker DNS (`keycloak:8080`)
- **DNS Resolution**: Automatic via Docker (no hardcoded IPs)
- **Internal URL**: `http://keycloak:8080/realms/master/.well-known/openid-configuration`

## Deployment

### Quick Deploy
```bash
cd /home/administrator/projects/open-webui
./deploy.sh
```

### Manual Configuration
1. Update Keycloak client secret in `$HOME/projects/secrets/open-webui.env`
2. Run `./setup-keycloak.sh` for setup instructions
3. Deploy with `./deploy.sh`

## Scripts
- `deploy.sh` - Main deployment script with Traefik labels and multi-network setup
- `setup-keycloak.sh` - Keycloak configuration guide

### Deploy Script Details
The deploy.sh script is configured to:
1. Start container on **keycloak-net** first (critical for DNS resolution)
2. Use env file at `$HOME/projects/secrets/open-webui.env` (portable path)
3. Connect to litellm-net and traefik-net after initial deployment
4. No hardcoded host entries (relies on Docker DNS)

## Environment Variables
Key settings in `$HOME/projects/secrets/open-webui.env`:
```env
# WebUI Settings
WEBUI_NAME="AI Servicers Chat"
WEBUI_URL=https://open-webui.ai-servicers.com

# LiteLLM Integration
OPENAI_API_KEY=sk-litellm-cecca390f610603ff5180ba0ba2674afc8f7689716daf25343de027d10c32404
OPENAI_API_BASE_URL=http://mcp-middleware:8080/v1

# Authentication
ENABLE_SIGNUP=false  # Users must authenticate via Keycloak
ENABLE_OAUTH_SIGNUP=true  # Auto-create users on first SSO login

# Keycloak OAuth (Internal Docker Network)
OAUTH_PROVIDER_NAME=Keycloak
OAUTH_CLIENT_ID=open-webui
OAUTH_CLIENT_SECRET=pHivWX2Z2GEdHwYnNhLQlqpCMxBf52CA
OPENID_PROVIDER_URL=http://keycloak:8080/realms/master/.well-known/openid-configuration
OPENID_REDIRECT_URI=https://open-webui.ai-servicers.com/oauth/oidc/callback
OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true

# Default Models
DEFAULT_MODELS=gpt-5,gpt-5-chat-latest,gpt-5-mini,claude-opus-4.1,gemini-2.5-pro
```

## Troubleshooting

### OAuth Internal Server Error (FIXED 2025-10-10)
**Issue**: 500 error or 404 when clicking "Sign in with Keycloak"
**Root Cause**: Docker DNS resolution issues when container is on multiple networks
**Solution**:
1. Start container on `keycloak-net` as primary network (CRITICAL)
2. Use internal Docker hostname: `http://keycloak:8080`
3. Do NOT use hardcoded `--add-host` entries
4. Do NOT use external URLs or IP addresses
5. Connect to other networks AFTER initial deployment

**Verification**:
```bash
# Check DNS resolution
docker exec open-webui getent hosts keycloak

# Test OIDC endpoint
docker exec open-webui curl -s -o /dev/null -w "%{http_code}" \
  http://keycloak:8080/realms/master/.well-known/openid-configuration
```

### Connection Timeouts
**Issue**: `httpx.ConnectTimeout` in logs
**Solution**:
- Verify container is on keycloak-net
- Ensure OPENID_PROVIDER_URL uses `http://keycloak:8080` (not external URL)
- Check deploy.sh has `--network keycloak-net` as first network

### Clean Logs
To verify no errors:
```bash
docker logs open-webui --tail 100 2>&1 | grep -E "ERROR|error|Failed|Exception|timeout"
```

### DNS Wrong IP Resolution
**Issue**: `keycloak` hostname resolves to wrong IP (e.g., traefik network IP instead of keycloak-net IP)
**Cause**: When Docker container is on multiple networks, it uses the first network for DNS
**Solution**: Always start with keycloak-net as primary network in docker run command

## MCP Middleware Integration (2025-09-07) ✅ WORKING

### Current Configuration
- **API Endpoint**: http://mcp-middleware:8080/v1 (via middleware)
- **Middleware**: FastAPI-based execution layer for MCP tools
- **Network**: Connected to litellm-net for service communication
- **Status**: ✅ Fully operational with 57 MCP tools across 8 servers
- **MCP Servers**: filesystem, postgres, puppeteer, memory, minio, n8n, timescaledb, ib

### Internal Access Configuration (2025-09-07)
- **Container**: open-webui-internal
- **Port**: 8001
- **URLs**: 
  - http://open-webui.linuxserver.lan (via Traefik)
  - http://linuxserver.lan:8001 (direct)
- **Authentication**: None (internal network only)
- **Data Directory**: `/home/administrator/data/open-webui-internal/`

### Dual Instance Setup
1. **External (SSO)**: https://open-webui.ai-servicers.com
   - Port 8000, Keycloak authentication required
   - Production data at `/data/open-webui/`
   
2. **Internal (No Auth)**: http://open-webui.linuxserver.lan
   - Port 8001, no authentication
   - Separate data at `/data/open-webui-internal/`
   - Same models and MCP tools

### Available MCP Tools (Updated 2025-10-10)
- **57 tools** across **8 MCP servers**
- Auto-injected into all requests via middleware
- Filesystem (9), PostgreSQL (1), Puppeteer (7), Memory (9), MinIO (9), N8N (6), TimescaleDB (6), IB/Interactive Brokers (10)
- All tools accessible via natural language ("list tools" to see full catalog)

## LiteLLM Integration

### Available Models (17 working)
**OpenAI GPT Models (7)**:
- gpt-5 (reasoning model, brief responses)
- gpt-5-chat-latest (shows detailed work)
- gpt-5-mini, gpt-5-nano
- gpt-4.1, gpt-4o, gpt-4o-mini

**Anthropic Claude Models (4)**:
- claude-opus-4.1 (latest, most capable)
- claude-opus-4
- claude-thinking (extended reasoning)
- claude-sonnet-4 (fast, balanced)

**Google Gemini Models (8)**:
- gemini-2.5-pro, gemini-2.5-flash
- gemini-2.5-flash-lite, gemini-2.5-flash-image-preview
- gemini-2.5-flash-preview-tts, gemini-2.5-pro-preview-tts
- gemini-1.5-pro, gemini-1.5-flash (legacy)

### Model Access
- **API Gateway**: http://litellm:4000/v1 (internal)
- **Master Key**: sk-e0b742bc6575adf26c7d356c49c78d8fd08119fcde1d6e188d753999b5f956fc
- **Default Models**: gpt-5, gpt-5-chat-latest, gpt-5-mini, claude-opus-4.1, gemini-2.5-pro

## Recent Changes

### 2025-10-10 - Keycloak DNS Fix
- ✅ **Fixed OAuth authentication** - resolved 500/404 errors on login
- ✅ **Primary network changed** from traefik-net to keycloak-net (critical for DNS)
- ✅ **Removed hardcoded IPs** - now uses Docker DNS resolution
- ✅ **Updated env file path** to `$HOME/projects/secrets/open-webui.env` (portable symlink)
- ✅ **Multi-network setup** - connects to litellm-net and traefik-net after deployment
- ✅ **Verified working** - Keycloak login flow operational
- ✅ **Updated to main image** from v0.6.32
- ✅ **All changes persisted** in deploy.sh for future deployments

**Root Cause**: Docker DNS returns different IPs when container is on multiple networks. Starting on keycloak-net ensures `keycloak` hostname resolves to correct IP (172.19.0.6).

### 2025-01-11
- ✅ Integrated LiteLLM with 19 models
- ✅ Configured GPT-5, Claude Opus 4.1, Gemini 2.5 models
- ✅ Fixed model routing and identification
- ✅ Added model verification documentation

### 2025-08-27
- ✅ Migrated from `/home/websurfinmurf/projects/` to `/home/administrator/projects/`
- ✅ Fixed Keycloak OAuth integration with internal networking
- ✅ Achieved zero errors in logs

## Maintenance

### Check Status
```bash
docker ps | grep open-webui
docker logs open-webui --tail 50
```

### Restart
```bash
docker restart open-webui
```

### Update
```bash
docker pull ghcr.io/open-webui/open-webui:main
docker stop open-webui && docker rm open-webui
./deploy.sh
```

## Security Notes
- SSO authentication required (no local accounts)
- Keycloak manages all user authentication
- Internal Docker networking for service communication
- HTTPS only via Traefik

## Related Documentation
- LiteLLM Config: `/home/administrator/projects/litellm/CLAUDE.md`
- Model List: `/home/administrator/projects/litellm/modellist.md`
- Model Verification: `/home/administrator/projects/litellm/model-verification.md`
- Integration Guide: `/home/administrator/projects/open-webui/LITELLM_INTEGRATION.md`

---
*Last Updated: 2025-10-10 - Keycloak DNS Fix Applied*