"""In-memory sliding-window rate limiter keyed by user id (or IP).
NOTE: per-instance only. On serverless it limits per warm instance; use Redis/Upstash for a global limit."""
import time
from collections import defaultdict, deque

from fastapi import Request

from .config import get_settings
from .errors import ApiError

_hits: dict[str, deque] = defaultdict(deque)


def check(key: str, limit: int | None = None, window: float = 60.0) -> None:
    limit = limit or get_settings().rate_limit_per_minute
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise ApiError(429, "rate_limited", "Too many requests. Please slow down.")
    q.append(now)


def limiter(bucket: str, limit: int | None = None):
    def dep(request: Request) -> None:
        auth = request.headers.get("authorization", "")
        who = auth[-24:] if auth else (request.client.host if request.client else "anon")
        check(f"{bucket}:{who}", limit)
    return dep
