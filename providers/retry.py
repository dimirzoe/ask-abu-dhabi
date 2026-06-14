"""Shared retry helper for LLM provider HTTP calls.

Transient upstream failures — rate limits (429) and server overload
(500/502/503/504) — are retried with exponential backoff so a momentary blip
self-heals instead of surfacing as an error to the user. Permanent failures
(401/402/404/...) are returned immediately for the caller to handle.
"""

from __future__ import annotations

import time
from typing import Callable

import requests

# Status codes worth retrying — temporary by nature.
TRANSIENT_STATUS: frozenset[int] = frozenset({429, 500, 502, 503, 504})


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff: 0.5s, 1s, 2s, 4s … capped at 8s."""
    return min(0.5 * (2**attempt), 8.0)


def post_with_retries(
    do_post: Callable[[], requests.Response],
    *,
    max_retries: int,
    sleep: Callable[[float], None] = time.sleep,
) -> requests.Response:
    """Invoke ``do_post`` with retries on transient HTTP failures.

    Args:
        do_post: Zero-arg callable performing the POST and returning a Response.
            Defined as a closure in each provider so test mocks of
            ``requests.post`` are still honoured.
        max_retries: Number of additional attempts after the first (0 disables).
        sleep: Sleep function (injectable for fast tests).

    Returns:
        The final :class:`requests.Response`. Status is not raised here; the
        caller decides via ``raise_for_status``.

    Raises:
        requests.exceptions.RequestException: If the request keeps failing at the
            transport level (timeout / connection error) past the last retry.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = do_post()
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt < max_retries:
                sleep(_backoff_seconds(attempt))
                continue
            raise
        if response.status_code in TRANSIENT_STATUS and attempt < max_retries:
            sleep(_backoff_seconds(attempt))
            continue
        return response

    # Unreachable in practice, but keeps type-checkers happy.
    assert last_exc is not None
    raise last_exc
