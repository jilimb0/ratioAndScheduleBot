"""Telegram Mini App (TMA) initData HMAC-SHA256 validator.

Mirrors the cryptographic specification from @tgwrapper/core/tma:
1. Extracts `hash` from URL-encoded query string.
2. Constructs `data_check_string` by sorting remaining key=value pairs
   alphabetically by key, joined by '\\n'.
3. Computes secret key via HMAC-SHA256("WebAppData", bot_token).
4. Computes signature via HMAC-SHA256(secret_key, data_check_string).
5. Compares signature with hex hash in constant time.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def compute_init_data_hash(data_check_string: str, bot_token: str) -> str:
    """Computes HMAC-SHA256 hash according to Telegram Bot API specification."""
    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    return hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def parse_init_data(init_data: str) -> dict:
    """Parses raw initData query string into a dictionary, unpacking JSON 'user' if present."""
    parsed = {}
    for key, value in parse_qsl(init_data, keep_blank_values=True):
        if key in ("user", "receiver", "chat"):
            try:
                parsed[key] = json.loads(value)
            except Exception:
                parsed[key] = value
        else:
            parsed[key] = value
    return parsed


def validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> bool:
    """Validates Telegram Mini App initData using HMAC-SHA256."""
    valid, _, _ = parse_and_validate_init_data(
        init_data, bot_token, max_age_seconds=max_age_seconds
    )
    return valid


def parse_and_validate_init_data(
    init_data: str, bot_token: str, max_age_seconds: int = 86400
) -> tuple[bool, dict | None, str | None]:
    """Validates and parses initData.

    Returns:
        (valid: bool, data: dict | None, error: str | None)
    """
    if not init_data or not bot_token:
        return False, None, "Missing init_data or bot_token"

    params = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = params.pop("hash", None)

    if not received_hash:
        return False, None, "Missing hash parameter"

    # Sort keys alphabetically and build data_check_string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items(), key=lambda item: item[0])
    )

    expected_hash = compute_init_data_hash(data_check_string, bot_token)

    if not hmac.compare_digest(expected_hash, received_hash):
        return False, None, "Invalid HMAC signature"

    # Validate auth_date freshness
    auth_date_str = params.get("auth_date")
    if auth_date_str and max_age_seconds > 0:
        try:
            auth_date = int(auth_date_str)
            if time.time() - auth_date > max_age_seconds:
                return False, None, "initData expired"
        except (ValueError, TypeError):
            return False, None, "Invalid auth_date"

    data = parse_init_data(init_data)
    return True, data, None
