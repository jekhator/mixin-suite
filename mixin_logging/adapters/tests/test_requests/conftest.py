"""Requests-specific pytest fixtures for adapter tests."""

from __future__ import annotations

import http.server
import socketserver
import threading
from collections.abc import Callable, Generator, Iterator
from typing import Any, cast

import pytest
import requests as requests_lib  # type: ignore[import-untyped]

from mixin_logging import clear_correlation_id


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def make_prepared_request() -> Callable[..., Any]:
    """Factory fixture for creating a requests.PreparedRequest with method/url defaults."""

    def factory(
        method: str = "GET",
        url: str = "https://example.com/test",
    ) -> requests_lib.PreparedRequest:
        """Create a minimal requests.PreparedRequest for testing."""
        request = requests_lib.Request(method=method, url=url)
        return request.prepare()

    return factory


@pytest.fixture
def http_server_with_header_capture() -> Generator[
    tuple[str, dict[str, Any]], None, None
]:
    """Stand up local HTTP server that captures request headers."""
    captured_headers: dict[str, Any] = {}

    class CaptureHandler(http.server.BaseHTTPRequestHandler):
        """HTTP request handler that captures inbound request headers."""

        def do_GET(self) -> None:
            captured_headers.clear()
            captured_headers.update(dict(self.headers))
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = socketserver.TCPServer(("127.0.0.1", 0), CaptureHandler)
    server_address = server.server_address
    host: str = cast(str, server_address[0])
    port: int = cast(int, server_address[1])
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    yield f"http://{host}:{port}", captured_headers
    server.shutdown()
