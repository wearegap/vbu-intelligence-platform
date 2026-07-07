"""
Local Anthropic HTTP bridge for gap-gong-cost-platform.html.
Run:
    python anthropicClient.py serve 8766
"""

import json
import logging
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-6"
PRIMARY_MAX_TOKENS = 2200
RETRY_MAX_TOKENS = 4200
REPAIR_MAX_TOKENS = 4200


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _load_env_file() -> None:
    """Load simple KEY=VALUE pairs from a local .env file if present."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        logger.info("No .env file found at %s", env_path)
        return

    logger.info("Loading environment variables from %s", env_path)
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
            prompt = f.read().strip()
            logger.info("Loaded system prompt from %s", prompt_path)
            return prompt
    except FileNotFoundError:
        logger.error("System prompt file not found: %s", prompt_path)
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

    @staticmethod
    def _extract_first_json_object(text: str) -> str:
        """Return the first top-level JSON object found in a text blob."""
        if not text:
            return ""

        start = text.find("{")
        if start < 0:
            return ""

        depth = 0
        in_string = False
        escaped = False
        for idx in range(start, len(text)):
            ch = text[idx]

            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : idx + 1]

        # No balanced object found; likely truncated output.
        return ""

    @staticmethod
    def _parse_model_json(raw_text: str) -> dict:
        """Parse model text into JSON with a best-effort extraction strategy."""
        clean = raw_text.replace("```json", "").replace("```", "").strip()
        if not clean:
            return {}

        # First try direct parsing (fast path).
        try:
            parsed = json.loads(clean)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            pass

        # Then try first balanced object in mixed-content text.
        candidate = AnthropicClient._extract_first_json_object(clean)
        if candidate:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {"value": parsed}

        raise json.JSONDecodeError("No complete JSON object found in model output", clean, 0)

    def _send_messages_request(self, prompt: str, max_tokens: int = 1000) -> dict:
        payload = {
            "model": DEFAULT_MODEL,
            "max_tokens": max_tokens,
            "temperature": 0,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        }

        req = urllib.request.Request(ANTHROPIC_URL, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", self.api_key)
        req.add_header("anthropic-version", ANTHROPIC_VERSION)

        body = json.dumps(payload).encode("utf-8")
        logger.info("Sending request to Anthropic messages API (max_tokens=%s)", max_tokens)
        with urllib.request.urlopen(req, data=body) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _extract_text_block(data: dict) -> str:
        blocks = data.get("content") or []
        parts: list[str] = []
        for block in blocks:
            if block.get("type") == "text":
                parts.append(block.get("text") or "")
        return "\n".join(parts).strip()

    def extract_modernization_signals(self, client_name: str, transcript_text: str) -> dict:
        logger.info("Extracting modernization signals for client '%s'", client_name)
        prompt = (
            f'Extract modernization signals from these call transcripts for client "{client_name}":\n\n'
            f"{transcript_text}"
        )

        try:
            data = self._send_messages_request(prompt, max_tokens=PRIMARY_MAX_TOKENS)
            logger.info("Received successful response from Anthropic API")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else ""
            try:
                detail = json.loads(raw)
            except json.JSONDecodeError:
                detail = raw
            logger.error("Anthropic API HTTP error %s %s", exc.code, exc.reason)
            raise AnthropicAPIError(exc.code, exc.reason, detail) from exc
        except urllib.error.URLError as exc:
            logger.error("Anthropic API connection error: %s", exc.reason)
            raise AnthropicConnectionError(str(exc.reason)) from exc

        raw_text = self._extract_text_block(data)
        stop_reason = str(data.get("stop_reason") or "")
        if stop_reason == "max_tokens":
            logger.warning("Primary response hit max_tokens; retrying with a larger token budget")
        else:
            try:
                return self._parse_model_json(raw_text)
            except json.JSONDecodeError:
                logger.warning("Primary model output was not valid JSON; retrying with strict JSON instruction")

        retry_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Return ONLY one valid JSON object. "
            "No markdown fences, no explanations, no trailing text. "
            "Keep reasoning fields concise."
        )
        retry_data: dict = {}

        try:
            retry_data = self._send_messages_request(retry_prompt, max_tokens=RETRY_MAX_TOKENS)
            retry_text = self._extract_text_block(retry_data)
            return self._parse_model_json(retry_text)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else ""
            try:
                detail = json.loads(raw)
            except json.JSONDecodeError:
                detail = raw
            logger.error("Anthropic API HTTP error on retry %s %s", exc.code, exc.reason)
            raise AnthropicAPIError(exc.code, exc.reason, detail) from exc
        except urllib.error.URLError as exc:
            logger.error("Anthropic API connection error on retry: %s", exc.reason)
            raise AnthropicConnectionError(str(exc.reason)) from exc
        except json.JSONDecodeError:
            logger.warning("Retry output still invalid; attempting repair pass")

        partial = self._extract_text_block(retry_data) or raw_text
        repair_prompt = (
            "You will receive malformed or truncated JSON. Repair it into one valid JSON object that preserves existing values. "
            "If data is missing, use null, false, 0, \"unknown\", or estimator defaults consistent with fields. "
            "Return ONLY JSON.\n\n"
            f"Malformed JSON:\n{partial[:12000]}"
        )

        repair_data: dict = {}
        try:
            repair_data = self._send_messages_request(repair_prompt, max_tokens=REPAIR_MAX_TOKENS)
            return self._parse_model_json(self._extract_text_block(repair_data))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else ""
            try:
                detail = json.loads(raw)
            except json.JSONDecodeError:
                detail = raw
            logger.error("Anthropic API HTTP error on repair %s %s", exc.code, exc.reason)
            raise AnthropicAPIError(exc.code, exc.reason, detail) from exc
        except urllib.error.URLError as exc:
            logger.error("Anthropic API connection error on repair: %s", exc.reason)
            raise AnthropicConnectionError(str(exc.reason)) from exc
        except json.JSONDecodeError as exc:
            final_text = self._extract_text_block(repair_data) or partial
            snippet = re.sub(r"\s+", " ", final_text)[:1000]
            logger.error("Model output was not valid JSON after retry and repair")
            raise AnthropicAPIError(502, "Bad Model Output", snippet or "<empty>") from exc


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
                logger.info("Health check requested")
                self._write_json(200, {"ok": True, "service": "anthropic-bridge"})
                return
            logger.warning("Unknown GET path requested: %s", self.path)
            self._write_json(404, {"error": "Not Found"})

        def do_POST(self):
            if self.path != "/api/anthropic/extract-signals":
                logger.warning("Unknown POST path requested: %s", self.path)
                self._write_json(404, {"error": "Not Found"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                payload = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON payload received")
                self._write_json(400, {"error": "Invalid JSON payload"})
                return

            anthropic_key = str(os.getenv("ANTHROPIC_API_KEY") or "").strip()
            client_name = str(payload.get("clientName") or "").strip()
            transcript = str(payload.get("transcript") or "").strip()

            if not anthropic_key:
                logger.error("ANTHROPIC_API_KEY is missing from environment")
                self._write_json(
                    500,
                    {
                        "error": "Missing server credentials",
                        "detail": "Set ANTHROPIC_API_KEY in your .env file or environment.",
                    },
                )
                return
            if not anthropic_key.startswith("sk-ant-"):
                logger.warning("ANTHROPIC_API_KEY format is invalid")
                self._write_json(400, {
                    "error": "Invalid anthropicKey format",
                    "detail": "The configured ANTHROPIC_API_KEY should start with 'sk-ant-'."
                })
                return
            if not transcript:
                logger.warning("Request rejected because transcript is missing")
                self._write_json(400, {"error": "transcript is required"})
                return

            try:
                logger.info("Processing extraction request for client '%s'", client_name or "Client")
                client = AnthropicClient(anthropic_key)
                extraction = client.extract_modernization_signals(client_name or "Client", transcript)
                logger.info("Extraction request completed successfully")
                self._write_json(200, {"extraction": extraction})
            except AnthropicAPIError as exc:
                logger.error("Anthropic API error while processing request: %s", exc)
                self._write_json(
                    502,
                    {
                        "error": "Anthropic API error",
                        "detail": str(exc),
                        "statusCode": exc.status_code,
                    },
                )
            except AnthropicConnectionError as exc:
                logger.error("Connection error while processing request: %s", exc)
                self._write_json(502, {"error": "Connection error", "detail": str(exc)})
            except Exception as exc:  # pragma: no cover
                logger.error("Unhandled server error: %s", exc, exc_info=True)
                self._write_json(500, {"error": "Internal server error", "detail": str(exc)})

        def log_message(self, format: str, *args):  # pragma: no cover
            return

    return AnthropicBridgeHandler


def run_bridge_server(host: str = "127.0.0.1", port: int = 8766):
    handler = _make_handler()
    server = ThreadingHTTPServer((host, port), handler)
    logger.info("Anthropic bridge running at http://%s:%s", host, port)
    logger.info("POST /api/anthropic/extract-signals")
    logger.info("GET  /health")
    print(f"Anthropic bridge running at http://{host}:{port}")
    print("POST /api/anthropic/extract-signals")
    print("GET  /health")
    server.serve_forever()


def _main():
    import sys

    if len(sys.argv) >= 2 and sys.argv[1].lower() == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8766
        logger.info("Starting bridge server on port %s", port)
        run_bridge_server(port=port)
        return

    logger.warning("Invalid invocation. Expected: python anthropicClient.py serve [port]")
    print("Usage: python anthropicClient.py serve [port]")


if __name__ == "__main__":
    _main()
