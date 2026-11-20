"""Fixed-capacity hash tables using chaining or linear probing."""

from collections.abc import Iterator
from typing import Protocol


class HashTableProtocol(Protocol):
    strategy: str

    @property
    def capacity(self) -> int: ...

    @property
    def size(self) -> int: ...

    @property
    def buckets(self) -> tuple[tuple[tuple[str, str], ...], ...]: ...

    def __len__(self) -> int: ...

    def hash_trace(self, key: str) -> tuple[tuple[str, int, int], ...]: ...

    def bucket_index(self, key: str) -> int: ...

    def put(self, key: str, value: str) -> None: ...

    def get(self, key: str) -> str | None: ...

    def find_with_probes(self, key: str) -> tuple[str | None, int]: ...

    def probe_trace(self, key: str) -> tuple[int, ...]: ...

    def items(self) -> Iterator[tuple[str, str]]: ...


class _HashTableBase:
    def __init__(self, capacity: int = 8):
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self._capacity = capacity
        self._size = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return self._size

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

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")


class HashTable(_HashTableBase):
    """A fixed-capacity hash table using separate chaining."""

    strategy = "chaining"

    def __init__(self, capacity: int = 8):
        super().__init__(capacity)
        self._buckets: list[list[tuple[str, str]]] = [
            [] for _ in range(self._capacity)
        ]

    @property
    def buckets(self) -> tuple[tuple[tuple[str, str], ...], ...]:
        return tuple(tuple(bucket) for bucket in self._buckets)

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
        bucket_index = self.bucket_index(key)
        bucket = self._buckets[bucket_index]
        probes = 0
        for stored_key, value in bucket:
            probes += 1
            if stored_key == key:
                return value, probes
        return None, probes

    def probe_trace(self, key: str) -> tuple[int, ...]:
        self._validate_key(key)
        bucket_index = self.bucket_index(key)
        trace = []
        for stored_key, _ in self._buckets[bucket_index]:
            trace.append(bucket_index)
            if stored_key == key:
                break
        return tuple(trace)

    def items(self) -> Iterator[tuple[str, str]]:
        for bucket in self._buckets:
            yield from bucket


class LinearProbingHashTable(_HashTableBase):
    """A fixed-capacity hash table using linear probing."""

    strategy = "linear"

    def __init__(self, capacity: int = 8):
        super().__init__(capacity)
        self._buckets: list[tuple[str, str] | None] = [
            None for _ in range(self._capacity)
        ]

    @property
    def buckets(self) -> tuple[tuple[tuple[str, str], ...], ...]:
        return tuple(
            (entry,) if entry is not None else () for entry in self._buckets
        )

    def put(self, key: str, value: str) -> None:
        self._validate_key(key)
        if not isinstance(value, str):
            raise TypeError("value must be a string")

        home = self.bucket_index(key)
        for offset in range(self.capacity):
            index = (home + offset) % self.capacity
            entry = self._buckets[index]
            if entry is None:
                self._buckets[index] = (key, value)
                self._size += 1
                return
            if entry[0] == key:
                self._buckets[index] = (key, value)
                return
        raise OverflowError("hash table is full")

    def get(self, key: str) -> str | None:
        self._validate_key(key)
        value, _ = self.find_with_probes(key)
        return value

    def find_with_probes(self, key: str) -> tuple[str | None, int]:
        self._validate_key(key)
        home = self.bucket_index(key)
        for offset in range(self.capacity):
            entry = self._buckets[(home + offset) % self.capacity]
            if entry is None:
                return None, offset + 1
            if entry[0] == key:
                return entry[1], offset + 1
        return None, self.capacity

    def probe_trace(self, key: str) -> tuple[int, ...]:
        self._validate_key(key)
        home = self.bucket_index(key)
        trace = []
        for offset in range(self.capacity):
            index = (home + offset) % self.capacity
            trace.append(index)
            entry = self._buckets[index]
            if entry is None or entry[0] == key:
                break
        return tuple(trace)

    def items(self) -> Iterator[tuple[str, str]]:
        for entry in self._buckets:
            if entry is not None:
                yield entry
