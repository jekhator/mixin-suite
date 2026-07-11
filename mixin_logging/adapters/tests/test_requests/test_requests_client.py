"""Tests for CorrelationHTTPAdapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import requests as requests_lib  # type: ignore[import-untyped]

from mixin_logging import set_correlation_id
from mixin_logging.adapters.constants import requests as const
from mixin_logging.adapters.requests import requests_client
from mixin_logging.common.constants import tests as test_const


class TestCorrelationHTTPAdapterAddHeaders:
    """Tests for CorrelationHTTPAdapter.add_headers() method."""

    def test_add_headers_with_set_correlation_injects_header(
        self,
        make_prepared_request: Callable[..., Any],
    ) -> None:
        """add_headers() injects X-Correlation-ID when correlation_id is set."""
        set_correlation_id(test_const.HTTPX_CORR_ID_TEST)
        adapter = requests_client.CorrelationHTTPAdapter()
        prepared_request = make_prepared_request()
        adapter.add_headers(prepared_request)
        assert (
            prepared_request.headers[const.CORRELATION_ID_HEADER]
            == test_const.HTTPX_CORR_ID_TEST
        )

    def test_add_headers_without_context_is_noop(
        self,
        make_prepared_request: Callable[..., Any],
    ) -> None:
        """add_headers() does nothing when context is not set."""
        adapter = requests_client.CorrelationHTTPAdapter()
        prepared_request = make_prepared_request()
        adapter.add_headers(prepared_request)
        assert const.CORRELATION_ID_HEADER not in prepared_request.headers

    def test_add_headers_with_unsafe_context_is_noop(
        self,
        make_prepared_request: Callable[..., Any],
    ) -> None:
        """add_headers() does nothing when context has unsafe value."""
        unsafe_id = "bad\r\nvalue"
        set_correlation_id(unsafe_id)
        adapter = requests_client.CorrelationHTTPAdapter()
        prepared_request = make_prepared_request()
        adapter.add_headers(prepared_request)
        assert const.CORRELATION_ID_HEADER not in prepared_request.headers


class TestCorrelationHTTPAdapterRegisterOnSession:
    """Tests for CorrelationHTTPAdapter.register_on_session() class method."""

    def test_register_on_session_mounts_adapter_on_http(self) -> None:
        """register_on_session() mounts CorrelationHTTPAdapter on http:// scheme."""
        session = requests_lib.Session()
        requests_client.CorrelationHTTPAdapter.register_on_session(session)
        adapter = session.get_adapter("http://example.com")
        assert isinstance(adapter, requests_client.CorrelationHTTPAdapter)

    def test_register_on_session_mounts_adapter_on_https(self) -> None:
        """register_on_session() mounts CorrelationHTTPAdapter on https:// scheme."""
        session = requests_lib.Session()
        requests_client.CorrelationHTTPAdapter.register_on_session(session)
        adapter = session.get_adapter("https://example.com")
        assert isinstance(adapter, requests_client.CorrelationHTTPAdapter)


class TestCorrelationHTTPAdapterCorrelationSession:
    """Tests for CorrelationHTTPAdapter.correlation_session() class method."""

    def test_correlation_session_returns_session_with_adapter_mounted(self) -> None:
        """correlation_session() returns a Session with adapter mounted on http+https."""
        session = requests_client.CorrelationHTTPAdapter.correlation_session()
        assert isinstance(session, requests_lib.Session)
        http_adapter = session.get_adapter("http://example.com")
        https_adapter = session.get_adapter("https://example.com")
        assert isinstance(http_adapter, requests_client.CorrelationHTTPAdapter)
        assert isinstance(https_adapter, requests_client.CorrelationHTTPAdapter)


class TestCorrelationHTTPAdapterRealRequestsIntegration:
    """Tests for real requests.Session transport with CorrelationHTTPAdapter."""

    def test_real_session_injects_correlation_header_on_send(
        self,
        http_server_with_header_capture: tuple[str, dict[str, Any]],
    ) -> None:
        """Real requests.Session via correlation_session() injects header on actual send."""
        server_url, captured_headers = http_server_with_header_capture
        set_correlation_id(test_const.HTTPX_CORR_ID_SAFE)
        session = requests_client.CorrelationHTTPAdapter.correlation_session()
        response = session.get(f"{server_url}/test")
        assert response.status_code == 200
        assert const.CORRELATION_ID_HEADER in captured_headers
        assert (
            captured_headers[const.CORRELATION_ID_HEADER]
            == test_const.HTTPX_CORR_ID_SAFE
        )

    def test_real_session_omits_header_when_context_unset(
        self,
        http_server_with_header_capture: tuple[str, dict[str, Any]],
    ) -> None:
        """Real requests.Session omits header when correlation_id context is unset."""
        server_url, captured_headers = http_server_with_header_capture
        session = requests_client.CorrelationHTTPAdapter.correlation_session()
        response = session.get(f"{server_url}/test")
        assert response.status_code == 200
        assert const.CORRELATION_ID_HEADER not in captured_headers
