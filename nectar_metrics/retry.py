"""Retry helpers for transient OpenStack API failures.

The collectors talk to a number of OpenStack services (nova, keystone,
the allocation API) over HTTP. Under load these occasionally return a
transient gateway error (HTTP 502/503/504), a rate limit (429) or drop
the connection. A single such blip should not abort a whole collection
run, so wrap the affected calls with :func:`retry_on_transient`.
"""

import functools
import logging
import time

from keystoneauth1 import exceptions as ksa_exceptions


LOG = logging.getLogger(__name__)

# HTTP status codes that indicate a transient server-side or gateway
# problem worth retrying. 429 is included so we back off when the API
# rate limits us rather than giving up.
RETRIABLE_STATUS_CODES = frozenset([429, 500, 502, 503, 504])

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_BACKOFF = 2.0


def _status_code(exc):
    """Return the HTTP status code carried by an exception, if any.

    Different client libraries expose it under different attribute
    names: novaclient uses ``code`` while keystoneauth1 uses
    ``http_status``.
    """
    for attr in ('http_status', 'code', 'status_code'):
        code = getattr(exc, attr, None)
        if isinstance(code, int):
            return code
    return None


def _is_transient(exc):
    """Return True if the exception looks like a transient failure."""
    if isinstance(exc, ksa_exceptions.RetriableConnectionFailure):
        return True
    return _status_code(exc) in RETRIABLE_STATUS_CODES


def retry_on_transient(
    max_attempts=DEFAULT_MAX_ATTEMPTS,
    backoff=DEFAULT_BACKOFF,
):
    """Retry the wrapped call on transient OpenStack API failures.

    Retries up to ``max_attempts`` times using exponential backoff
    (``backoff`` seconds, doubled each attempt). Non-transient errors,
    and the final attempt, are re-raised unchanged.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    if attempt >= max_attempts or not _is_transient(exc):
                        raise
                    delay = backoff * 2 ** (attempt - 1)
                    LOG.warning(
                        "%s failed (%s), attempt %d/%d, retrying in %.0fs",
                        getattr(func, '__name__', func),
                        exc,
                        attempt,
                        max_attempts,
                        delay,
                    )
                    time.sleep(delay)

        return wrapper

    return decorator
