#!/usr/bin/env python3
"""
Simple webhook server to trigger knowledge sync.
Runs on port 8765 and provides a /sync endpoint.
"""

import subprocess
import os
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from Dashy

SYNC_SCRIPT = "/app/sync_knowledge.py"

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/sync', methods=['POST', 'GET'])
def sync():
    """Trigger knowledge sync."""
    try:
        # Run the sync script
        result = subprocess.run(
            ['python3', SYNC_SCRIPT],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env={
                **os.environ,
                'OPEN_WEBUI_API_KEY': os.getenv('OPEN_WEBUI_API_KEY', ''),
                'OPEN_WEBUI_URL': os.getenv('OPEN_WEBUI_URL', 'http://open-webui:8080'),
                'KNOWLEDGE_DIR': os.getenv('KNOWLEDGE_DIR', '/knowledge'),
                'CACHE_FILE': os.getenv('CACHE_FILE', '/app/cache/.sync_cache.json'),
                'QDRANT_URI': os.getenv('QDRANT_URI', 'http://qdrant:6333'),
            }
        )
        
        return jsonify({
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "errors": result.stderr,
            "returncode": result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Sync timed out"}), 504
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8766)
