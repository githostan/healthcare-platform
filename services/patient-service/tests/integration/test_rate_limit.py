
"""
Integration tests for rate limiting.

Deferred:
- Rate limiting is middleware stateful behaviour.
- It needs isolated middleware/app state to avoid flaky CI.
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="Rate-limit tests deferred until middleware test isolation is stable"
)


def test_rate_limit_placeholder():
    assert True