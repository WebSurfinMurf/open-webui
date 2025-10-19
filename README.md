# Open WebUI

AI chat interface with Keycloak SSO integration.

## Quick Start

```bash
./deploy.sh
```

## Access
- **URL**: https://open-webui.ai-servicers.com
- **Auth**: Sign in with Keycloak SSO

## Files
- `deploy.sh` - Deployment script
- `setup-keycloak.sh` - SSO setup guide
- `CLAUDE.md` - Full documentation
- `.gitignore` - Git ignore rules

## Configuration
- Environment: `$HOME/projects/secrets/open-webui.env`
- Data: `/home/administrator/data/open-webui/`

## Management

```bash
# Check status
docker ps | grep open-webui

# View logs
docker logs open-webui --tail 50

# Restart
docker restart open-webui

# Update
docker pull ghcr.io/open-webui/open-webui:main
./deploy.sh
```

---
*Project created: Sat Aug 16 12:37:19 PM EDT 2025*
*See CLAUDE.md for detailed documentation*