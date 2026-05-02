
# =============================================================================
# Security utilities (API‑key fingerprinting)
# =============================================================================
# NOTE (Purpose):
# - Provides a shared utility for generating short, non-reversible fingerprints
#   of API keys using SHA‑256, enabling safe inclusion of API‑key identifiers in
#   logs and audit trails without exposing the underlying secret.
# - Ensures consistent fingerprinting across middleware, authentication, and
#   service layers, avoiding duplicated hashing logic and preventing drift.
# - Returns `None` when no API key is provided, allowing callers to cleanly
#   omit the field from structured logs.
# - Designed for observability and auditability in internal service-to-service
#   communication where full key material must never be logged.

import hashlib


def fingerprint_api_key(api_key: str) -> str | None:
    if not api_key:
        return None
    return hashlib.sha256(api_key.encode()).hexdigest()[:12]