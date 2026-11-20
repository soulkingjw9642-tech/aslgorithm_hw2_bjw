import unittest

from src.hash_table import HashTable, LinearProbingHashTable
from src.shortener import URLShortener


class URLShortenerTests(unittest.TestCase):
    table_factory = HashTable

    def make_shortener(self, capacity):
        return URLShortener(capacity=capacity, table_factory=self.table_factory)

    def test_shortens_and_expands_http_and_https_urls(self):
        shortener = self.make_shortener(capacity=3)
        urls = ("http://example.com/a", "https://example.com/b")
        for url in urls:
            with self.subTest(url=url):
                code = shortener.shorten(url)
                self.assertEqual(shortener.expand(code), url)

    def test_repeated_url_returns_the_original_code(self):
        shortener = self.make_shortener(capacity=2)
        url = "https://example.com/"
        self.assertEqual(shortener.shorten(url), shortener.shorten(url))

    def test_codes_are_base62_ids_not_table_hashes(self):
        shortener = self.make_shortener(capacity=3)
        first = shortener.shorten("https://one.example/")
        second = shortener.shorten("https://two.example/")
        self.assertEqual((first, second), ("0", "1"))

    def test_missing_code_returns_none(self):
        shortener = self.make_shortener(capacity=2)
        self.assertIsNone(shortener.expand("0"))

    def test_invalid_urls_are_rejected(self):
        shortener = self.make_shortener(capacity=2)
        for url in (
            "",
            "ftp://example.com",
            "https:///missing-host",
            "/relative/path",
            " https://example.com/",
            "https://example.com/ ",
            "https://example.com:invalid/",
            "https://example.com:65536/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shortener.shorten(url)

    def test_rejects_non_string_url(self):
        shortener = self.make_shortener(capacity=2)
        with self.assertRaises(TypeError):
            shortener.shorten(None)

    def test_invalid_base62_code_is_rejected(self):
        shortener = self.make_shortener(capacity=2)
        for code in ("", "!"):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    shortener.expand(code)

    def test_rejects_non_string_code(self):
        shortener = self.make_shortener(capacity=2)
        with self.assertRaises(TypeError):
            shortener.expand(None)


class LinearProbingURLShortenerTests(URLShortenerTests):
    table_factory = LinearProbingHashTable


if __name__ == "__main__":
    unittest.main()
