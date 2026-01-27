"""Tests for upbit_connect.exceptions module.

Tests cover all exception classes and the status-to-exception mapping function.
"""

import pytest

from upbit_connect.exceptions import (
    UpbitAPIError,
    UpbitAuthError,
    UpbitError,
    UpbitNetworkError,
    UpbitRateLimitError,
    UpbitValidationError,
    get_exception_for_status,
)


class TestUpbitErrorBase:
    """Tests for the base UpbitError class."""

    def test_instantiation(self) -> None:
        """Test that UpbitError can be instantiated with a message."""
        error = UpbitError("Test error message")
        assert error.message == "Test error message"
        assert str(error) == "Test error message"

    def test_inheritance(self) -> None:
        """Test that UpbitError inherits from Exception."""
        error = UpbitError("Base error")
        assert isinstance(error, Exception)

    def test_empty_message(self) -> None:
        """Test that empty message is allowed."""
        error = UpbitError("")
        assert error.message == ""


class TestUpbitAPIError:
    """Tests for the UpbitAPIError class."""

    def test_instantiation_full(self) -> None:
        """Test UpbitAPIError with all parameters."""
        error = UpbitAPIError(
            message="API failed",
            status_code=400,
            error_name="INVALID_PARAMETER",
            error_message="Missing required field",
        )
        assert error.message == "API failed"
        assert error.status_code == 400
        assert error.error_name == "INVALID_PARAMETER"
        assert error.error_message == "Missing required field"

    def test_instantiation_minimal(self) -> None:
        """Test UpbitAPIError with only required parameters."""
        error = UpbitAPIError(message="Bad request", status_code=400)
        assert error.message == "Bad request"
        assert error.status_code == 400
        assert error.error_name is None
        assert error.error_message is None

    def test_inheritance(self) -> None:
        """Test that UpbitAPIError inherits from UpbitError."""
        error = UpbitAPIError("test", 500)
        assert isinstance(error, UpbitError)
        assert isinstance(error, Exception)

    def test_various_status_codes(self) -> None:
        """Test with various HTTP status codes."""
        for code in [400, 401, 403, 404, 500, 502, 503]:
            error = UpbitAPIError(f"Error {code}", code)
            assert error.status_code == code


class TestUpbitAuthError:
    """Tests for the UpbitAuthError class."""

    def test_instantiation(self) -> None:
        """Test that UpbitAuthError can be instantiated."""
        error = UpbitAuthError("Invalid API key")
        assert error.message == "Invalid API key"

    def test_inheritance(self) -> None:
        """Test that UpbitAuthError inherits from UpbitError."""
        error = UpbitAuthError("Unauthorized")
        assert isinstance(error, UpbitError)
        assert isinstance(error, Exception)


class TestUpbitRateLimitError:
    """Tests for the UpbitRateLimitError class."""

    def test_instantiation_with_retry_after(self) -> None:
        """Test UpbitRateLimitError with retry_after."""
        error = UpbitRateLimitError("Too many requests", retry_after=5.0)
        assert error.message == "Too many requests"
        assert error.retry_after == 5.0

    def test_instantiation_without_retry_after(self) -> None:
        """Test UpbitRateLimitError without retry_after."""
        error = UpbitRateLimitError("Rate limit exceeded")
        assert error.message == "Rate limit exceeded"
        assert error.retry_after is None

    def test_retry_after_int(self) -> None:
        """Test retry_after can be an integer (via float)."""
        error = UpbitRateLimitError("Slow down", retry_after=10.0)
        assert error.retry_after == 10.0

    def test_retry_after_zero(self) -> None:
        """Test retry_after can be zero."""
        error = UpbitRateLimitError("Rate limit", retry_after=0.0)
        assert error.retry_after == 0.0

    def test_inheritance(self) -> None:
        """Test that UpbitRateLimitError inherits from UpbitError."""
        error = UpbitRateLimitError("429")
        assert isinstance(error, UpbitError)


class TestUpbitValidationError:
    """Tests for the UpbitValidationError class."""

    def test_instantiation(self) -> None:
        """Test that UpbitValidationError can be instantiated."""
        error = UpbitValidationError("Invalid price tick size")
        assert error.message == "Invalid price tick size"

    def test_inheritance(self) -> None:
        """Test that UpbitValidationError inherits from UpbitError."""
        error = UpbitValidationError("Validation failed")
        assert isinstance(error, UpbitError)


class TestUpbitNetworkError:
    """Tests for the UpbitNetworkError class."""

    def test_instantiation(self) -> None:
        """Test that UpbitNetworkError can be instantiated."""
        error = UpbitNetworkError("Connection refused")
        assert error.message == "Connection refused"

    def test_inheritance(self) -> None:
        """Test that UpbitNetworkError inherits from UpbitError."""
        error = UpbitNetworkError("Network error")
        assert isinstance(error, UpbitError)


class TestGetExceptionForStatus:
    """Tests for the get_exception_for_status mapping function."""

    def test_401_returns_auth_error(self) -> None:
        """Test 401 status returns UpbitAuthError."""
        exc_class = get_exception_for_status(401)
        assert exc_class is UpbitAuthError

    def test_403_returns_auth_error(self) -> None:
        """Test 403 status returns UpbitAuthError."""
        exc_class = get_exception_for_status(403)
        assert exc_class is UpbitAuthError

    def test_429_returns_rate_limit_error(self) -> None:
        """Test 429 status returns UpbitRateLimitError."""
        exc_class = get_exception_for_status(429)
        assert exc_class is UpbitRateLimitError

    def test_400_returns_api_error(self) -> None:
        """Test 400 status returns UpbitAPIError."""
        exc_class = get_exception_for_status(400)
        assert exc_class is UpbitAPIError

    def test_404_returns_api_error(self) -> None:
        """Test 404 status returns UpbitAPIError."""
        exc_class = get_exception_for_status(404)
        assert exc_class is UpbitAPIError

    def test_500_returns_api_error(self) -> None:
        """Test 500 status returns UpbitAPIError."""
        exc_class = get_exception_for_status(500)
        assert exc_class is UpbitAPIError

    def test_502_returns_api_error(self) -> None:
        """Test 502 status returns UpbitAPIError."""
        exc_class = get_exception_for_status(502)
        assert exc_class is UpbitAPIError

    def test_503_returns_api_error(self) -> None:
        """Test 503 status returns UpbitAPIError."""
        exc_class = get_exception_for_status(503)
        assert exc_class is UpbitAPIError

    def test_599_returns_api_error(self) -> None:
        """Test 599 (edge of 4xx-5xx) returns UpbitAPIError."""
        exc_class = get_exception_for_status(599)
        assert exc_class is UpbitAPIError

    def test_200_returns_base_error(self) -> None:
        """Test 200 status returns base UpbitError."""
        exc_class = get_exception_for_status(200)
        assert exc_class is UpbitError

    def test_301_returns_base_error(self) -> None:
        """Test 301 status returns base UpbitError."""
        exc_class = get_exception_for_status(301)
        assert exc_class is UpbitError

    def test_600_returns_base_error(self) -> None:
        """Test 600 (outside 4xx-5xx) returns base UpbitError."""
        exc_class = get_exception_for_status(600)
        assert exc_class is UpbitError

    def test_negative_returns_base_error(self) -> None:
        """Test negative status code returns base UpbitError."""
        exc_class = get_exception_for_status(-1)
        assert exc_class is UpbitError

    def test_mapping_returns_class_not_instance(self) -> None:
        """Test that mapping returns a class, not an instance."""
        exc_class = get_exception_for_status(400)
        assert isinstance(exc_class, type)
        assert issubclass(exc_class, UpbitError)


class TestExceptionCatching:
    """Tests for exception hierarchy and catching behavior."""

    def test_catch_api_error_as_upbit_error(self) -> None:
        """Test that UpbitAPIError can be caught as UpbitError."""
        with pytest.raises(UpbitError):
            raise UpbitAPIError("test", 400)

    def test_catch_auth_error_as_upbit_error(self) -> None:
        """Test that UpbitAuthError can be caught as UpbitError."""
        with pytest.raises(UpbitError):
            raise UpbitAuthError("test")

    def test_catch_rate_limit_error_as_upbit_error(self) -> None:
        """Test that UpbitRateLimitError can be caught as UpbitError."""
        with pytest.raises(UpbitError):
            raise UpbitRateLimitError("test")

    def test_catch_validation_error_as_upbit_error(self) -> None:
        """Test that UpbitValidationError can be caught as UpbitError."""
        with pytest.raises(UpbitError):
            raise UpbitValidationError("test")

    def test_catch_network_error_as_upbit_error(self) -> None:
        """Test that UpbitNetworkError can be caught as UpbitError."""
        with pytest.raises(UpbitError):
            raise UpbitNetworkError("test")

    def test_specific_exception_types_distinguishable(self) -> None:
        """Test that specific exception types can be distinguished."""
        try:
            raise UpbitRateLimitError("rate limit", retry_after=5.0)
        except UpbitAuthError:
            pytest.fail("Should not catch as UpbitAuthError")
        except UpbitRateLimitError as e:
            assert e.retry_after == 5.0
