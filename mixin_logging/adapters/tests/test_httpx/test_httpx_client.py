"""Tests for CorrelationIdInjector."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest import mock

import pytest

from mixin_logging import set_correlation_id
from mixin_logging.adapters.constants import httpx as const
from mixin_logging.adapters.httpx import httpx_client
from mixin_logging.common.constants import tests as test_const


class TestCorrelationIdInjectorEventHooks:
    """Tests for CorrelationIdInjector.event_hooks() class method."""

    def test_event_hooks_returns_request_event_list(self) -> None:
        """event_hooks() returns dict with request key containing inject_sync and inject_async."""
        hooks = httpx_client.CorrelationIdInjector.event_hooks()
        assert const.EVENT_HOOK_REQUEST in hooks
        assert len(hooks[const.EVENT_HOOK_REQUEST]) == 2
        assert (
            hooks[const.EVENT_HOOK_REQUEST][0]
            == httpx_client.CorrelationIdInjector.inject_sync
        )
        assert (
            hooks[const.EVENT_HOOK_REQUEST][1]
            == httpx_client.CorrelationIdInjector.inject_async
        )


class TestCorrelationIdInjectorSync:
    """Tests for CorrelationIdInjector.inject_sync() class method."""

    def test_inject_sync_with_set_correlation_writes_header(
        self,
        make_request: Callable[..., Any],
    ) -> None:
        """inject_sync() writes X-Correlation-ID header when correlation_id is set."""
        set_correlation_id(test_const.HTTPX_CORR_ID_TEST)
        request = make_request()
        httpx_client.CorrelationIdInjector.inject_sync(request)
        assert (
            request.headers[const.CORRELATION_ID_HEADER]
            == test_const.HTTPX_CORR_ID_TEST
        )

    def test_inject_sync_without_context_is_noop(
        self,
        make_request: Callable[..., Any],
    ) -> None:
        """inject_sync() does nothing when context is not set."""
        request = make_request()
        httpx_client.CorrelationIdInjector.inject_sync(request)
        assert const.CORRELATION_ID_HEADER not in request.headers

    def test_inject_sync_with_unsafe_context_is_noop(
        self,
        make_request: Callable[..., Any],
    ) -> None:
        """inject_sync() does nothing when context has unsafe value."""
        unsafe_id = "bad\r\nvalue"
        set_correlation_id(unsafe_id)
        request = make_request()
        httpx_client.CorrelationIdInjector.inject_sync(request)
        assert const.CORRELATION_ID_HEADER not in request.headers


class TestCorrelationIdInjectorAsync:
    """Tests for CorrelationIdInjector.inject_async() async class method."""

    @pytest.mark.asyncio
    async def test_inject_async_with_set_correlation_writes_header(
        self,
        make_request: Callable[..., Any],
    ) -> None:
        """inject_async() writes X-Correlation-ID header when correlation_id is set."""
        set_correlation_id(test_const.HTTPX_CORR_ID_ASYNC)
        request = make_request()
        await httpx_client.CorrelationIdInjector.inject_async(request)
        assert (
            request.headers[const.CORRELATION_ID_HEADER]
            == test_const.HTTPX_CORR_ID_ASYNC
        )

    @pytest.mark.asyncio
    async def test_inject_async_without_context_is_noop(
        self,
        make_request: Callable[..., Any],
    ) -> None:
        """inject_async() does nothing when context is not set."""
        request = make_request()
        await httpx_client.CorrelationIdInjector.inject_async(request)
        assert const.CORRELATION_ID_HEADER not in request.headers

    @pytest.mark.asyncio
    async def test_inject_async_delegates_to_sync_implementation(
        self,
        make_request: Callable[..., Any],
    ) -> None:
        """inject_async() delegates to inject_sync."""
        set_correlation_id(test_const.HTTPX_CORR_ID_SAFE)
        request = make_request()
        with mock.patch.object(
            httpx_client.CorrelationIdInjector,
            "inject_sync",
        ) as mock_inject:
            await httpx_client.CorrelationIdInjector.inject_async(request)
            mock_inject.assert_called_once_with(request)
