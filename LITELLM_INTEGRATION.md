# Open-WebUI + LiteLLM Integration Guide

## Overview
This document describes how Open-WebUI is connected to LiteLLM to provide access to multiple LLM providers through a single interface.

## Current Configuration

### LiteLLM Gateway
- **URL**: https://litellm.ai-servicers.com
- **API Endpoint**: https://litellm.ai-servicers.com/v1
- **Master Key**: sk-e0b742bc6575adf26c7d356c49c78d8fd08119fcde1d6e188d753999b5f956fc

### Available Models (10 total)

#### Premium Models
- **gpt-4o** - OpenAI GPT-4 Omni (Latest, multimodal)
- **gpt-4-turbo** - OpenAI GPT-4 Turbo
- **claude-3-opus** - Anthropic Claude 3 Opus (Most capable)
- **gemini-1.5-pro** - Google Gemini 1.5 Pro

#### Standard Models
- **gpt-4o-mini** - Smaller, faster GPT-4o variant
- **claude-3-5-sonnet** - Claude 3.5 Sonnet (Fast & balanced)
- **gemini-pro** - Google Gemini Pro

#### Fast Models
- **gpt-3.5-turbo** - OpenAI GPT-3.5 Turbo
- **claude-3-haiku** - Claude 3 Haiku (Fastest)
- **gemini-1.5-flash** - Google Gemini 1.5 Flash

## Configuration Methods

### Method 1: Environment Variables (Current - Persistent)
Configuration is set in `$HOME/projects/secrets/open-webui.env`:

```env
# LiteLLM Gateway Configuration (OpenAI Compatible)
OPENAI_API_KEY=sk-e0b742bc6575adf26c7d356c49c78d8fd08119fcde1d6e188d753999b5f956fc
OPENAI_API_BASE_URL=https://litellm.ai-servicers.com/v1

# Default Models
DEFAULT_MODELS=gpt-4o,claude-3-opus,gemini-1.5-pro
```

### Method 2: UI Configuration (Alternative)
1. Access https://open-webui.ai-servicers.com
2. Go to Settings → Connections
3. Add OpenAI connection with:
   - Base URL: `https://litellm.ai-servicers.com/v1`
   - API Key: `sk-e0b742bc6575adf26c7d356c49c78d8fd08119fcde1d6e188d753999b5f956fc`

## Using the Models

### In Open-WebUI Chat
1. Go to https://open-webui.ai-servicers.com
2. Log in with Keycloak SSO
3. Select model from dropdown (gpt-4o, claude-3-opus, etc.)
4. Start chatting!

### Model Selection Tips
- **For complex reasoning**: Use `claude-3-opus` or `gpt-4o`
- **For balanced performance**: Use `claude-3-5-sonnet` or `gemini-1.5-pro`
- **For fast responses**: Use `claude-3-haiku` or `gpt-3.5-turbo`
- **For image analysis**: Use `gpt-4o` (multimodal) or `gemini-1.5-pro`

## Architecture Flow
```
User → Open-WebUI → LiteLLM Gateway → Provider APIs
         ↓              ↓                    ↓
    (Web Interface) (Unified API)    (OpenAI/Anthropic/Google)
```

## Troubleshooting

### Models Not Appearing
1. Check environment variables are set correctly
2. Restart Open-WebUI: `docker restart open-webui`
3. Verify LiteLLM is running: `docker ps | grep litellm`

### Connection Errors
1. Test LiteLLM directly:
```bash
curl https://litellm.ai-servicers.com/v1/models \
  -H "Authorization: Bearer sk-e0b742bc6575adf26c7d356c49c78d8fd08119fcde1d6e188d753999b5f956fc"
```

2. Check Open-WebUI logs:
```bash
docker logs open-webui --tail 50
```

### API Key Issues
- Ensure the master key is correct in the environment file
- Check LiteLLM logs: `docker logs litellm --tail 50`

## Benefits of This Integration

1. **Unified Interface**: Single UI for all LLM providers
2. **Cost Tracking**: LiteLLM tracks usage across all models
3. **Fallback Support**: Automatic failover between models
4. **Load Balancing**: "Least-busy" routing for optimal performance
5. **Model Flexibility**: Easy to add/remove models in LiteLLM config

## Maintenance

### Update Models
1. Edit `/home/administrator/projects/litellm/config.yaml`
2. Restart LiteLLM: `docker restart litellm`
3. Models automatically available in Open-WebUI

### Update API Key
1. Edit `$HOME/projects/secrets/litellm.env`
2. Update `$HOME/projects/secrets/open-webui.env`
3. Restart both services:
```bash
docker restart litellm
docker restart open-webui
```

## Related Documentation
- LiteLLM: `/home/administrator/projects/litellm/CLAUDE.md`
- Open-WebUI: `/home/administrator/projects/open-webui/CLAUDE.md`
- Network: `/home/administrator/projects/AINotes/network.md`

---
*Created: 2025-01-11*
*Integration Status: ✅ Active*