"""
Gong API HTTP Client
Handles all interactions with the Gong REST API v2.
"""

import base64
from datetime import date
import logging
import os
from typing import Optional
import urllib.request
import urllib.parse
import urllib.error
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


GONG_BASE_URL = "https://api.gong.io/v2"
logger = logging.getLogger(__name__)


def _load_env_file() -> None:
    """Load simple KEY=VALUE pairs from a local .env file if present."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        logger.info("No .env file found at %s; using process environment variables.", env_path)
        return

    loaded_count = 0
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
            if key not in os.environ:
                loaded_count += 1
            os.environ.setdefault(key, value)

    logger.info("Loaded %d variable(s) from .env.", loaded_count)


_load_env_file()


class GongClient:
    """HTTP client for the Gong API v2."""

    def __init__(self, access_key: str, access_secret: str):
        """
        Initialize the Gong client.

        Args:
            access_key: Gong API access key (from Gong Settings → API).
            access_secret: Gong API secret.
        """
        if not access_key or not access_secret:
            raise ValueError("Both access_key and access_secret are required.")
        credentials = f"{access_key}:{access_secret}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        self._auth_header = f"Basic {encoded}"

    # ── Private helpers ───────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
    ) -> dict:
        """
        Execute an authenticated HTTP request against the Gong API.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: API path, e.g. "/calls".
            params: Optional query string parameters.
            body: Optional JSON body payload.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            GongAPIError: On non-2xx responses.
            GongConnectionError: On network-level failures.
        """
        url = GONG_BASE_URL + path
        if params:
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            url = f"{url}?{query}"

        logger.info("Gong API request: %s %s", method, path)

        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", self._auth_header)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")

        try:
            payload = json.dumps(body).encode("utf-8") if body is not None else None
            with urllib.request.urlopen(req, data=payload) as resp:
                resp_body = resp.read().decode("utf-8")
                return json.loads(resp_body) if resp_body else {}
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8") if exc.fp else ""
            try:
                detail = json.loads(err_body)
            except json.JSONDecodeError:
                detail = err_body
            logger.error("Gong API HTTP error on %s %s: %s %s", method, path, exc.code, exc.reason)
            raise GongAPIError(exc.code, exc.reason, detail) from exc
        except urllib.error.URLError as exc:
            logger.error("Gong API connection error on %s %s: %s", method, path, exc.reason)
            raise GongConnectionError(str(exc.reason)) from exc

    # ── Public API methods ────────────────────────────────────────────────────

    @staticmethod
    def _call_matches_account(call: dict, account_name: str) -> bool:
        """Best-effort account matching against fields available in /calls payload."""
        if not account_name:
            return True

        needle = account_name.strip().lower()
        if not needle:
            return True

        haystacks = [
            str(call.get("title") or "").lower(),
            str(call.get("clientUniqueId") or "").lower(),
            str(call.get("meetingUrl") or "").lower(),
            str(call.get("url") or "").lower(),
            json.dumps(call.get("customData") or {}).lower(),
        ]

        # Some tenants may include parties on /calls responses.
        parties = call.get("parties") or []
        for party in parties:
            haystacks.append(str(party.get("name") or "").lower())
            haystacks.append(str(party.get("emailAddress") or "").lower())

        return any(needle in h for h in haystacks)

    @staticmethod
    def _extract_custom_account_values(custom_data) -> set[str]:
        """Extract account-like string values from nested customData structures."""
        values: set[str] = set()
        if custom_data is None:
            return values

        keys_hint = ("account", "client", "customer", "company", "organization", "org")

        def walk(node, parent_key: Optional[str] = None):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, str(k).lower())
                return
            if isinstance(node, list):
                for item in node:
                    walk(item, parent_key)
                return
            if isinstance(node, str):
                text = node.strip()
                if not text:
                    return
                if parent_key and any(h in parent_key for h in keys_hint):
                    values.add(text)

        walk(custom_data)
        return values

    @staticmethod
    def _infer_account_from_title(title: str) -> Optional[str]:
        """Best-effort account extraction from call title prefix."""
        if not title:
            return None

        candidate = title.strip()
        for sep in (" - ", " :: ", " / ", " | ", ": "):
            if sep in candidate:
                candidate = candidate.split(sep, 1)[0].strip()
                break

        # Drop very noisy candidates (mostly initials/symbols).
        if len(candidate) < 3:
            return None
        if not re.search(r"[A-Za-z]", candidate):
            return None
        return candidate

    def list_calls(
        self,
        account_name: Optional[str] = None,
        from_date: Optional[date | str] = None,
        to_date: Optional[date | str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        List calls, optionally filtered by account name and date range.

        Args:
            account_name: Account/client name to search for.
            from_date: Start date (date object or ISO string "YYYY-MM-DD").
            to_date: End date (date object or ISO string "YYYY-MM-DD").
            limit: Maximum number of calls to return (default 10).

        Returns:
            List of call objects.
        """
        params: dict = {}
        if account_name:
            params["accountName"] = account_name
        if from_date:
            d = from_date.isoformat() if isinstance(from_date, date) else from_date
            params["fromDateTime"] = f"{d}T00:00:00Z"
        if to_date:
            d = to_date.isoformat() if isinstance(to_date, date) else to_date
            params["toDateTime"] = f"{d}T23:59:59Z"

        all_calls: list[dict] = []
        cursor: Optional[str] = None

        while True:
            page_params = dict(params)
            if cursor:
                page_params["cursor"] = cursor

            data = self._request("GET", "/calls", params=page_params)
            page_calls = data.get("calls") or []

            # Gong may ignore accountName on /calls for some tenants.
            # Enforce account filtering client-side so returned calls match the input.
            if account_name:
                page_calls = [c for c in page_calls if self._call_matches_account(c, account_name)]

            all_calls.extend(page_calls)

            if len(all_calls) >= limit:
                break

            records = data.get("records") or {}
            cursor = records.get("cursor")
            if not cursor:
                break

        return all_calls[:limit]

    def get_call_transcript(self, call_id: str) -> list[dict]:
        """
        Fetch the transcript for a specific call.

        Args:
            call_id: Gong call identifier.

        Returns:
            List of transcript segment objects, each with speakerName and sentences.
        """
        # Gong transcript API expects POST /calls/transcript with callIds filter.
        # Keep a fallback to older per-call endpoint for compatibility.
        data = self._request(
            "POST",
            "/calls/transcript",
            params=None,
            body={"filter": {"callIds": [call_id]}},
        )

        # Current response shape includes callTranscripts array.
        if isinstance(data, dict) and "callTranscripts" in data:
            entries = data.get("callTranscripts") or []
            if entries:
                # Each entry may include either transcript or transcriptSegments.
                first = entries[0] or {}
                return (
                    first.get("transcript")
                    or first.get("transcriptSegments")
                    or []
                )

        # Backward-compatible fallback for older Gong tenants/contracts.
        try:
            legacy = self._request("GET", f"/calls/{call_id}/transcript")
            return legacy.get("transcript") or []
        except GongAPIError:
            logger.warning("Transcript unavailable for call_id=%s via both transcript endpoints.", call_id)
            return []

    def list_account_names(
        self,
        from_date: Optional[date | str] = None,
        to_date: Optional[date | str] = None,
        max_calls: int = 100,
        include_inferred_from_title: bool = True,
    ) -> list[str]:
        """
        Return distinct account names found in Gong calls.

        The method first uses explicit account-related fields when available
        (`clientUniqueId`, `customData`, party affiliation/company). Since some
        tenants do not expose dedicated account metadata on `/calls`, it can
        optionally infer account names from call title prefixes.

        Args:
            from_date: Optional start date filter.
            to_date: Optional end date filter.
            max_calls: Max number of calls to scan (default 100).
            include_inferred_from_title: Include best-effort title inference.

        Returns:
            Sorted list of unique account names.
        """
        calls = self.list_calls(
            account_name=None,
            from_date=from_date,
            to_date=to_date,
            limit=max_calls,
        )

        account_names: set[str] = set()
        for call in calls:
            client_id = str(call.get("clientUniqueId") or "").strip()
            if client_id:
                account_names.add(client_id)

            for value in self._extract_custom_account_values(call.get("customData")):
                account_names.add(value)

            # Some tenants may include parties with affiliation/company fields.
            for party in (call.get("parties") or []):
                for key in ("affiliation", "company", "organization"):
                    value = str(party.get(key) or "").strip()
                    if value:
                        account_names.add(value)

            if include_inferred_from_title:
                inferred = self._infer_account_from_title(str(call.get("title") or ""))
                if inferred:
                    account_names.add(inferred)

        return sorted(account_names, key=lambda n: n.lower())

    def list_lead_company_and_account_names(
        self,
        from_date: Optional[date | str] = None,
        to_date: Optional[date | str] = None,
        max_calls: int = 1000,
    ) -> dict:
        """
        Return both account names and lead company names.

        Since this tenant does not expose CRM lead/account endpoints, this method
        combines explicit account-like metadata from calls with best-effort lead
        company inference from external call titles.

        Args:
            from_date: Optional start date filter.
            to_date: Optional end date filter.
            max_calls: Max number of calls to scan (default 1000).

        Returns:
            Dict with:
            - account_names: sorted unique account names
            - lead_company_names: sorted unique lead company names
        """
        calls = self.list_calls(
            account_name=None,
            from_date=from_date,
            to_date=to_date,
            limit=max_calls,
        )

        account_names: set[str] = set()
        lead_company_names: set[str] = set()

        for call in calls:
            client_id = str(call.get("clientUniqueId") or "").strip()
            if client_id:
                account_names.add(client_id)

            custom_values = self._extract_custom_account_values(call.get("customData"))
            account_names.update(custom_values)

            for party in (call.get("parties") or []):
                for key in ("affiliation", "company", "organization"):
                    value = str(party.get(key) or "").strip()
                    if value:
                        account_names.add(value)

            inferred = self._infer_account_from_title(str(call.get("title") or ""))
            if inferred:
                account_names.add(inferred)

                # Prioritize external calls as lead-company candidates.
                if str(call.get("scope") or "").lower() == "external":
                    lead_company_names.add(inferred)

        # If no external-only lead names found, fallback to all inferred names.
        if not lead_company_names:
            lead_company_names = {
                self._infer_account_from_title(str(call.get("title") or ""))
                for call in calls
                if self._infer_account_from_title(str(call.get("title") or ""))
            } # type: ignore

        return {
            "account_names": sorted(account_names, key=lambda n: n.lower()),
            "lead_company_names": sorted(lead_company_names, key=lambda n: n.lower()),
        }

    def get_calls_with_transcripts(
        self,
        account_name: Optional[str] = None,
        from_date: Optional[date | str] = None,
        to_date: Optional[date | str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Convenience method: fetch calls and attach their full transcripts.

        Args:
            account_name: Account/client name to search for.
            from_date: Start date.
            to_date: End date.
            limit: Maximum number of calls to fetch (default 10).

        Returns:
            List of enriched call dicts with an added "transcript_text" field
            (plain-text concatenation of all speaker turns) and "transcript_raw"
            (raw segment objects from the API).
        """
        calls = self.list_calls(
            account_name=account_name,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
        )

        enriched = []
        for call in calls:
            call_id = call.get("id")
            segments = self.get_call_transcript(call_id) if call_id else []
            transcript_text = "\n".join(
                f"{seg.get('speakerName', 'Unknown')}: "
                + " ".join(s.get("text", "") for s in (seg.get("sentences") or []))
                for seg in segments
            )
            enriched.append(
                {
                    "id": call_id,
                    "title": call.get("title") or "Untitled Call",
                    "date": (call.get("started") or "")[:10],
                    "duration_seconds": call.get("duration"),
                    "duration_label": (
                        f"{round(call.get('duration', 0) / 60)} min"
                        if call.get("duration")
                        else "—"
                    ),
                    "participants": ", ".join(
                        p.get("name", "") for p in (call.get("parties") or [])
                    ) or "—",
                    "transcript_text": transcript_text,
                    "transcript_raw": segments,
                    "_raw": call,
                }
            )

        return enriched


# ── Exceptions ────────────────────────────────────────────────────────────────


class GongAPIError(Exception):
    """Raised when Gong returns a non-2xx HTTP response."""

    def __init__(self, status_code: int, reason: str, detail):
        self.status_code = status_code
        self.reason = reason
        self.detail = detail
        super().__init__(f"Gong API error {status_code} {reason}: {detail}")


class GongConnectionError(Exception):
    """Raised on network-level failures when reaching the Gong API."""


# ── Local HTTP bridge ─────────────────────────────────────────────────────────


def _make_http_handler():
    class GongBridgeHandler(BaseHTTPRequestHandler):
        def _write_json(self, status_code: int, payload: dict):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            if self.path == "/health":
                logger.info("Health check requested.")
                self._write_json(200, {"ok": True, "service": "gong-bridge"})
                return
            logger.warning("Unhandled GET path requested: %s", self.path)
            self._write_json(404, {"error": "Not Found"})

        def do_POST(self):
            if self.path != "/api/gong/calls-with-transcripts":
                logger.warning("Unhandled POST path requested: %s", self.path)
                self._write_json(404, {"error": "Not Found"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                payload = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON payload received on %s", self.path)
                self._write_json(400, {"error": "Invalid JSON payload"})
                return

            access_key = str(os.getenv("GONG_ACCESS_KEY") or "").strip()
            access_secret = str(os.getenv("GONG_ACCESS_SECRET") or "").strip()
            account_name = str(payload.get("accountName") or "").strip() or None
            from_date = str(payload.get("fromDate") or "").strip() or None
            to_date = str(payload.get("toDate") or "").strip() or None
            limit = int(payload.get("limit") or 10)

            if not access_key or not access_secret:
                logger.error("Missing Gong credentials in environment.")
                self._write_json(
                    500,
                    {
                        "error": "Missing server credentials",
                        "detail": "Set GONG_ACCESS_KEY and GONG_ACCESS_SECRET in your .env file or environment.",
                    },
                )
                return

            try:
                client = GongClient(access_key, access_secret)
                calls = client.get_calls_with_transcripts(
                    account_name=account_name,
                    from_date=from_date,
                    to_date=to_date,
                    limit=limit,
                )
                logger.info(
                    "Returning %d call(s) for account=%s range=%s..%s limit=%d",
                    len(calls),
                    account_name or "*",
                    from_date or "*",
                    to_date or "*",
                    limit,
                )

                calls_payload = [
                    {
                        "id": c.get("id"),
                        "title": c.get("title") or "Untitled Call",
                        "date": c.get("date") or "—",
                        "duration": c.get("duration_label") or "—",
                        "participants": c.get("participants") or "—",
                        "transcript": c.get("transcript_text") or "",
                    }
                    for c in calls
                ]
                self._write_json(200, {"calls": calls_payload})
            except GongAPIError as exc:
                logger.error("Bridge failed due to Gong API error: %s", exc)
                self._write_json(
                    502,
                    {
                        "error": "Gong API error",
                        "detail": str(exc),
                        "statusCode": exc.status_code,
                    },
                )
            except GongConnectionError as exc:
                logger.error("Bridge failed due to Gong connection error: %s", exc)
                self._write_json(502, {"error": "Connection error", "detail": str(exc)})
            except Exception as exc:  # pragma: no cover
                logger.exception("Unexpected bridge error.")
                self._write_json(500, {"error": "Internal server error", "detail": str(exc)})

        def log_message(self, format: str, *args):  # pragma: no cover
            return

    return GongBridgeHandler


def run_bridge_server(host: str = "127.0.0.1", port: int = 8765):
    """Run a local HTTP server that proxies Gong API requests for the HTML app."""
    handler = _make_http_handler()
    server = ThreadingHTTPServer((host, port), handler)
    logger.info("Gong bridge running at http://%s:%d", host, port)
    logger.info("POST /api/gong/calls-with-transcripts")
    logger.info("GET /health")
    server.serve_forever()


# ── CLI convenience ───────────────────────────────────────────────────────────


def _main():
    """
    Quick CLI / server entrypoint.
    Usage:
        python gongClient.py serve [port]
        python gongClient.py <access_key> <access_secret> [account_name] [from_date] [to_date]
    Date format: YYYY-MM-DD
    """
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) >= 2 and sys.argv[1].lower() == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
        run_bridge_server(port=port)
        return

    if len(sys.argv) < 3:
        print(
            "Usage: python gongClient.py serve [port]\n"
            "   or: python gongClient.py <access_key> <access_secret> "
            "[account_name] [from_date] [to_date]"
        )
        sys.exit(1)

    access_key = sys.argv[1]
    access_secret = sys.argv[2]
    account_name = sys.argv[3] if len(sys.argv) > 3 else None
    from_date = sys.argv[4] if len(sys.argv) > 4 else None
    to_date = sys.argv[5] if len(sys.argv) > 5 else None

    client = GongClient(access_key, access_secret)

    print("Fetching lead companies and account names…")
    try:
        result = client.list_lead_company_and_account_names(
            from_date=from_date,
            to_date=to_date,
            max_calls=5000,
        )
        accounts = result.get("account_names") or []
        lead_companies = result.get("lead_company_names") or []

        if account_name:
            needle = account_name.strip().lower()
            accounts = [name for name in accounts if needle in name.lower()]
            lead_companies = [name for name in lead_companies if needle in name.lower()]

        print(f"Found {len(lead_companies)} lead company name(s).")
        for name in lead_companies:
            print(f"  - {name}")

        print(f"\nFound {len(accounts)} account name(s).")
        if account_name and not accounts and not lead_companies:
            print(
                "No lead company/account names matched the filter. "
                "Try a broader search term."
            )

        for name in accounts:
            print(f"  - {name}")
    except GongAPIError as exc:
        print(f"API error: {exc}")
        sys.exit(1)
    except GongConnectionError as exc:
        print(f"Connection error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    _main()
