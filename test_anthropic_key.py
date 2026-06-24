#!/usr/bin/env python3
"""Simple test to verify Anthropic API key is valid."""

import json
import sys
import urllib.request
import urllib.error

if len(sys.argv) < 2:
    print("Usage: python test_anthropic_key.py <YOUR_API_KEY>")
    print("Example: python test_anthropic_key.py sk-ant-v0-xxxxx")
    sys.exit(1)

api_key = sys.argv[1].strip()

if not api_key.startswith("sk-ant-"):
    print(f"ERROR: Key should start with 'sk-ant-', got: {api_key[:20]}")
    sys.exit(1)

print(f"Testing Anthropic API key: {api_key[:30]}...")
print(f"Key length: {len(api_key)} characters")

# Simple test message
payload = {
    "model": "claude-sonnet-4-6",
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "Say 'API key is valid' if you can read this."}],
}

url = "https://api.anthropic.com/v1/messages"

req = urllib.request.Request(url, method="POST")
req.add_header("Content-Type", "application/json")
req.add_header("x-api-key", api_key)
req.add_header("anthropic-version", "2023-06-01")

try:
    print("\nSending test request to Anthropic API...")
    body = json.dumps(payload).encode("utf-8")
    with urllib.request.urlopen(req, data=body, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print("✅ SUCCESS! API key is valid.")
        print(f"Response: {data.get('content', [{}])[0].get('text', '')}")
except urllib.error.HTTPError as exc:
    raw = exc.read().decode("utf-8") if exc.fp else ""
    print(f"❌ HTTP Error {exc.code}: {exc.reason}")
    try:
        error_data = json.loads(raw)
        print(f"Error details: {json.dumps(error_data, indent=2)}")
    except:
        print(f"Error response: {raw}")
    sys.exit(1)
except Exception as exc:
    print(f"❌ Error: {exc}")
    sys.exit(1)
