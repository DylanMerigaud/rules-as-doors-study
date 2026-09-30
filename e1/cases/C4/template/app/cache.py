"""A small read-through cache in front of a slow key-value store.

Entries expire after a fixed time to live. A miss reads from the store and fills the cache; a
write goes to the store first and then invalidates the cached entry, so a reader never sees a
value the store has not accepted. Eviction is least recently used once `max_entries` is reached.
"""
import time
from collections import OrderedDict


class ReadThroughCache:
    def __init__(self, store, ttl_seconds=60, max_entries=1000, clock=time.monotonic):
        self.store, self.ttl, self.max = store, ttl_seconds, max_entries
        self.clock = clock
        self.entries = OrderedDict()

    def get(self, key):
        hit = self.entries.get(key)
        if hit and self.clock() - hit[1] < self.ttl:
            self.entries.move_to_end(key)
            return hit[0]
        value = self.store.read(key)
        self.entries[key] = (value, self.clock())
        self.entries.move_to_end(key)
        while len(self.entries) > self.max:
            self.entries.popitem(last=False)
        return value

    def put(self, key, value):
        self.store.write(key, value)
        self.entries.pop(key, None)
