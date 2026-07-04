"""
Thread-safe LRU cache with a memory budget. Stores numpy arrays keyed by
arbitrary hashable tuples. Evicts least-recently-used entries when the total
memory footprint exceeds the configured limit.
"""

import os
import threading
from collections import OrderedDict

from .constants import DEFAULT_CACHE_MB


def _get_cache_budget_bytes():
    """Read the memory budget from environment or use default."""
    mb = int(os.environ.get("NC2_CACHE_MB", DEFAULT_CACHE_MB))
    return mb * 1024 * 1024


class SliceCache:
    """
    Memory-bounded LRU cache for numpy arrays.

    Keys are arbitrary hashable tuples (e.g., (var_name, 'spatial', time_idx, depth_idx)).
    Values are numpy arrays. Eviction is based on total nbytes of stored arrays.
    """

    def __init__(self, max_bytes=None):
        if max_bytes is None:
            max_bytes = _get_cache_budget_bytes()
        self._max_bytes = max_bytes
        self._current_bytes = 0
        self._store = OrderedDict()  # key -> (array, nbytes)
        self._lock = threading.Lock()

    @property
    def max_mb(self):
        return self._max_bytes / (1024 * 1024)

    @property
    def used_mb(self):
        return self._current_bytes / (1024 * 1024)

    @property
    def size(self):
        """Number of cached entries."""
        return len(self._store)

    def get(self, key):
        """
        Retrieve a cached array by key, or None if not present.
        Moves the entry to the end (most recently used).
        """
        with self._lock:
            if key not in self._store:
                return None
            self._store.move_to_end(key)
            return self._store[key][0]

    def put(self, key, array):
        """
        Store an array in the cache. If the key already exists, it is replaced.
        Evicts LRU entries until the budget is satisfied.
        """
        nbytes = array.nbytes

        # Don't cache arrays larger than the entire budget
        if nbytes > self._max_bytes:
            return

        with self._lock:
            # Remove existing entry if present
            if key in self._store:
                old_array, old_bytes = self._store.pop(key)
                self._current_bytes -= old_bytes

            # Evict until there is room
            while self._current_bytes + nbytes > self._max_bytes and self._store:
                _, (_, evicted_bytes) = self._store.popitem(last=False)
                self._current_bytes -= evicted_bytes

            # Insert
            self._store[key] = (array, nbytes)
            self._current_bytes += nbytes

    def invalidate(self, key):
        """Remove a specific entry from the cache."""
        with self._lock:
            if key in self._store:
                _, nbytes = self._store.pop(key)
                self._current_bytes -= nbytes

    def clear(self):
        """Drop all cached entries."""
        with self._lock:
            self._store.clear()
            self._current_bytes = 0
