"""
Local Anthropic HTTP bridge for gap-gong-cost-platform.html.
Run:
    python anthropicClient.py serve 8766
"""

import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-6"


def _load_env_file() -> None:
    """Load simple KEY=VALUE pairs from a local .env file if present."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_env_file()


def _load_system_prompt() -> str:
    """Load system prompt from transcripts.md file."""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts\\transcripts.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise RuntimeError(f"System prompt file not found: {prompt_path}")


SYSTEM_PROMPT = _load_system_prompt()


class AnthropicAPIError(Exception):
    """Raised when Anthropic returns a non-2xx response."""

    def __init__(self, status_code: int, reason: str, detail):
        self.status_code = status_code
        self.reason = reason
        self.detail = detail
        super().__init__(f"Anthropic API error {status_code} {reason}: {detail}")


class AnthropicConnectionError(Exception):
    """Raised on network-level failures when reaching Anthropic."""


class AnthropicClient:
    """Small HTTP client for Anthropic messages API."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key

    def extract_modernization_signals(self, client_name: str, transcript_text: str) -> dict:
        prompt = (
            f'Extract modernization signals from these call transcripts for client "{client_name}":\n\n'
            f"{transcript_text}"
        )
        payload = {
            "model": DEFAULT_MODEL,
            "max_tokens": 1000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        }

        req = urllib.request.Request(ANTHROPIC_URL, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", self.api_key)
        req.add_header("anthropic-version", ANTHROPIC_VERSION)

        try:
            body = json.dumps(payload).encode("utf-8")
            with urllib.request.urlopen(req, data=body) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else ""
            try:
                detail = json.loads(raw)
            except json.JSONDecodeError:
                detail = raw
            raise AnthropicAPIError(exc.code, exc.reason, detail) from exc
        except urllib.error.URLError as exc:
            raise AnthropicConnectionError(str(exc.reason)) from exc

        blocks = data.get("content") or []
        raw_text = ""
        for block in blocks:
            if block.get("type") == "text":
                raw_text = block.get("text") or ""
                break

        clean = raw_text.replace("```json", "").replace("```", "").strip() or "{}"
        try:
            return json.loads(clean)
        except json.JSONDecodeError as exc:
            raise AnthropicAPIError(502, "Bad Model Output", clean) from exc


def _make_handler():
    class AnthropicBridgeHandler(BaseHTTPRequestHandler):
        def _write_json(self, status_code: int, payload: dict):
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(raw)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            if self.path == "/health":
                self._write_json(200, {"ok": True, "service": "anthropic-bridge"})
                return
            self._write_json(404, {"error": "Not Found"})

        def do_POST(self):
            if self.path != "/api/anthropic/extract-signals":
                self._write_json(404, {"error": "Not Found"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                payload = json.loads(raw)
            except json.JSONDecodeError:
                self._write_json(400, {"error": "Invalid JSON payload"})
                return

            anthropic_key = str(os.getenv("ANTHROPIC_API_KEY") or "").strip()
            client_name = str(payload.get("clientName") or "").strip()
            transcript = str(payload.get("transcript") or "").strip()

            if not anthropic_key:
                self._write_json(
                    500,
                    {
                        "error": "Missing server credentials",
                        "detail": "Set ANTHROPIC_API_KEY in your .env file or environment.",
                    },
                )
                return
            if not anthropic_key.startswith("sk-ant-"):
                self._write_json(400, {
                    "error": "Invalid anthropicKey format",
                    "detail": "The configured ANTHROPIC_API_KEY should start with 'sk-ant-'."
                })
                return
            if not transcript:
                self._write_json(400, {"error": "transcript is required"})
                return

            try:
                client = AnthropicClient(anthropic_key)
                extraction = client.extract_modernization_signals(client_name or "Client", transcript)
                self._write_json(200, {"extraction": extraction})
            except AnthropicAPIError as exc:
                self._write_json(
                    502,
                    {
                        "error": "Anthropic API error",
                        "detail": str(exc),
                        "statusCode": exc.status_code,
                    },
                )
            except AnthropicConnectionError as exc:
                self._write_json(502, {"error": "Connection error", "detail": str(exc)})
            except Exception as exc:  # pragma: no cover
                self._write_json(500, {"error": "Internal server error", "detail": str(exc)})

        def log_message(self, fmt: str, *args):  # pragma: no cover
            return

    return AnthropicBridgeHandler


def run_bridge_server(host: str = "127.0.0.1", port: int = 8766):
    handler = _make_handler()
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Anthropic bridge running at http://{host}:{port}")
    print("POST /api/anthropic/extract-signals")
    print("GET  /health")
    server.serve_forever()


def _main():
    import sys

    if len(sys.argv) >= 2 and sys.argv[1].lower() == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8766
        run_bridge_server(port=port)
        return

    print("Usage: python anthropicClient.py serve [port]")


if __name__ == "__main__":
    _main()
