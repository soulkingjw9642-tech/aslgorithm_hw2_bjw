"""A fixed-capacity hash table using separate chaining."""

from collections.abc import Iterator


class HashTable:
    def __init__(self, capacity: int = 8):
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self._capacity = capacity
        self._buckets: list[list[tuple[str, str]]] = [
            [] for _ in range(self._capacity)
        ]
        self._size = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return self._size

    @property
    def buckets(self) -> tuple[tuple[tuple[str, str], ...], ...]:
        return tuple(tuple(bucket) for bucket in self._buckets)

    def __len__(self) -> int:
        return self._size

    def hash_trace(self, key: str) -> tuple[tuple[str, int, int], ...]:
        self._validate_key(key)
        value = 0
        trace = []
        for character in key:
            code_point = ord(character)
            value = (value * 31 + code_point) % self.capacity
            trace.append((character, code_point, value))
        return tuple(trace)

    def bucket_index(self, key: str) -> int:
        trace = self.hash_trace(key)
        return trace[-1][2] if trace else 0

    def put(self, key: str, value: str) -> None:
        self._validate_key(key)
        if not isinstance(value, str):
            raise TypeError("value must be a string")

        bucket = self._buckets[self.bucket_index(key)]
        for index, (stored_key, _) in enumerate(bucket):
            if stored_key == key:
                bucket[index] = (key, value)
                return
        bucket.append((key, value))
        self._size += 1

    def get(self, key: str) -> str | None:
        self._validate_key(key)
        value, _ = self.find_with_probes(key)
        return value

    def find_with_probes(self, key: str) -> tuple[str | None, int]:
        self._validate_key(key)
        bucket = self._buckets[self.bucket_index(key)]
        probes = 0
        for stored_key, value in bucket:
            probes += 1
            if stored_key == key:
                return value, probes
        return None, probes

    def items(self) -> Iterator[tuple[str, str]]:
        for bucket in self._buckets:
            yield from bucket

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")
