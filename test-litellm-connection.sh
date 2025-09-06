#!/bin/bash

echo "Testing LiteLLM connection from Open-WebUI container..."
echo "=================================================="

# Test 1: Check if LiteLLM is reachable
echo -e "\n1. Testing network connectivity to LiteLLM:"
docker exec open-webui sh -c 'ping -c 2 litellm' 2>/dev/null || echo "Ping not available, trying curl..."

# Test 2: Check models endpoint
echo -e "\n2. Fetching available models from LiteLLM:"
docker exec open-webui sh -c 'curl -s http://litellm:4000/v1/models \
  -H "Authorization: Bearer sk-e0b742bc6575adf26c7d356c49c78d8fd08119fcde1d6e188d753999b5f956fc" \
  | grep -o "\"id\":\"[^\"]*\"" | sed "s/\"id\":\"/  - /g" | sed "s/\"//g"'

# Test 3: Test a simple completion
echo -e "\n3. Testing a simple completion with gpt-4o:"
docker exec open-webui sh -c 'curl -s http://litellm:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-e0b742bc6575adf26c7d356c49c78d8fd08119fcde1d6e188d753999b5f956fc" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"gpt-4o\", \"messages\": [{\"role\": \"user\", \"content\": \"Say OK\"}], \"max_tokens\": 10}" \
  | grep -o "\"content\":\"[^\"]*\"" | head -1'

echo -e "\n=================================================="
echo "If you see models listed above, the connection is working!"
echo ""
echo "To see models in Open-WebUI:"
echo "1. Go to https://open-webui.ai-servicers.com"
echo "2. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)"
echo "3. Log out and log back in"
echo "4. Check the model dropdown in a new chat"