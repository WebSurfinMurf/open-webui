# Open WebUI Deployment

## Overview
Open WebUI - A user-friendly interface for AI models with Keycloak SSO integration.

## Configuration
- **Location**: `/home/administrator/projects/open-webui/`
- **Data**: `/home/administrator/data/open-webui/`
- **Secrets**: `/home/administrator/secrets/open-webui.env`
- **Access**: https://open-webui.ai-servicers.com
- **Local Port**: 8000

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

### Network Configuration
- Uses internal Docker networking for Keycloak communication
- Host entry added: `keycloak:172.22.0.3`
- Internal URL: `http://keycloak:8080/realms/master/`

## Deployment

### Quick Deploy
```bash
cd /home/administrator/projects/open-webui
./deploy.sh
```

### Manual Configuration
1. Update Keycloak client secret in `/home/administrator/secrets/open-webui.env`
2. Run `./setup-keycloak.sh` for setup instructions
3. Deploy with `./deploy.sh`

## Scripts
- `deploy.sh` - Main deployment script with Traefik labels and Keycloak host entry
- `setup-keycloak.sh` - Keycloak configuration guide

## Environment Variables
Key settings in `/home/administrator/secrets/open-webui.env`:
```env
# WebUI Settings
WEBUI_NAME="AI Servicers Chat"
WEBUI_URL=https://open-webui.ai-servicers.com

# Authentication
ENABLE_SIGNUP=false  # Users must authenticate via Keycloak
ENABLE_OAUTH_SIGNUP=true  # Auto-create users on first SSO login

# Keycloak OAuth
OAUTH_CLIENT_ID=open-webui
OAUTH_CLIENT_SECRET=pHivWX2Z2GEdHwYnNhLQlqpCMxBf52CA
OPENID_PROVIDER_URL=http://keycloak:8080/realms/master/.well-known/openid-configuration
```

## Troubleshooting

### OAuth Internal Server Error
**Issue**: 500 error when clicking "Sign in with Keycloak"
**Solution**: 
- Use internal Docker hostname (`keycloak:8080`) not external URL
- Add host entry in deploy.sh: `--add-host keycloak:172.22.0.3`

### Connection Timeouts
**Issue**: `httpx.ConnectTimeout` in logs
**Solution**: Container must reach Keycloak internally, not through external URL

### Clean Logs
To verify no errors:
```bash
docker logs open-webui --tail 100 2>&1 | grep -E "ERROR|error|Failed|Exception|timeout"
```

## LiteLLM Integration

### Available Models (19 total)
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

### 2025-01-11
- ✅ Integrated LiteLLM with 19 models
- ✅ Configured GPT-5, Claude Opus 4.1, Gemini 2.5 models
- ✅ Fixed model routing and identification
- ✅ Added model verification documentation

### 2025-08-27
- ✅ Migrated from `/home/websurfinmurf/projects/` to `/home/administrator/projects/`
- ✅ Fixed Keycloak OAuth integration with internal networking
- ✅ Added host entry for Keycloak container
- ✅ Achieved zero errors in logs
- ✅ Successfully tested SSO login

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
*Last Updated: 2025-01-11*