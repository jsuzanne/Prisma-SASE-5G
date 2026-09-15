"""API Debug Logger & Inspector for Prisma SASE 5G.

Captures inbound and outbound API transactions (requests, payloads, responses, headers, timings)
into an in-memory ring-buffer for real-time inspection, copying, and troubleshooting.
"""

import time
import json
import uuid
import shlex
import threading
from collections import deque
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone


def sanitize_headers(headers: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Sanitize sensitive headers like Authorization Bearer tokens."""
    if not headers:
        return {}
    sanitized = {}
    for k, v in headers.items():
        k_lower = k.lower()
        v_str = str(v)
        if k_lower == "authorization":
            if v_str.lower().startswith("bearer "):
                token_val = v_str[7:]
                if len(token_val) > 12:
                    masked = f"Bearer {token_val[:6]}...{token_val[-4:]}"
                else:
                    masked = "Bearer ***"
                sanitized[k] = masked
            else:
                sanitized[k] = "***"
        elif any(sec in k_lower for sec in ["secret", "password", "key", "token"]):
            if len(v_str) > 8:
                sanitized[k] = f"{v_str[:3]}...{v_str[-3:]}"
            else:
                sanitized[k] = "***"
        else:
            sanitized[k] = v_str
    return sanitized


def generate_curl_command(
    method: str,
    url: str,
    headers: Optional[Dict[str, Any]] = None,
    body: Optional[Any] = None,
) -> str:
    """Generate a clean, reproducible cURL command."""
    parts = ["curl", "-X", method.upper(), shlex.quote(url)]
    
    clean_headers = sanitize_headers(headers)
    for k, v in clean_headers.items():
        parts.extend(["-H", shlex.quote(f"{k}: {v}")])
        
    if body is not None:
        if isinstance(body, (dict, list)):
            body_str = json.dumps(body, indent=2)
            parts.extend(["-d", shlex.quote(body_str)])
        elif isinstance(body, str) and body.strip():
            parts.extend(["-d", shlex.quote(body)])
            
    return " ".join(parts)


class APITransaction:
    """Represents a single recorded API transaction."""

    def __init__(
        self,
        method: str,
        url: str,
        path: str,
        request_headers: Optional[Dict[str, Any]] = None,
        request_body: Optional[Any] = None,
        response_status: Optional[int] = None,
        response_headers: Optional[Dict[str, Any]] = None,
        response_body: Optional[Any] = None,
        duration_ms: float = 0.0,
        error: Optional[str] = None,
        source: str = "SCM API",
        transaction_id: Optional[str] = None,
    ):
        self.id = transaction_id or str(uuid.uuid4())[:8]
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.time_local = datetime.now().strftime("%H:%M:%S")
        self.method = method.upper()
        self.url = url
        self.path = path
        self.source = source
        self.request_headers = sanitize_headers(request_headers)
        self.request_body = request_body
        self.response_status = response_status
        self.response_headers = sanitize_headers(response_headers) if response_headers else {}
        self.response_body = response_body
        self.duration_ms = round(duration_ms, 2)
        self.error = error
        self.curl_command = generate_curl_command(method, url, request_headers, request_body)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize transaction to dict."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "time_local": self.time_local,
            "source": self.source,
            "method": self.method,
            "url": self.url,
            "path": self.path,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "response_status": self.response_status,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "curl_command": self.curl_command,
        }


class APIDebugLogger:
    """Thread-safe ring buffer storing recent API transactions."""

    def __init__(self, max_capacity: int = 150):
        self.max_capacity = max_capacity
        self._buffer: deque = deque(maxlen=max_capacity)
        self._lock = threading.Lock()

    def record(
        self,
        method: str,
        url: str,
        path: str,
        request_headers: Optional[Dict[str, Any]] = None,
        request_body: Optional[Any] = None,
        response_status: Optional[int] = None,
        response_headers: Optional[Dict[str, Any]] = None,
        response_body: Optional[Any] = None,
        duration_ms: float = 0.0,
        error: Optional[str] = None,
        source: str = "SCM API",
    ) -> APITransaction:
        """Record an API transaction in the ring buffer."""
        # Try parsing json bodies if given as string
        req_parsed = request_body
        if isinstance(request_body, str):
            try:
                req_parsed = json.loads(request_body)
            except Exception:
                req_parsed = request_body

        resp_parsed = response_body
        if isinstance(response_body, str):
            try:
                resp_parsed = json.loads(response_body)
            except Exception:
                resp_parsed = response_body

        tx = APITransaction(
            method=method,
            url=url,
            path=path,
            request_headers=request_headers,
            request_body=req_parsed,
            response_status=response_status,
            response_headers=response_headers,
            response_body=resp_parsed,
            duration_ms=duration_ms,
            error=error,
            source=source,
        )

        with self._lock:
            self._buffer.appendleft(tx)

        return tx

    def get_logs(
        self,
        limit: int = 50,
        search: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve filtered logs in reverse chronological order (newest first)."""
        with self._lock:
            items = list(self._buffer)

        results = []
        search_lower = search.lower().strip() if search else None
        method_upper = method.upper().strip() if method else None

        for tx in items:
            if method_upper and tx.method != method_upper:
                continue
            if status_code is not None and tx.response_status != status_code:
                continue
            if search_lower:
                matchable_text = f"{tx.method} {tx.url} {tx.path} {tx.response_status} {json.dumps(tx.request_body)} {json.dumps(tx.response_body)}".lower()
                if search_lower not in matchable_text:
                    continue
            results.append(tx.to_dict())
            if len(results) >= limit:
                break

        return results

    def get_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        """Find a single transaction by ID."""
        with self._lock:
            for tx in self._buffer:
                if tx.id == log_id:
                    return tx.to_dict()
        return None

    def set_capacity(self, new_capacity: int) -> int:
        """Dynamically resize the ring buffer preserving recent items."""
        new_capacity = max(10, min(1000, int(new_capacity)))
        with self._lock:
            self.max_capacity = new_capacity
            self._buffer = deque(self._buffer, maxlen=new_capacity)
        return self.max_capacity

    def clear(self) -> int:
        """Clear all stored transactions."""
        with self._lock:
            count = len(self._buffer)
            self._buffer.clear()
            return count

    def count(self) -> int:
        """Get the current number of stored transactions."""
        with self._lock:
            return len(self._buffer)


def _get_default_buffer_capacity() -> int:
    """Read default buffer capacity from environment if provided."""
    try:
        return max(10, min(1000, int(os.environ.get("API_DEBUG_BUFFER_SIZE", "150"))))
    except Exception:
        return 150


# Global singleton instance
api_debug_logger = APIDebugLogger(max_capacity=_get_default_buffer_capacity())
