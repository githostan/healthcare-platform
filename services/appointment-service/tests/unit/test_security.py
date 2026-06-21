"""
Unit tests for security utilities.

Purpose:
- Test timing_safe_compare and fingerprint_api_key in isolation —
  pure functions, no FastAPI, no app state.
"""

from __future__ import annotations

from app.utils.security import fingerprint_api_key, timing_safe_compare


def test_timing_safe_compare_matches():
    assert timing_safe_compare("abc", "abc") is True


def test_timing_safe_compare_differs():
    assert timing_safe_compare("abc", "xyz") is False


def test_timing_safe_compare_different_lengths():
    # hmac.compare_digest handles unequal-length inputs safely without
    # raising — important since this is the exact case a malformed or
    # truncated API key would hit in production.
    assert timing_safe_compare("short", "a-much-longer-string") is False


def test_timing_safe_compare_empty_strings():
    assert timing_safe_compare("", "") is True


def test_fingerprint_is_deterministic():
    assert fingerprint_api_key("secret") == fingerprint_api_key("secret")


def test_fingerprint_is_not_raw_secret():
    assert fingerprint_api_key("secret") != "secret"


def test_fingerprint_differs_for_different_keys():
    assert fingerprint_api_key("secret-one") != fingerprint_api_key("secret-two")


def test_fingerprint_length_is_twelve_characters():
    # fingerprint_api_key truncates to the first 12 hex characters —
    # worth pinning this explicitly since downstream log/audit consumers
    # may assume a fixed-width fingerprint format.
    assert len(fingerprint_api_key("any-key-value")) == 12
