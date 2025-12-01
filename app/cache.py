import time
from collections import OrderedDict
from typing import Any, Dict, Tuple

class TimedLRUCache:
    def __init__(self, maxsize: int = 256, ttl_seconds: int = 300):
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self.store: "OrderedDict[str, Tuple[float, Any]]" = OrderedDict()

    def _is_expired(self, ts: float) -> bool:
        return (time.time() - ts) > self.ttl

    def get(self, key: str) -> Any:
        item = self.store.get(key)
        if not item:
            return None
        ts, value = item
        if self._is_expired(ts):
            self.store.pop(key, None)
            return None
        # mark as recently used
        self.store.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        self.store[key] = (time.time(), value)
        self.store.move_to_end(key)
        if len(self.store) > self.maxsize:
            self.store.popitem(last=False)

    def invalidate_prefix(self, prefix: str) -> None:
        keys = [k for k in self.store.keys() if k.startswith(prefix)]
        for k in keys:
            self.store.pop(k, None)

# caches per endpoint
trend_cache = TimedLRUCache(maxsize=256, ttl_seconds=300)
interaction_cache = TimedLRUCache(maxsize=256, ttl_seconds=300)

def invalidate_case(case_id: str) -> None:
    trend_cache.invalidate_prefix(f"{case_id}::")
    interaction_cache.invalidate_prefix(f"{case_id}::")

