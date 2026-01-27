"""Rate limiting for Upbit API requests.

Implements intelligent rate limiting using a leaky bucket algorithm with
support for Upbit's custom Remaining-Req header format.
"""

import asyncio
import time
from collections import deque
from typing import Any

from upbit_connect.exceptions import UpbitRateLimitError


def parse_remaining_req(header_value: str) -> dict[str, Any]:
    """Parse Upbit's Remaining-Req header format.

    The header format is: "group=market; min=598; sec=9"

    Args:
        header_value: Raw Remaining-Req header value

    Returns:
        Dictionary with keys:
            - group: Rate limit group name (e.g., "market", "order")
            - min: Remaining requests per minute
            - sec: Remaining requests per second

    Raises:
        ValueError: If header format is invalid

    Examples:
        >>> parse_remaining_req("group=market; min=598; sec=9")
        {'group': 'market', 'min': 598, 'sec': 9}
    """
    result: dict[str, Any] = {}

    if not header_value:
        raise ValueError("Empty Remaining-Req header")

    # Split by semicolon and parse key=value pairs
    parts = header_value.split(";")
    for raw_part in parts:
        part = raw_part.strip()
        if "=" not in part:
            continue

        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Convert numeric values
        if key in ("min", "sec"):
            try:
                result[key] = int(value)
            except ValueError:
                raise ValueError(f"Invalid numeric value for {key}: {value}")
        else:
            result[key] = value

    # Validate required fields
    if "group" not in result:
        raise ValueError("Missing 'group' in Remaining-Req header")
    if "sec" not in result and "min" not in result:
        raise ValueError("Missing rate limit values in Remaining-Req header")

    return result


class RateLimiter:
    """Rate limiter using leaky bucket algorithm.

    This implementation tracks request timestamps and enforces rate limits
    by waiting when the bucket would overflow. It integrates with Upbit's
    Remaining-Req header to dynamically adjust limits.

    Attributes:
        group_name: Rate limit group name (e.g., "quotation", "exchange")
        max_requests: Maximum requests allowed per second
        remaining: Remaining requests from API header (per second)
        auto_retry: Whether to auto-retry when limit reached
    """

    def __init__(
        self,
        group_name: str,
        max_requests: int = 30,
        auto_retry: bool = True,
    ) -> None:
        """Initialize rate limiter.

        Args:
            group_name: Rate limit group name
            max_requests: Maximum requests per second (default: 30)
            auto_retry: Enable exponential backoff retry (default: True)
        """
        self.group_name = group_name
        self.max_requests = max_requests
        self.remaining: int | None = None
        self.auto_retry = auto_retry

        # Leaky bucket: deque of request timestamps
        self._bucket: deque[float] = deque()

        # Exponential backoff state
        self._retry_count = 0
        self._max_retries = 5
        self._base_delay = 1.0
        self._max_delay = 60.0

    async def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded.

        Uses leaky bucket algorithm:
        1. Remove timestamps older than 1 second (leak)
        2. If bucket full, wait until oldest request expires
        3. Add current timestamp to bucket

        Raises:
            UpbitRateLimitError: If rate limit exceeded and auto_retry is False
        """
        current_time = time.time()

        # Leak: remove requests older than 1 second
        while self._bucket and current_time - self._bucket[0] >= 1.0:
            self._bucket.popleft()

        # Determine current limit (use API-provided remaining if available)
        effective_limit = self.max_requests
        if self.remaining is not None and self.remaining < effective_limit:
            effective_limit = self.remaining

        # Check if bucket is full
        if len(self._bucket) >= effective_limit:
            if not self.auto_retry:
                raise UpbitRateLimitError(
                    f"Rate limit exceeded for {self.group_name}: "
                    f"{len(self._bucket)}/{effective_limit} requests/sec"
                )

            # Calculate wait time with exponential backoff
            if self._bucket:
                # Wait until oldest request expires
                oldest_request = self._bucket[0]
                base_wait = 1.0 - (current_time - oldest_request)
                base_wait = max(0.0, base_wait)
            else:
                base_wait = 0.1

            # Apply exponential backoff
            backoff_multiplier = 2**self._retry_count
            wait_time = min(
                base_wait * backoff_multiplier + self._base_delay * backoff_multiplier,
                self._max_delay,
            )

            self._retry_count = min(self._retry_count + 1, self._max_retries)

            await asyncio.sleep(wait_time)

            # Re-check after waiting (recursive call)
            await self.wait_if_needed()
            return

        # Successfully acquired slot - reset retry count
        self._retry_count = 0
        self._bucket.append(current_time)

    def update_from_headers(self, headers: dict[str, str]) -> None:
        """Update limiter state from Remaining-Req header.

        Parses Upbit's custom header format and updates the remaining
        request count. This allows the limiter to adapt to server-side
        rate limit information.

        Args:
            headers: HTTP response headers dictionary

        Examples:
            >>> limiter = RateLimiter("market")
            >>> limiter.update_from_headers({"Remaining-Req": "group=market; min=598; sec=9"})
            >>> limiter.remaining
            9
        """
        remaining_req = headers.get("Remaining-Req") or headers.get("remaining-req")

        if not remaining_req:
            return

        try:
            parsed = parse_remaining_req(remaining_req)

            # Validate group matches
            if parsed.get("group") != self.group_name:
                return

            if "sec" in parsed:
                self.remaining = parsed["sec"]

        except ValueError:
            # Ignore malformed headers
            pass

    def reset(self) -> None:
        """Reset rate limiter state.

        Clears the bucket and retry counter. Useful for testing or
        after extended idle periods.
        """
        self._bucket.clear()
        self._retry_count = 0
        self.remaining = None
