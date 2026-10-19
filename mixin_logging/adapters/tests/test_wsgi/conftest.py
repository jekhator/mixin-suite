"""WSGI-specific pytest fixtures for adapter tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from mixin_logging.common.constants import tests as test_const


@pytest.fixture
def make_environ() -> Callable[[dict[str, str] | None], dict[str, Any]]:
    """Factory fixture for creating WSGI environ dicts with optional headers."""

    def factory(headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Create a minimal WSGI environ dict with optional header mappings."""
        environ: dict[str, Any] = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/test",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "80",
            "wsgi.url_scheme": "http",
        }
        if headers:
            for key, value in headers.items():
                wsgi_key = f"HTTP_{key.upper().replace('-', '_')}"
                environ[wsgi_key] = value
        return environ

    return factory


@pytest.fixture
def start_response_capture() -> tuple[
    list[tuple[str, list[tuple[str, str]]]],
    Callable[[str, list[tuple[str, str]], Any], Callable[[bytes], None]],
]:
    """Capture start_response calls and return (captured list, start_response callable) tuple."""
    captured: list[tuple[str, list[tuple[str, str]]]] = []

    def start_response(
        status: str,
        headers: list[tuple[str, str]],
        exc_info: Any = None,
    ) -> Callable[[bytes], None]:
        captured.append((status, headers))
        return lambda data: None

    return captured, start_response


@pytest.fixture
def mock_app() -> Callable[[dict[str, Any], Any], Any]:
    """Mock WSGI app that returns empty iterator."""

    def app(
        environ: dict[str, Any],
        start_response: Any,
    ) -> Any:
        return iter([])

    return app


@pytest.fixture
def mock_app_that_calls_start_response() -> Callable[[dict[str, Any], Any], Any]:
    """Mock WSGI app that calls start_response with basic response."""

    def app(
        environ: dict[str, Any],
        start_response: Any,
    ) -> Any:
        start_response(
            test_const.HTTP_STATUS_200_OK,
            [(test_const.HTTP_HEADER_CONTENT_TYPE, test_const.HTTP_MIME_TEXT_PLAIN)],
        )
        return iter([b"test"])

    return app
