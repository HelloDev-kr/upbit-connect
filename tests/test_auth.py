"""Tests for upbit_connect.auth module.

Tests cover JWT token generation, query hash, body hash, and base64url encoding.
"""

import base64
import hashlib
import hmac
import json
from typing import Any
from unittest.mock import patch

from upbit_connect.auth import (
    base64url_encode,
    create_body_hash,
    create_query_hash,
    generate_jwt_token,
)


class TestBase64urlEncode:
    """Tests for the base64url_encode function."""

    def test_basic_encoding(self) -> None:
        """Test basic bytes encoding."""
        data = b"hello"
        result = base64url_encode(data)
        assert isinstance(result, str)
        assert "=" not in result

    def test_padding_stripped(self) -> None:
        """Test that padding is removed."""
        # "a" encodes to "YQ==" in standard base64
        result = base64url_encode(b"a")
        assert result == "YQ"
        assert not result.endswith("=")

    def test_url_safe_characters(self) -> None:
        """Test that URL-unsafe characters are replaced."""
        # Data that produces + and / in standard base64
        data = b"\xfb\xff\xfe"
        result = base64url_encode(data)
        assert "+" not in result
        assert "/" not in result
        assert "_" in result or "-" in result

    def test_empty_bytes(self) -> None:
        """Test encoding empty bytes."""
        result = base64url_encode(b"")
        assert result == ""

    def test_json_header_encoding(self) -> None:
        """Test encoding typical JWT header."""
        header = {"alg": "HS256", "typ": "JWT"}
        header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
        result = base64url_encode(header_bytes)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_round_trip_decode(self) -> None:
        """Test that encoded data can be decoded back."""
        original = b"test data for round trip"
        encoded = base64url_encode(original)
        # Add padding back for decoding
        padded = encoded + "=" * (4 - len(encoded) % 4) if len(encoded) % 4 else encoded
        decoded = base64.urlsafe_b64decode(padded)
        assert decoded == original


class TestCreateQueryHash:
    """Tests for the create_query_hash function."""

    def test_single_param(self) -> None:
        """Test hash with single parameter."""
        params = {"market": "KRW-BTC"}
        result = create_query_hash(params)
        assert isinstance(result, str)
        assert len(result) == 128  # SHA-512 hex is 128 chars

    def test_sorted_params(self) -> None:
        """Test that parameters are sorted alphabetically."""
        params1 = {"z_param": "1", "a_param": "2"}
        params2 = {"a_param": "2", "z_param": "1"}
        # Same hash regardless of insertion order
        assert create_query_hash(params1) == create_query_hash(params2)

    def test_hash_consistency(self) -> None:
        """Test that same params produce same hash."""
        params = {"market": "KRW-BTC", "count": "10"}
        hash1 = create_query_hash(params)
        hash2 = create_query_hash(params)
        assert hash1 == hash2

    def test_different_params_different_hash(self) -> None:
        """Test that different params produce different hashes."""
        hash1 = create_query_hash({"market": "KRW-BTC"})
        hash2 = create_query_hash({"market": "KRW-ETH"})
        assert hash1 != hash2

    def test_empty_params(self) -> None:
        """Test hash with empty parameters."""
        result = create_query_hash({})
        # Empty string hash
        expected = hashlib.sha512(b"").hexdigest()
        assert result == expected

    def test_special_characters(self) -> None:
        """Test hash with special characters in values."""
        params = {"key": "value with spaces", "other": "a+b=c"}
        result = create_query_hash(params)
        assert len(result) == 128

    def test_manual_hash_verification(self) -> None:
        """Verify hash matches manual calculation."""
        params = {"count": "10", "market": "KRW-BTC"}
        result = create_query_hash(params)
        # Manual: sorted -> "count=10&market=KRW-BTC"
        expected_input = "count=10&market=KRW-BTC"
        expected_hash = hashlib.sha512(expected_input.encode("utf-8")).hexdigest()
        assert result == expected_hash


class TestCreateBodyHash:
    """Tests for the create_body_hash function."""

    def test_simple_body(self) -> None:
        """Test hash with simple body."""
        body = {"market": "KRW-BTC", "side": "bid"}
        result = create_body_hash(body)
        assert isinstance(result, str)
        assert len(result) == 128

    def test_hash_uses_compact_json(self) -> None:
        """Test that hash uses compact JSON (no spaces)."""
        body = {"a": "1", "b": "2"}
        result = create_body_hash(body)
        # Compact JSON: {"a":"1","b":"2"} (keys sorted)
        compact_json = json.dumps(body, separators=(",", ":"), sort_keys=True)
        expected = hashlib.sha512(compact_json.encode("utf-8")).hexdigest()
        assert result == expected

    def test_keys_sorted(self) -> None:
        """Test that body keys are sorted before hashing."""
        body1 = {"z": "1", "a": "2"}
        body2 = {"a": "2", "z": "1"}
        assert create_body_hash(body1) == create_body_hash(body2)

    def test_nested_body(self) -> None:
        """Test hash with nested structure."""
        body: dict[str, Any] = {"order": {"market": "KRW-BTC", "volume": "0.01"}}
        result = create_body_hash(body)
        assert len(result) == 128

    def test_empty_body(self) -> None:
        """Test hash with empty body."""
        result = create_body_hash({})
        expected = hashlib.sha512(b"{}").hexdigest()
        assert result == expected


class TestGenerateJwtToken:
    """Tests for the generate_jwt_token function."""

    def test_token_structure(self) -> None:
        """Test that token has three parts separated by dots."""
        token = generate_jwt_token("access", "secret")
        parts = token.split(".")
        assert len(parts) == 3

    def test_header_content(self) -> None:
        """Test that header contains correct algorithm and type."""
        token = generate_jwt_token("access", "secret")
        header_b64 = token.split(".")[0]
        # Add padding for decode
        padded = header_b64 + "=" * (4 - len(header_b64) % 4) if len(header_b64) % 4 else header_b64
        header_json = base64.urlsafe_b64decode(padded).decode("utf-8")
        header = json.loads(header_json)
        assert header["alg"] == "HS256"
        assert header["typ"] == "JWT"

    def test_payload_required_fields(self) -> None:
        """Test that payload contains required fields."""
        token = generate_jwt_token("my-access-key", "my-secret-key")
        payload_b64 = token.split(".")[1]
        padded = (
            payload_b64 + "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else payload_b64
        )
        payload_json = base64.urlsafe_b64decode(padded).decode("utf-8")
        payload = json.loads(payload_json)
        assert payload["access_key"] == "my-access-key"
        assert "nonce" in payload
        assert "timestamp" in payload
        assert isinstance(payload["timestamp"], int)

    def test_timestamp_in_milliseconds(self) -> None:
        """Test that timestamp is in milliseconds."""
        with patch("upbit_connect.auth.time.time", return_value=1704067200.0):
            token = generate_jwt_token("access", "secret")
        payload_b64 = token.split(".")[1]
        padded = (
            payload_b64 + "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else payload_b64
        )
        payload = json.loads(base64.urlsafe_b64decode(padded))
        assert payload["timestamp"] == 1704067200000

    def test_nonce_is_uuid4_format(self) -> None:
        """Test that nonce is a valid UUID4 string."""
        token = generate_jwt_token("access", "secret")
        payload_b64 = token.split(".")[1]
        padded = (
            payload_b64 + "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else payload_b64
        )
        payload = json.loads(base64.urlsafe_b64decode(padded))
        nonce = payload["nonce"]
        # UUID4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        assert len(nonce) == 36
        assert nonce.count("-") == 4

    def test_with_query_params(self) -> None:
        """Test token with query parameters includes hash."""
        token = generate_jwt_token("access", "secret", query_params={"market": "KRW-BTC"})
        payload_b64 = token.split(".")[1]
        padded = (
            payload_b64 + "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else payload_b64
        )
        payload = json.loads(base64.urlsafe_b64decode(padded))
        assert "query_hash" in payload
        assert payload["query_hash_alg"] == "SHA512"
        assert len(payload["query_hash"]) == 128

    def test_with_body(self) -> None:
        """Test token with body includes hash."""
        token = generate_jwt_token("access", "secret", body={"market": "KRW-BTC", "side": "bid"})
        payload_b64 = token.split(".")[1]
        padded = (
            payload_b64 + "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else payload_b64
        )
        payload = json.loads(base64.urlsafe_b64decode(padded))
        assert "query_hash" in payload
        assert payload["query_hash_alg"] == "SHA512"

    def test_body_overwrites_query_hash(self) -> None:
        """Test that body hash overwrites query hash when both provided."""
        # Per Upbit API: POST requests use body hash, not query params
        query_hash = create_query_hash({"market": "KRW-BTC"})
        body_hash = create_body_hash({"side": "bid"})
        token = generate_jwt_token(
            "access",
            "secret",
            query_params={"market": "KRW-BTC"},
            body={"side": "bid"},
        )
        payload_b64 = token.split(".")[1]
        padded = (
            payload_b64 + "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else payload_b64
        )
        payload = json.loads(base64.urlsafe_b64decode(padded))
        # Body hash should be used, not query hash
        assert payload["query_hash"] == body_hash
        assert payload["query_hash"] != query_hash

    def test_without_params_no_hash_fields(self) -> None:
        """Test that token without params has no query_hash fields."""
        token = generate_jwt_token("access", "secret")
        payload_b64 = token.split(".")[1]
        padded = (
            payload_b64 + "=" * (4 - len(payload_b64) % 4) if len(payload_b64) % 4 else payload_b64
        )
        payload = json.loads(base64.urlsafe_b64decode(padded))
        assert "query_hash" not in payload
        assert "query_hash_alg" not in payload

    def test_signature_validation(self) -> None:
        """Test that signature is valid HMAC-SHA256."""
        access_key = "test-access"
        secret_key = "test-secret"
        token = generate_jwt_token(access_key, secret_key)
        parts = token.split(".")
        message = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(
            secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_sig_b64 = base64url_encode(expected_sig)
        assert parts[2] == expected_sig_b64

    def test_different_secrets_different_signatures(self) -> None:
        """Test that different secrets produce different signatures."""
        # Mock time and uuid to ensure only secret differs
        with patch("upbit_connect.auth.time.time", return_value=1000000.0):
            with patch("upbit_connect.auth.uuid.uuid4", return_value="fixed-uuid"):
                token1 = generate_jwt_token("access", "secret1")
                token2 = generate_jwt_token("access", "secret2")
        sig1 = token1.split(".")[2]
        sig2 = token2.split(".")[2]
        assert sig1 != sig2

    def test_unique_nonce_per_call(self) -> None:
        """Test that each call generates unique nonce."""
        token1 = generate_jwt_token("access", "secret")
        token2 = generate_jwt_token("access", "secret")
        payload1_b64 = token1.split(".")[1]
        payload2_b64 = token2.split(".")[1]
        padded1 = (
            payload1_b64 + "=" * (4 - len(payload1_b64) % 4)
            if len(payload1_b64) % 4
            else payload1_b64
        )
        padded2 = (
            payload2_b64 + "=" * (4 - len(payload2_b64) % 4)
            if len(payload2_b64) % 4
            else payload2_b64
        )
        payload1 = json.loads(base64.urlsafe_b64decode(padded1))
        payload2 = json.loads(base64.urlsafe_b64decode(padded2))
        assert payload1["nonce"] != payload2["nonce"]


class TestQueryHashSorting:
    """Tests specifically for query hash parameter sorting."""

    def test_alphabetical_sorting(self) -> None:
        """Test that params are sorted alphabetically."""
        # Check multiple orderings produce same hash
        orderings = [
            {"c": "3", "a": "1", "b": "2"},
            {"a": "1", "b": "2", "c": "3"},
            {"b": "2", "c": "3", "a": "1"},
        ]
        hashes = [create_query_hash(p) for p in orderings]
        assert len(set(hashes)) == 1

    def test_case_sensitive_sorting(self) -> None:
        """Test that sorting is case-sensitive."""
        params1 = {"A": "1", "a": "2"}
        params2 = {"a": "2", "A": "1"}
        # ASCII: 'A' (65) < 'a' (97), so A comes first
        assert create_query_hash(params1) == create_query_hash(params2)

    def test_numeric_string_values(self) -> None:
        """Test with numeric string values."""
        params = {"count": "100", "page": "1"}
        result = create_query_hash(params)
        # count comes before page alphabetically
        expected = hashlib.sha512(b"count=100&page=1").hexdigest()
        assert result == expected
