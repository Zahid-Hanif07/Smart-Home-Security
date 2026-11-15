"""Small dependency-free per-process IP rate limiter for API abuse resistance.

Deployments with multiple workers should enforce an equivalent limit at the
reverse proxy because each worker keeps its own bounded in-memory counters.
"""

from collections import deque
import time

from starlette.responses import JSONResponse


class RequestRateLimitMiddleware:
    def __init__(self, app, requests_per_minute: int = 1200, max_clients: int = 4096):
        self.app = app
        self.limit = max(1, requests_per_minute)
        self.window_seconds = 60.0
        self.max_clients = max(64, max_clients)
        self._requests: dict[str, deque[float]] = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path in {"/", "/health", "/ready"}:
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        key = client[0] if client else "unknown"
        now = time.monotonic()
        entries = self._requests.setdefault(key, deque())
        while entries and now - entries[0] >= self.window_seconds:
            entries.popleft()
        if len(entries) >= self.limit:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Request rate limit exceeded. Retry shortly."},
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return
        entries.append(now)
        if len(self._requests) > self.max_clients:
            expired = [address for address, times in self._requests.items() if not times or now - times[-1] >= self.window_seconds]
            for address in expired:
                self._requests.pop(address, None)
            while len(self._requests) > self.max_clients:
                self._requests.pop(next(iter(self._requests)))
        await self.app(scope, receive, send)
