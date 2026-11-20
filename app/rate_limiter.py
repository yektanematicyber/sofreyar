import logging
import os
import time
from collections import defaultdict
from threading import Lock
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException, Request, status

from app.exceptions import RateLimitExceededException

logger = logging.getLogger("safreyar.ratelimit")

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)

LUA_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

local cutoff = now - window
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local current_count = redis.call('ZCARD', key)

if current_count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local oldest_ts = now
    if oldest and #oldest >= 2 then
        oldest_ts = tonumber(oldest[2])
    end
    local retry_after = math.max(1, math.ceil(window - (now - oldest_ts)))
    return {0, retry_after}
else
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, math.ceil(window + 5))
    return {1, 0}
end
"""


def sanitize_redis_url(url: str) -> str:
    """Masks password and credentials in Redis URL for safe logging."""
    if not url:
        return ""
    try:
        parts = urlsplit(url)
        if parts.password:
            user = parts.username or ""
            port = f":{parts.port}" if parts.port else ""
            if user:
                netloc = f"{user}:***@{parts.hostname}{port}"
            else:
                netloc = f":***@{parts.hostname}{port}"
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
        return url
    except Exception:
        return "redis://***"


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


class UserRateLimiter:
    """Sliding-window per-authenticated-user rate limiter.

    Designed for expensive endpoints like AI recipe suggestions.
    Configurable via environment variables:
      - SUGGESTIONS_RATE_LIMIT_TIMES (default: 10 requests)
      - SUGGESTIONS_RATE_LIMIT_SECONDS (default: 60 seconds)
      - REDIS_URL (optional Redis connection for distributed multi-worker deployments)

    Limitations of in-memory mode:
      In multi-worker production environments without Redis, each worker process
      maintains its own counter. For strict cluster-wide throttling, configure REDIS_URL.
    """

    def __init__(self, times: int | None = None, seconds: int | None = None):
        self.times = times or int(os.getenv("SUGGESTIONS_RATE_LIMIT_TIMES", "10"))
        self.seconds = seconds or int(os.getenv("SUGGESTIONS_RATE_LIMIT_SECONDS", "60"))
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()
        self.redis_client = None
        self.lua_script = None

        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            sanitized_url = sanitize_redis_url(redis_url)
            try:
                import redis

                self.redis_client = redis.from_url(redis_url)
                self.lua_script = self.redis_client.register_script(LUA_SLIDING_WINDOW_SCRIPT)
                logger.info("UserRateLimiter connected to Redis: %s", sanitized_url)
            except Exception as err:
                logger.warning(
                    "UserRateLimiter failed to connect to Redis (%s), falling back to in-memory: %s",
                    sanitized_url,
                    err,
                )

    def check(self, user_id: int) -> None:
        """Enforces rate limiting for a specific user ID.

        Raises RateLimitExceededException (HTTP 429) if threshold is breached.
        """
        if not RATE_LIMIT_ENABLED:
            return

        key = f"rate_limit:user:{user_id}:suggestions"
        now = time.time()

        if self.redis_client and self.lua_script:
            try:
                unique_member = f"{now}_{time.perf_counter()}"
                res = self.lua_script(
                    keys=[key],
                    args=[now, self.seconds, self.times, unique_member],
                )
                allowed = int(res[0])
                retry_after = int(res[1])

                if not allowed:
                    raise RateLimitExceededException(retry_after=retry_after)
                return
            except RateLimitExceededException:
                raise
            except Exception as err:
                logger.warning("Redis rate limit operation failed, falling back to memory: %s", err)

        # In-memory sliding window
        monotonic_now = time.monotonic()
        with self.lock:
            cutoff = monotonic_now - self.seconds
            active_timestamps = [t for t in self.requests[key] if t > cutoff]

            if len(active_timestamps) >= self.times:
                oldest = active_timestamps[0]
                retry_after = max(1, int(self.seconds - (monotonic_now - oldest)))
                raise RateLimitExceededException(retry_after=retry_after)

            active_timestamps.append(monotonic_now)
            self.requests[key] = active_timestamps


# Default singleton instance for suggestions
suggestions_rate_limiter = UserRateLimiter()
