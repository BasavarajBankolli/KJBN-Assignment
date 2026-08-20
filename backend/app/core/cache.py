"""Minimal in-process TTL cache.

Design notes:
- Thread-safe (``threading.Lock``) - safe under concurrent async requests.
- Entries expire after ``ttl_seconds`` and are evicted lazily on access.
- ``ttl_seconds == 0`` disables the cache (entries are never stored).
- The clock is injectable (``now_fn``) so expiration is deterministically
  testable without sleeping.
- Unbounded size is acceptable here: the cache holds one list of trucks
  per status filter - a tiny, bounded key space.
"""

import logging
import threading
import time
from typing import Callable, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TTLCache(Generic[T]):
    """In-process cache with time-to-live expiration for typed values."""

    def __init__(
        self,
        ttl_seconds: int,
        now_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be >= 0")
        self._ttl_seconds = ttl_seconds
        self._now_fn = now_fn
        self._store: dict[str, tuple[float, T]] = {}
        self._lock = threading.Lock()

    @property
    def ttl_seconds(self) -> int:
        """Configured TTL in seconds."""
        return self._ttl_seconds

    @property
    def enabled(self) -> bool:
        """Whether caching is active (TTL > 0)."""
        return self._ttl_seconds > 0

    def get(self, key: str) -> T | None:
        """Return the cached value for ``key``, or None if absent/expired."""
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, value = item
            if self._now_fn() >= expires_at:
                del self._store[key]
                logger.debug("Cache entry expired: %s", key)
                return None
            logger.debug("Cache hit: %s", key)
            return value

    def set(self, key: str, value: T) -> None:
        """Store ``value`` under ``key`` with a fresh TTL (no-op if disabled)."""
        if not self.enabled:
            return
        with self._lock:
            self._store[key] = (self._now_fn() + self._ttl_seconds, value)
            logger.debug("Cache set: %s", key)

    def clear(self) -> None:
        """Remove all entries."""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)