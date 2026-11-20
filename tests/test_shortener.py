import unittest

from src.shortener import URLShortener


class URLShortenerTests(unittest.TestCase):
    def test_shortens_and_expands_http_and_https_urls(self):
        shortener = URLShortener(capacity=3)
        urls = ("http://example.com/a", "https://example.com/b")
        for url in urls:
            with self.subTest(url=url):
                code = shortener.shorten(url)
                self.assertEqual(shortener.expand(code), url)

    def test_repeated_url_returns_the_original_code(self):
        shortener = URLShortener(capacity=2)
        url = "https://example.com/"
        self.assertEqual(shortener.shorten(url), shortener.shorten(url))

    def test_codes_are_base62_ids_not_table_hashes(self):
        shortener = URLShortener(capacity=1)
        first = shortener.shorten("https://one.example/")
        second = shortener.shorten("https://two.example/")
        self.assertEqual((first, second), ("0", "1"))

    def test_missing_code_returns_none(self):
        shortener = URLShortener(capacity=2)
        self.assertIsNone(shortener.expand("0"))

    def test_invalid_urls_are_rejected(self):
        shortener = URLShortener(capacity=2)
        for url in ("", "ftp://example.com", "https:///missing-host", "/relative/path"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shortener.shorten(url)

    def test_invalid_base62_code_is_rejected(self):
        shortener = URLShortener(capacity=2)
        with self.assertRaises(ValueError):
            shortener.expand("!")


if __name__ == "__main__":
    unittest.main()
