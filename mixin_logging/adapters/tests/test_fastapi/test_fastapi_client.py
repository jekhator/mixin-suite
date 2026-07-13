"""Tests for FastAPI middleware and dependency."""

from __future__ import annotations

# ruff: noqa: S101
import pytest
from starlette.testclient import TestClient

from mixin_logging import clear_correlation_id, get_correlation_id


class TestCorrelationIdMiddleware:
    """Tests for CorrelationIdMiddleware dispatch behavior."""

    def test_middleware_extracts_correlation_id_from_request_header(
        self,
        test_client: TestClient,
        correlation_id_abc: str,
    ) -> None:
        """Middleware extracts correlation ID from x-correlation-id request header."""
        response = test_client.get("/test", headers={"x-correlation-id": correlation_id_abc})
        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] == correlation_id_abc

    def test_middleware_generates_correlation_id_when_header_missing(
        self,
        test_client: TestClient,
    ) -> None:
        """Middleware generates correlation ID when x-correlation-id header is missing."""
        response = test_client.get("/test")
        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] is not None
        assert len(data["correlation_id"]) == 12

    def test_middleware_injects_correlation_id_into_response_header(
        self,
        test_client: TestClient,
        correlation_id_custom: str,
    ) -> None:
        """Middleware injects correlation ID into x-correlation-id response header."""
        response = test_client.get("/test", headers={"x-correlation-id": correlation_id_custom})
        assert response.status_code == 200
        assert response.headers.get("x-correlation-id") == correlation_id_custom

    def test_middleware_injects_generated_correlation_id_into_response_header(
        self,
        test_client: TestClient,
    ) -> None:
        """Middleware injects generated correlation ID into response header."""
        response = test_client.get("/test")
        assert response.status_code == 200
        correlation_id = response.headers.get("x-correlation-id")
        assert correlation_id is not None
        assert len(correlation_id) == 12

    def test_middleware_clears_context_after_request(
        self,
        test_client: TestClient,
        correlation_id_some: str,
    ) -> None:
        """Middleware clears correlation ID from context after request handling."""
        clear_correlation_id()
        assert get_correlation_id() is None

        test_client.get("/test", headers={"x-correlation-id": correlation_id_some})

        assert get_correlation_id() is None

    def test_middleware_propagates_correlation_id_to_handler(
        self,
        test_client: TestClient,
        correlation_id_abc: str,
    ) -> None:
        """Middleware makes correlation ID available to request handler."""
        response = test_client.get(
            "/test-with-request",
            headers={"x-correlation-id": correlation_id_abc},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] == correlation_id_abc
        assert data["header_value"] == correlation_id_abc

    def test_middleware_rejects_unsafe_correlation_id(
        self,
        test_client: TestClient,
    ) -> None:
        """Middleware rejects correlation ID with unsafe characters and generates new one."""
        unsafe_id = "abc\r\ndef"
        response = test_client.get("/test", headers={"x-correlation-id": unsafe_id})
        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] != unsafe_id
        assert len(data["correlation_id"]) == 12

    def test_middleware_rejects_oversized_correlation_id(
        self,
        test_client: TestClient,
    ) -> None:
        """Middleware rejects oversized correlation ID and generates new one."""
        from mixin_logging.adapters.constants import fastapi as const

        oversized_id = "x" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        response = test_client.get("/test", headers={"x-correlation-id": oversized_id})
        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] != oversized_id
        assert len(data["correlation_id"]) == 12


class TestGetCorrelationIdDependency:
    """Tests for get_correlation_id_dependency() FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_dependency_returns_correlation_id_when_set(
        self,
        correlation_id_abc: str,
    ) -> None:
        """get_correlation_id_dependency() returns correlation ID when set in context."""
        from mixin_logging import set_correlation_id
        from mixin_logging.adapters.fastapi import get_correlation_id_dependency

        set_correlation_id(correlation_id_abc)
        result = await get_correlation_id_dependency()
        assert result == correlation_id_abc
        clear_correlation_id()

    @pytest.mark.asyncio
    async def test_dependency_raises_when_not_set(self) -> None:
        """get_correlation_id_dependency() raises ValueError when no correlation ID in context."""
        from mixin_logging.adapters.fastapi import get_correlation_id_dependency

        clear_correlation_id()
        with pytest.raises(ValueError, match="Correlation ID not set in context"):
            await get_correlation_id_dependency()
