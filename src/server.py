"""HTTP interface for the in-memory URL shortener."""

import argparse
import os
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast
from urllib.parse import parse_qsl, quote, unquote, urlsplit

from src.shortener import URLShortener

MAX_FORM_SIZE = 1_048_576


class ShortenerHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        shortener: URLShortener | None = None,
    ):
        self.shortener = shortener if shortener is not None else URLShortener()
        super().__init__(server_address, ShortenerRequestHandler)


class ShortenerRequestHandler(BaseHTTPRequestHandler):
    @property
    def shortener(self) -> URLShortener:
        return cast(ShortenerHTTPServer, self.server).shortener

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self._send_page("URL 단축기", self._form())
            return
        if path == "/table":
            self._send_page("해시 테이블", self._table_page())
            return
        if path.startswith("/") and path.count("/") == 1:
            code = unquote(path[1:])
            try:
                url = self.shortener.expand(code)
            except (TypeError, ValueError):
                self.send_error(404, "Short URL not found")
                return
            if url is None:
                self.send_error(404, "Short URL not found")
                return
            self.send_response(302)
            self.send_header("Location", url)
            self.end_headers()
            return
        self.send_error(404, "Page not found")

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/shorten":
            self.send_error(404, "Page not found")
            return

        length_header = self.headers.get("Content-Length")
        if length_header is None:
            self.send_error(411, "Content-Length is required")
            return
        try:
            length = int(length_header)
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if length < 0:
            self.send_error(400, "Invalid Content-Length")
            return
        if length > MAX_FORM_SIZE:
            self.send_error(413, "Form is too large")
            return

        try:
            body = self.rfile.read(length).decode("utf-8")
        except UnicodeDecodeError:
            self.send_error(400, "Form must be UTF-8")
            return
        form = parse_qsl(body, keep_blank_values=True)
        urls = [value for key, value in form if key == "url"]
        if not urls:
            self.send_error(400, "The url field is required")
            return

        try:
            code = self.shortener.shorten(urls[0])
        except (TypeError, ValueError) as error:
            message = f'<p class="error">{escape(str(error))}</p>{self._form()}'
            self._send_page("잘못된 URL", message, status=400)
            return

        short_url = f"{self._base_url()}/{quote(code, safe='')}"
        result = (
            '<p>짧은 링크가 준비되었습니다.</p>'
            f'<p><a id="short-url" href="{escape(short_url, quote=True)}">'
            f"{escape(short_url)}</a></p>"
            f"{self._form()}"
        )
        self._send_page("단축 결과", result)

    def _base_url(self) -> str:
        forwarded_host = self.headers.get("X-Forwarded-Host")
        host = (
            forwarded_host.split(",", 1)[0].strip()
            if forwarded_host
            else self.headers.get("Host", "")
        )
        if not host:
            host = f"localhost:{self.server.server_port}"

        hostname = urlsplit(f"//{host}").hostname
        if hostname in ("localhost", "127.0.0.1", "::1"):
            if hostname == "localhost":
                codespace_name = os.environ.get("CODESPACE_NAME")
                forwarding_domain = os.environ.get(
                    "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"
                )
                if codespace_name and forwarding_domain:
                    forwarding_domain = forwarding_domain.strip().lstrip(".")
                    if forwarding_domain and all(
                        character.isalnum() or character in "-."
                        for character in codespace_name + forwarding_domain
                    ):
                        return (
                            f"https://{codespace_name}-{self.server.server_port}."
                            f"{forwarding_domain}"
                        )
            return f"http://{host}"

        forwarded_scheme = self.headers.get("X-Forwarded-Proto", "")
        scheme = forwarded_scheme.split(",", 1)[0].strip().lower()
        if scheme not in ("http", "https"):
            scheme = "https" if forwarded_host else "http"
        return f"{scheme}://{host}"

    def _table_page(self) -> str:
        table = self.shortener.url_table
        rows = []
        base_url = self._base_url()
        for bucket_index, bucket in enumerate(table.buckets):
            nodes = []
            for url, code in bucket:
                short_url = f"{base_url}/{quote(code, safe='')}"
                trace_items = []
                previous = 0
                for character, code_point, remainder in table.hash_trace(url):
                    trace_items.append(
                        "<li>"
                        f"{escape(repr(character))}: ({previous} * 31 + "
                        f"{code_point}) % {table.capacity} = {remainder}"
                        "</li>"
                    )
                    previous = remainder
                trace = (
                    "<details><summary>Horner 해시 계산 과정</summary><ol>"
                    f"{''.join(trace_items)}"
                    "</ol></details>"
                )
                nodes.append(
                    '<section class="node">'
                    f"<p><strong>URL 키:</strong> {escape(url)}</p>"
                    f"<p><strong>짧은 코드:</strong> {escape(code)}</p>"
                    f'<p><strong>짧은 링크:</strong> <a href="'
                    f'{escape(short_url, quote=True)}">{escape(short_url)}</a></p>'
                    f"{trace}</section>"
                )
            if not nodes:
                chain = '<span class="empty">비어 있음</span>'
            else:
                chain = '<span class="chain">' + " → ".join(nodes) + "</span>"
            rows.append(
                f"<tr><th scope=\"row\">Bucket {bucket_index}</th>"
                f"<td>{chain}</td></tr>"
            )
        return (
            "<p>버킷의 연결 리스트 노드와 각 키의 Horner 계산 과정입니다.</p>"
            "<table><thead><tr><th>칸</th><th>연결 리스트</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    @staticmethod
    def _form() -> str:
        return (
            '<form action="/shorten" method="post">'
            '<label for="url">줄일 URL</label>'
            '<input id="url" name="url" type="url" required '
            'placeholder="https://example.com/long/path">'
            '<button type="submit">줄이기</button>'
            "</form>"
        )

    def _send_page(self, title: str, content: str, status: int = 200) -> None:
        page = (
            "<!doctype html><html lang=\"ko\"><head>"
            '<meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width, initial-scale=1">'
            f"<title>{escape(title)}</title>"
            "<style>body{font-family:sans-serif;max-width:70rem;margin:2rem auto;"
            "padding:0 1rem}input{width:min(36rem,90%);padding:.6rem}"
            "button{padding:.6rem;margin:.5rem}table{border-collapse:collapse;width:100%}"
            "th,td{border:1px solid #bbb;padding:.6rem;text-align:left;vertical-align:top}"
            ".chain{display:flex;align-items:flex-start;gap:.75rem;flex-wrap:wrap}"
            ".node{border:1px solid #888;border-radius:.4rem;padding:.5rem;max-width:32rem}"
            ".node p{overflow-wrap:anywhere}.error{color:#b00020}.empty{color:#666}"
            "</style></head><body>"
            f"<h1>{escape(title)}</h1>{content}"
            '<p><a href="/">처음으로</a> · <a href="/table">해시 테이블 보기</a></p>'
            "</body></html>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener web server")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")

    server = ShortenerHTTPServer(("", args.port))
    print(f"Serving URL shortener on http://0.0.0.0:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
