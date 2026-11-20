"""In-memory URL shortener backed by the custom hash table."""

from urllib.parse import urlsplit

from src.base62 import decode, encode
from src.hash_table import HashTable


class URLShortener:
    def __init__(self, capacity: int = 8):
        self._url_to_code = HashTable(capacity)
        self._code_to_url = HashTable(capacity)
        self._next_id = 0

    def shorten(self, url: str) -> str:
        self._validate_url(url)
        existing_code = self._url_to_code.get(url)
        if existing_code is not None:
            return existing_code

        code = encode(self._next_id)
        self._url_to_code.put(url, code)
        self._code_to_url.put(code, url)
        self._next_id += 1
        return code

    def expand(self, code: str) -> str | None:
        decode(code)
        return self._code_to_url.get(code)

    @staticmethod
    def _validate_url(url: str) -> None:
        if not isinstance(url, str):
            raise TypeError("url must be a string")
        if not url or url != url.strip():
            raise ValueError("url must not be empty or have surrounding whitespace")

        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("url must be an absolute HTTP or HTTPS URL")
        _ = parsed.port
