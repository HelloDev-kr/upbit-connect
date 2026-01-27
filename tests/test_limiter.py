"""Tests for upbit_connect.limiter module.

Tests cover rate limiter logic, header parsing, and exponential backoff.
"""

import asyncio
from collections import deque
from unittest.mock import AsyncMock, patch

import pytest

from upbit_connect.exceptions import UpbitRateLimitError
from upbit_connect.limiter import RateLimiter, parse_remaining_req


class TestParseRemainingReq:
    """Tests for the parse_remaining_req function."""

    def test_valid_format(self) -> None:
        """Test parsing valid Remaining-Req header."""
        result = parse_remaining_req("group=market; min=598; sec=9")
        assert result["group"] == "market"
        assert result["min"] == 598
        assert result["sec"] == 9

    def test_order_exchange_format(self) -> None:
        """Test parsing order group format."""
        result = parse_remaining_req("group=order; min=58; sec=4")
        assert result["group"] == "order"
        assert result["min"] == 58
        assert result["sec"] == 4

    def test_extra_whitespace(self) -> None:
        """Test parsing with extra whitespace."""
        result = parse_remaining_req("group = market ;  min = 100 ; sec = 5")
        assert result["group"] == "market"
        assert result["min"] == 100
        assert result["sec"] == 5

    def test_missing_group_raises(self) -> None:
        """Test that missing group raises ValueError."""
        with pytest.raises(ValueError, match="Missing 'group'"):
            parse_remaining_req("min=100; sec=5")

    def test_missing_rate_values_raises(self) -> None:
        """Test that missing min and sec raises ValueError."""
        with pytest.raises(ValueError, match="Missing rate limit values"):
            parse_remaining_req("group=market")

    def test_only_sec_is_valid(self) -> None:
        """Test that only sec without min is valid."""
        result = parse_remaining_req("group=market; sec=5")
        assert result["group"] == "market"
        assert result["sec"] == 5
        assert "min" not in result

    def test_only_min_is_valid(self) -> None:
        """Test that only min without sec is valid."""
        result = parse_remaining_req("group=market; min=100")
        assert result["group"] == "market"
        assert result["min"] == 100
        assert "sec" not in result

    def test_empty_string_raises(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Empty Remaining-Req header"):
            parse_remaining_req("")

    def test_invalid_numeric_value_raises(self) -> None:
        """Test that non-numeric min/sec raises ValueError."""
        with pytest.raises(ValueError, match="Invalid numeric value"):
            parse_remaining_req("group=market; min=abc; sec=5")

    def test_malformed_without_equals(self) -> None:
        """Test that malformed entries without = are skipped."""
        result = parse_remaining_req("group=market; garbage; sec=5")
        assert result["group"] == "market"
        assert result["sec"] == 5


class TestRateLimiterInit:
    """Tests for RateLimiter initialization."""

    def test_default_values(self) -> None:
        """Test default initialization values."""
        limiter = RateLimiter("test-group")
        assert limiter.group_name == "test-group"
        assert limiter.max_requests == 30
        assert limiter.auto_retry is True
        assert limiter.remaining is None

    def test_custom_max_requests(self) -> None:
        """Test initialization with custom max_requests."""
        limiter = RateLimiter("exchange", max_requests=8)
        assert limiter.max_requests == 8

    def test_auto_retry_disabled(self) -> None:
        """Test initialization with auto_retry disabled."""
        limiter = RateLimiter("test", auto_retry=False)
        assert limiter.auto_retry is False


class TestRateLimiterWaitIfNeeded:
    """Tests for RateLimiter.wait_if_needed method."""

    @pytest.mark.asyncio
    async def test_under_limit_no_wait(self) -> None:
        """Test that requests under limit don't wait."""
        limiter = RateLimiter("test", max_requests=30)
        start = asyncio.get_event_loop().time()
        await limiter.wait_if_needed()
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_bucket_tracks_requests(self) -> None:
        """Test that bucket tracks request timestamps."""
        limiter = RateLimiter("test", max_requests=30)
        await limiter.wait_if_needed()
        assert len(limiter._bucket) == 1

    @pytest.mark.asyncio
    async def test_bucket_leaks_old_requests(self) -> None:
        """Test that requests older than 1 second are removed."""
        limiter = RateLimiter("test", max_requests=30)
        old_time = 1000.0
        limiter._bucket = deque([old_time])
        with patch("upbit_connect.limiter.time.time", return_value=1001.5):
            await limiter.wait_if_needed()
        assert old_time not in limiter._bucket

    @pytest.mark.asyncio
    async def test_at_limit_auto_retry_disabled_raises(self) -> None:
        """Test that at limit with auto_retry=False raises."""
        limiter = RateLimiter("test", max_requests=2, auto_retry=False)
        current_time = 1000.0
        limiter._bucket = deque([current_time, current_time])
        with patch("upbit_connect.limiter.time.time", return_value=current_time):
            with pytest.raises(UpbitRateLimitError):
                await limiter.wait_if_needed()

    @pytest.mark.asyncio
    async def test_at_limit_auto_retry_waits(self) -> None:
        """Test that at limit with auto_retry waits."""
        limiter = RateLimiter("test", max_requests=2, auto_retry=True)
        current_time = 1000.0
        limiter._bucket = deque([current_time, current_time])
        with patch(
            "upbit_connect.limiter.time.time", side_effect=[current_time, current_time + 2.0]
        ):
            with patch("upbit_connect.limiter.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await limiter.wait_if_needed()
                mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_retry_count_resets_on_success(self) -> None:
        """Test that retry count resets after successful acquisition."""
        limiter = RateLimiter("test", max_requests=30)
        limiter._retry_count = 3
        await limiter.wait_if_needed()
        assert limiter._retry_count == 0

    @pytest.mark.asyncio
    async def test_uses_remaining_as_effective_limit(self) -> None:
        """Test that remaining from headers is used as limit."""
        limiter = RateLimiter("test", max_requests=30, auto_retry=False)
        limiter.remaining = 2
        current_time = 1000.0
        limiter._bucket = deque([current_time, current_time])
        with patch("upbit_connect.limiter.time.time", return_value=current_time):
            with pytest.raises(UpbitRateLimitError):
                await limiter.wait_if_needed()


class TestExponentialBackoff:
    """Tests for exponential backoff behavior."""

    @pytest.mark.asyncio
    async def test_backoff_increases(self) -> None:
        """Test that backoff delay increases with retries."""
        limiter = RateLimiter("test", max_requests=1, auto_retry=True)
        current_time = 1000.0
        limiter._bucket = deque([current_time])
        wait_times: list[float] = []

        async def capture_sleep(duration: float) -> None:
            wait_times.append(duration)

        call_count = 0

        def time_mock() -> float:
            nonlocal call_count
            call_count += 1
            if call_count > 3:
                return current_time + 5.0
            return current_time

        with patch("upbit_connect.limiter.time.time", side_effect=time_mock):
            with patch("upbit_connect.limiter.asyncio.sleep", side_effect=capture_sleep):
                await limiter.wait_if_needed()

        assert len(wait_times) >= 1

    @pytest.mark.asyncio
    async def test_max_delay_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        limiter = RateLimiter("test", max_requests=1, auto_retry=True)
        limiter._retry_count = 10
        assert limiter._max_delay == 60.0


class TestUpdateFromHeaders:
    """Tests for RateLimiter.update_from_headers method."""

    def test_updates_remaining(self) -> None:
        """Test that remaining is updated from header."""
        limiter = RateLimiter("market")
        limiter.update_from_headers({"Remaining-Req": "group=market; min=598; sec=9"})
        assert limiter.remaining == 9

    def test_case_insensitive_header(self) -> None:
        """Test that header lookup is case-insensitive."""
        limiter = RateLimiter("market")
        limiter.update_from_headers({"remaining-req": "group=market; sec=5"})
        assert limiter.remaining == 5

    def test_ignores_different_group(self) -> None:
        """Test that different group headers are ignored."""
        limiter = RateLimiter("market")
        limiter.update_from_headers({"Remaining-Req": "group=order; sec=5"})
        assert limiter.remaining is None

    def test_ignores_missing_header(self) -> None:
        """Test that missing header is handled gracefully."""
        limiter = RateLimiter("market")
        limiter.update_from_headers({})
        assert limiter.remaining is None

    def test_ignores_malformed_header(self) -> None:
        """Test that malformed header is ignored."""
        limiter = RateLimiter("market")
        limiter.remaining = 10
        limiter.update_from_headers({"Remaining-Req": "invalid format"})
        assert limiter.remaining == 10


class TestRateLimiterReset:
    """Tests for RateLimiter.reset method."""

    def test_clears_bucket(self) -> None:
        """Test that reset clears the bucket."""
        limiter = RateLimiter("test")
        limiter._bucket = deque([1.0, 2.0, 3.0])
        limiter.reset()
        assert len(limiter._bucket) == 0

    def test_clears_retry_count(self) -> None:
        """Test that reset clears retry count."""
        limiter = RateLimiter("test")
        limiter._retry_count = 5
        limiter.reset()
        assert limiter._retry_count == 0

    def test_clears_remaining(self) -> None:
        """Test that reset clears remaining."""
        limiter = RateLimiter("test")
        limiter.remaining = 10
        limiter.reset()
        assert limiter.remaining is None


class TestLeakyBucketAlgorithm:
    """Tests for the leaky bucket implementation details."""

    @pytest.mark.asyncio
    async def test_requests_within_window_counted(self) -> None:
        """Test that requests within 1-second window are counted."""
        limiter = RateLimiter("test", max_requests=5)
        current_time = 1000.0
        times = [current_time - 0.1, current_time - 0.5, current_time - 0.9]
        limiter._bucket = deque(times)
        with patch("upbit_connect.limiter.time.time", return_value=current_time):
            await limiter.wait_if_needed()
        assert len(limiter._bucket) == 4

    @pytest.mark.asyncio
    async def test_requests_outside_window_leaked(self) -> None:
        """Test that requests outside 1-second window are removed."""
        limiter = RateLimiter("test", max_requests=5)
        current_time = 1000.0
        old_times = [current_time - 1.5, current_time - 2.0]
        recent_times = [current_time - 0.5]
        limiter._bucket = deque(old_times + recent_times)
        with patch("upbit_connect.limiter.time.time", return_value=current_time):
            await limiter.wait_if_needed()
        assert current_time - 1.5 not in limiter._bucket
        assert current_time - 2.0 not in limiter._bucket

    @pytest.mark.asyncio
    async def test_bucket_uses_deque(self) -> None:
        """Test that bucket is a deque for O(1) operations."""
        limiter = RateLimiter("test")
        assert isinstance(limiter._bucket, deque)
