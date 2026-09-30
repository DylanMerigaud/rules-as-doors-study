import unittest

from app.cache import ReadThroughCache


class Store:
    def __init__(self):
        self.data, self.reads = {}, 0

    def read(self, k):
        self.reads += 1
        return self.data.get(k)

    def write(self, k, v):
        self.data[k] = v


class CacheTest(unittest.TestCase):
    def test_hit_does_not_read_store(self):
        s = Store()
        s.data["a"] = 1
        c = ReadThroughCache(s)
        c.get("a")
        c.get("a")
        self.assertEqual(s.reads, 1)

    def test_put_invalidates(self):
        s = Store()
        c = ReadThroughCache(s)
        c.put("a", 2)
        self.assertEqual(c.get("a"), 2)


if __name__ == "__main__":
    unittest.main()
