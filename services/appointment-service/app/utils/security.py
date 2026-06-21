

# =============================================================================
# Security utilities — crypto primitives only
# =============================================================================
# NOTE (Purpose):
# - Provides timing-safe API key comparison to prevent timing attacks.
# - Generates short, non-reversible SHA-256 fingerprints of API keys for
#   safe inclusion in logs and audit trails without exposing the secret.
# - No business logic here — pure cryptographic helpers only.

from __future__ import annotations

import hashlib
import hmac


def timing_safe_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.
    Used for API key validation.
    """
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def fingerprint_api_key(api_key: str) -> str:
    """
    Generate a short non-reversible fingerprint of an API key.
    Safe to include in logs and audit trails — does not expose the secret.

    Returns the first 12 hex characters of the SHA-256 hash.
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]