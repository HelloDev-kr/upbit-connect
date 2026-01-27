"""Authentication module for Upbit API.

This module provides JWT token generation with Upbit-specific requirements:
- HS256 algorithm using stdlib (no PyJWT dependency)
- Query String Hash (QSH) with SHA-512
- JSON body hashing for POST requests
- Nonce generation using uuid.uuid4()

All tokens include:
- access_key: API access key
- nonce: UUID4 string to prevent replay attacks
- timestamp: Unix timestamp in milliseconds
- query_hash: SHA-512 hex of sorted query string (if query params present)
- query_hash_alg: "SHA512" (if query_hash present)
"""

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any
from urllib.parse import urlencode


def base64url_encode(data: bytes) -> str:
    """Encode bytes as base64url string without padding.

    Args:
        data: Bytes to encode.

    Returns:
        Base64url-encoded string with padding removed.
    """
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def create_query_hash(params: dict[str, Any]) -> str:
    """Create SHA-512 hash of query parameters.

    Parameters are sorted alphabetically and formatted as a query string
    before hashing. This ensures consistent hash values regardless of
    parameter order.

    Args:
        params: Dictionary of query parameters.

    Returns:
        Hexadecimal SHA-512 hash of the canonicalized query string.

    Example:
        >>> create_query_hash({"market": "KRW-BTC", "count": "10"})
        'a1b2c3...'  # SHA-512 hex of "count=10&market=KRW-BTC"
    """
    # Sort parameters alphabetically and create query string
    sorted_params = dict(sorted(params.items()))
    query_string = urlencode(sorted_params)

    # Hash with SHA-512 and return hex digest
    hash_obj = hashlib.sha512()
    hash_obj.update(query_string.encode("utf-8"))
    return hash_obj.hexdigest()


def create_body_hash(body: dict[str, Any]) -> str:
    """Create SHA-512 hash of JSON request body.

    Args:
        body: Dictionary representing the JSON request body.

    Returns:
        Hexadecimal SHA-512 hash of the JSON-encoded body.

    Example:
        >>> create_body_hash({"market": "KRW-BTC", "side": "bid"})
        'd4e5f6...'  # SHA-512 hex of JSON body
    """
    # Serialize to JSON without whitespace
    json_body = json.dumps(body, separators=(",", ":"), sort_keys=True)

    # Hash with SHA-512 and return hex digest
    hash_obj = hashlib.sha512()
    hash_obj.update(json_body.encode("utf-8"))
    return hash_obj.hexdigest()


def generate_jwt_token(
    access_key: str,
    secret_key: str,
    query_params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> str:
    """Generate JWT token for Upbit API authentication.

    Creates a JWT token using HS256 algorithm with Upbit-specific payload:
    - access_key: The API access key
    - nonce: UUID4 string for replay attack prevention
    - timestamp: Current Unix timestamp in milliseconds
    - query_hash: SHA-512 hex of sorted query string (if params provided)
    - query_hash_alg: "SHA512" (if query_hash included)

    The token format is: {header}.{payload}.{signature}
    where each component is base64url-encoded.

    Args:
        access_key: Upbit API access key.
        secret_key: Upbit API secret key for HMAC signing.
        query_params: Optional dictionary of query parameters.
        body: Optional dictionary of JSON request body.

    Returns:
        JWT token string in format: {header}.{payload}.{signature}

    Example:
        >>> token = generate_jwt_token(
        ...     access_key="my-access-key",
        ...     secret_key="my-secret-key",
        ...     query_params={"market": "KRW-BTC"}
        ... )
        >>> # Returns: "eyJhbGc..."

    Note:
        - Nonce is generated using uuid.uuid4() for each request
        - Timestamp is in milliseconds to match Upbit API requirements
        - Query hash uses SHA-512 with hex encoding (not base64)
        - Query parameters are sorted alphabetically before hashing
    """
    # Create JWT header
    header = {"alg": "HS256", "typ": "JWT"}

    # Create JWT payload with required fields
    payload: dict[str, Any] = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),  # Milliseconds
    }

    # Add query hash if query parameters provided
    if query_params:
        payload["query_hash"] = create_query_hash(query_params)
        payload["query_hash_alg"] = "SHA512"

    # Add body hash if body provided
    if body:
        payload["query_hash"] = create_body_hash(body)
        payload["query_hash_alg"] = "SHA512"

    # Encode header and payload as base64url
    header_encoded = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_encoded = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    # Create signature: HMAC-SHA256 of "{header}.{payload}"
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature_encoded = base64url_encode(signature)

    # Return complete JWT token
    return f"{message}.{signature_encoded}"
