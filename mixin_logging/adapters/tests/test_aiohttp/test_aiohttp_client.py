"""Tests for CorrelationIdInjector."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest import mock

import aiohttp
import pytest

from mixin_logging import set_correlation_id
from mixin_logging.adapters.aiohttp import aiohttp_client
from mixin_logging.adapters.constants import aiohttp as const
from mixin_logging.common.constants import tests as test_const


class TestCorrelationIdInjectorTraceConfig:
    """Tests for CorrelationIdInjector.trace_config() class method."""

    def test_trace_config_returns_trace_config_instance(self) -> None:
        """trace_config() returns an aiohttp.TraceConfig instance."""
        config = aiohttp_client.CorrelationIdInjector.trace_config()
        assert isinstance(config, aiohttp.TraceConfig)

    def test_trace_config_appends_inject_hook(self) -> None:
        """trace_config() appends _inject to on_request_start hooks."""
        config = aiohttp_client.CorrelationIdInjector.trace_config()
        assert len(config.on_request_start) == 1
        assert (
            config.on_request_start[0] == aiohttp_client.CorrelationIdInjector._inject
        )


class TestCorrelationIdInjectorInject:
    """Tests for CorrelationIdInjector._inject() async method."""

    @pytest.mark.asyncio
    async def test_inject_with_set_correlation_writes_header(
        self,
        make_trace_params: Callable[..., Any],
    ) -> None:
        """_inject() writes X-Correlation-ID header when correlation_id is set."""
        set_correlation_id(test_const.HTTPX_CORR_ID_SAFE)
        params = make_trace_params()
        session = mock.MagicMock(spec=aiohttp.ClientSession)
        trace_config_ctx = mock.MagicMock()

        await aiohttp_client.CorrelationIdInjector._inject(
            session, trace_config_ctx, params
        )

        assert (
            params.headers[const.CORRELATION_ID_HEADER] == test_const.HTTPX_CORR_ID_SAFE
        )

    @pytest.mark.asyncio
    async def test_inject_without_context_is_noop(
        self,
        make_trace_params: Callable[..., Any],
    ) -> None:
        """_inject() does nothing when context is not set."""
        params = make_trace_params()
        session = mock.MagicMock(spec=aiohttp.ClientSession)
        trace_config_ctx = mock.MagicMock()

        await aiohttp_client.CorrelationIdInjector._inject(
            session, trace_config_ctx, params
        )

        assert const.CORRELATION_ID_HEADER not in params.headers

    @pytest.mark.asyncio
    async def test_inject_with_unsafe_context_is_noop(
        self,
        make_trace_params: Callable[..., Any],
    ) -> None:
        """_inject() does nothing when context has unsafe value."""
        unsafe_id = "bad\r\nvalue"
        set_correlation_id(unsafe_id)
        params = make_trace_params()
        session = mock.MagicMock(spec=aiohttp.ClientSession)
        trace_config_ctx = mock.MagicMock()

        await aiohttp_client.CorrelationIdInjector._inject(
            session, trace_config_ctx, params
        )

        assert const.CORRELATION_ID_HEADER not in params.headers
