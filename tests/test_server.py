import os
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import patch

from src.hash_table import LinearProbingHashTable
from src.server import ShortenerHTTPServer
from src.shortener import URLShortener


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class ShortenerServerTests(unittest.TestCase):
    def setUp(self):
        self.server = ShortenerHTTPServer(
            ("127.0.0.1", 0), shortener=URLShortener(capacity=1)
        )
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.no_redirect_opener = urllib.request.build_opener(NoRedirectHandler)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def post_url(self, url):
        body = urllib.parse.urlencode({"url": url}).encode()
        request = urllib.request.Request(
            f"{self.base_url}/shorten",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return urllib.request.urlopen(request)

    def test_root_shows_url_form(self):
        with urllib.request.urlopen(self.base_url) as response:
            page = response.read().decode("utf-8")
        self.assertIn('action="/shorten"', page)
        self.assertIn('name="url"', page)
        self.assertIn("줄이기", page)

    def test_shortens_url_and_redirects_code_to_original(self):
        url = "https://example.com/path"
        with self.post_url(url) as response:
            page = response.read().decode("utf-8")
        self.assertIn(f"{self.base_url}/0", page)

        with self.assertRaises(urllib.error.HTTPError) as redirect:
            self.no_redirect_opener.open(f"{self.base_url}/0")
        self.assertEqual(redirect.exception.code, 302)
        self.assertEqual(redirect.exception.headers["Location"], url)

    def test_short_link_uses_forwarded_codespace_host(self):
        body = urllib.parse.urlencode({"url": "https://example.com/forwarded"}).encode()
        request = urllib.request.Request(
            f"{self.base_url}/shorten",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "localhost:8000",
                "X-Forwarded-Host": "sample-space-8000.app.github.dev",
                "X-Forwarded-Proto": "https",
            },
        )
        with urllib.request.urlopen(request) as response:
            page = response.read().decode("utf-8")
        self.assertIn("https://sample-space-8000.app.github.dev/0", page)

    def test_short_link_builds_codespace_url_when_host_is_localhost(self):
        body = urllib.parse.urlencode({"url": "https://example.com/codespace"}).encode()
        request = urllib.request.Request(
            f"{self.base_url}/shorten",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "localhost:8000",
                "X-Forwarded-Proto": "https",
            },
        )
        with patch.dict(
            os.environ,
            {
                "CODESPACE_NAME": "sample-space",
                "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "app.github.dev",
            },
        ):
            with urllib.request.urlopen(request) as response:
                page = response.read().decode("utf-8")
        expected = (
            f"https://sample-space-{self.server.server_port}.app.github.dev/0"
        )
        self.assertIn(expected, page)

    def test_localhost_without_codespace_env_uses_http(self):
        body = urllib.parse.urlencode({"url": "https://example.com/local"}).encode()
        request = urllib.request.Request(
            f"{self.base_url}/shorten",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "localhost:8000",
                "X-Forwarded-Proto": "https",
            },
        )
        with patch.dict(os.environ, {}, clear=True):
            with urllib.request.urlopen(request) as response:
                page = response.read().decode("utf-8")
        self.assertIn("http://localhost:8000/0", page)

    def test_unknown_code_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as missing:
            urllib.request.urlopen(f"{self.base_url}/not-found")
        self.assertEqual(missing.exception.code, 404)

    def test_table_shows_chained_nodes_links_and_hash_traces(self):
        self.post_url("https://example.com/first").close()
        self.post_url("https://example.com/second").close()

        with urllib.request.urlopen(f"{self.base_url}/table") as response:
            page = response.read().decode("utf-8")
        self.assertIn("Bucket 0", page)
        self.assertIn("https://example.com/first", page)
        self.assertIn("https://example.com/second", page)
        self.assertIn(f"{self.base_url}/0", page)
        self.assertIn(f"{self.base_url}/1", page)
        self.assertIn("→", page)
        self.assertIn("Horner", page)
        self.assertIn("탐색한 칸", page)
        self.assertIn("<details>", page)

    def test_table_shows_linear_probe_slots_and_calculations(self):
        shortener = URLShortener(
            capacity=4, table_factory=LinearProbingHashTable
        )
        self.server.shortener = shortener
        colliding_urls = []
        for number in range(1000):
            url = f"https://example.com/linear-{number}"
            if shortener.url_table.bucket_index(url) == 3:
                colliding_urls.append(url)
                if len(colliding_urls) == 2:
                    break

        self.assertEqual(len(colliding_urls), 2)
        for url in colliding_urls:
            shortener.shorten(url)

        with urllib.request.urlopen(f"{self.base_url}/table") as response:
            page = response.read().decode("utf-8")
        self.assertIn("선형 탐지 방식", page)
        self.assertIn("선형 탐지 슬롯", page)
        self.assertIn("탐색한 칸", page)
        self.assertIn("3 → 0", page)
        self.assertIn("(3 + 1) % 4 = 0", page)
        self.assertIn("Horner", page)

    def test_linear_table_returns_507_when_full(self):
        self.server.shortener = URLShortener(
            capacity=1, table_factory=LinearProbingHashTable
        )
        self.post_url("https://example.com/first").close()
        request = urllib.request.Request(
            f"{self.base_url}/shorten",
            data=urllib.parse.urlencode(
                {"url": "https://example.com/second"}
            ).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with self.assertRaises(urllib.error.HTTPError) as full:
            urllib.request.urlopen(request)
        self.assertEqual(full.exception.code, 507)

    def test_invalid_url_returns_400(self):
        request = urllib.request.Request(
            f"{self.base_url}/shorten",
            data=urllib.parse.urlencode({"url": "ftp://example.com"}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with self.assertRaises(urllib.error.HTTPError) as invalid:
            urllib.request.urlopen(request)
        self.assertEqual(invalid.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
