"""Tests for CorrelationIdPoolManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import urllib3

from mixin_logging import set_correlation_id
from mixin_logging.adapters.constants import urllib3 as const
from mixin_logging.adapters.urllib3 import urllib3_client
from mixin_logging.common.constants import tests as test_const


class TestCorrelationIdPoolManagerUrlopen:
    """Tests for CorrelationIdPoolManager.urlopen() method."""

    def test_urlopen_with_set_correlation_injects_header(self) -> None:
        """urlopen() injects X-Correlation-ID header when correlation_id is set."""
        set_correlation_id(test_const.HTTPX_CORR_ID_TEST)
        manager = urllib3_client.CorrelationIdPoolManager()

        captured_kwargs: dict[str, Any] = {}

        def capture_urlopen(
            self_: Any,
            method: str,
            url: str,
            **kwargs: Any,
        ) -> urllib3.BaseHTTPResponse:
            captured_kwargs.update(kwargs)
            mock_response = Mock(spec=urllib3.BaseHTTPResponse)
            return mock_response

        with patch.object(
            urllib3.PoolManager,
            "urlopen",
            capture_urlopen,
        ):
            manager.urlopen("GET", "https://example.com/test")

        assert "headers" in captured_kwargs
        assert (
            captured_kwargs["headers"][const.CORRELATION_ID_HEADER]
            == test_const.HTTPX_CORR_ID_TEST
        )

    def test_urlopen_without_context_omits_header(self) -> None:
        """urlopen() omits correlation header when context is not set."""
        manager = urllib3_client.CorrelationIdPoolManager()

        captured_kwargs: dict[str, Any] = {}

        def capture_urlopen(
            self_: Any,
            method: str,
            url: str,
            **kwargs: Any,
        ) -> urllib3.BaseHTTPResponse:
            captured_kwargs.update(kwargs)
            mock_response = Mock(spec=urllib3.BaseHTTPResponse)
            return mock_response

        with patch.object(
            urllib3.PoolManager,
            "urlopen",
            capture_urlopen,
        ):
            manager.urlopen("GET", "https://example.com/test")

        if "headers" in captured_kwargs:
            assert const.CORRELATION_ID_HEADER not in captured_kwargs["headers"]

    def test_urlopen_with_unsafe_context_omits_header(self) -> None:
        """urlopen() omits header when context has unsafe value."""
        unsafe_id = "bad\r\nvalue"
        set_correlation_id(unsafe_id)
        manager = urllib3_client.CorrelationIdPoolManager()

        captured_kwargs: dict[str, Any] = {}

        def capture_urlopen(
            self_: Any,
            method: str,
            url: str,
            **kwargs: Any,
        ) -> urllib3.BaseHTTPResponse:
            captured_kwargs.update(kwargs)
            mock_response = Mock(spec=urllib3.BaseHTTPResponse)
            return mock_response

        with patch.object(
            urllib3.PoolManager,
            "urlopen",
            capture_urlopen,
        ):
            manager.urlopen("GET", "https://example.com/test")

        if "headers" in captured_kwargs:
            assert const.CORRELATION_ID_HEADER not in captured_kwargs["headers"]

    def test_urlopen_preserves_existing_headers(self) -> None:
        """urlopen() adds correlation header without dropping existing headers."""
        set_correlation_id(test_const.HTTPX_CORR_ID_TEST)
        manager = urllib3_client.CorrelationIdPoolManager()

        captured_kwargs: dict[str, Any] = {}

        def capture_urlopen(
            self_: Any,
            method: str,
            url: str,
            **kwargs: Any,
        ) -> urllib3.BaseHTTPResponse:
            captured_kwargs.update(kwargs)
            mock_response = Mock(spec=urllib3.BaseHTTPResponse)
            return mock_response

        existing_headers = {"User-Agent": "test-agent"}

        with patch.object(
            urllib3.PoolManager,
            "urlopen",
            capture_urlopen,
        ):
            manager.urlopen(
                "GET",
                "https://example.com/test",
                headers=existing_headers,
            )

        assert "headers" in captured_kwargs
        assert captured_kwargs["headers"]["User-Agent"] == "test-agent"
        assert (
            captured_kwargs["headers"][const.CORRELATION_ID_HEADER]
            == test_const.HTTPX_CORR_ID_TEST
        )

    def test_urlopen_with_none_headers_initializes_dict(self) -> None:
        """urlopen() initializes headers dict when kwargs['headers'] is None."""
        set_correlation_id(test_const.HTTPX_CORR_ID_TEST)
        manager = urllib3_client.CorrelationIdPoolManager()

        captured_kwargs: dict[str, Any] = {}

        def capture_urlopen(
            self_: Any,
            method: str,
            url: str,
            **kwargs: Any,
        ) -> urllib3.BaseHTTPResponse:
            captured_kwargs.update(kwargs)
            mock_response = Mock(spec=urllib3.BaseHTTPResponse)
            return mock_response

        with patch.object(
            urllib3.PoolManager,
            "urlopen",
            capture_urlopen,
        ):
            manager.urlopen(
                "GET",
                "https://example.com/test",
                headers=None,
            )

        assert "headers" in captured_kwargs
        assert (
            captured_kwargs["headers"][const.CORRELATION_ID_HEADER]
            == test_const.HTTPX_CORR_ID_TEST
        )

    def test_urlopen_calls_super_with_method_url_kwargs(self) -> None:
        """urlopen() delegates to parent with method, url, and kwargs."""
        manager = urllib3_client.CorrelationIdPoolManager()

        called_with: dict[str, Any] = {}

        def capture_urlopen(
            self_: Any,
            method: str,
            url: str,
            **kwargs: Any,
        ) -> urllib3.BaseHTTPResponse:
            called_with["method"] = method
            called_with["url"] = url
            called_with["kwargs"] = kwargs
            mock_response = Mock(spec=urllib3.BaseHTTPResponse)
            return mock_response

        with patch.object(
            urllib3.PoolManager,
            "urlopen",
            capture_urlopen,
        ):
            manager.urlopen("POST", "https://api.example.com/v1/resource")

        assert called_with["method"] == "POST"
        assert called_with["url"] == "https://api.example.com/v1/resource"

    def test_urlopen_forwards_additional_kwargs(self) -> None:
        """urlopen() forwards additional kwargs like timeout, retries, etc."""
        manager = urllib3_client.CorrelationIdPoolManager()

        captured_kwargs: dict[str, Any] = {}

        def capture_urlopen(
            self_: Any,
            method: str,
            url: str,
            **kwargs: Any,
        ) -> urllib3.BaseHTTPResponse:
            captured_kwargs.update(kwargs)
            mock_response = Mock(spec=urllib3.BaseHTTPResponse)
            return mock_response

        with patch.object(
            urllib3.PoolManager,
            "urlopen",
            capture_urlopen,
        ):
            manager.urlopen(
                "GET",
                "https://example.com/test",
                timeout=10.0,
                retries=3,
            )

        assert captured_kwargs.get("timeout") == 10.0
        assert captured_kwargs.get("retries") == 3
