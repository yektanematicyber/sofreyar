import os
import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from fastapi import HTTPException, Request, status

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)


class RateLimiter:
    """Sliding-window in-memory rate limiter per client IP and endpoint path.

    Requires zero external dependencies and enforces standard HTTP 429 Too Many
    Requests with a Retry-After header.
    """

    def __init__(self, times: int, seconds: int):
        self.times = times
        self.seconds = seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def __call__(self, request: Request) -> None:
        if not RATE_LIMIT_ENABLED:
            return

        # Extract client IP (handles reverse proxy / docker X-Forwarded-For)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "127.0.0.1"

        key = f"{client_ip}:{request.url.path}"
        now = time.monotonic()

        with self.lock:
            # Purge timestamps outside the sliding window
            cutoff = now - self.seconds
            active_timestamps = [t for t in self.requests[key] if t > cutoff]

            if len(active_timestamps) >= self.times:
                oldest = active_timestamps[0]
                retry_after = max(1, int(self.seconds - (now - oldest)))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

            active_timestamps.append(now)
            self.requests[key] = active_timestamps
