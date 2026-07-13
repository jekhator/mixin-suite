"""Fixtures for FastAPI adapter tests."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from mixin_logging import LoggingMixin
from mixin_logging.adapters.fastapi import CorrelationIdMiddleware


class MockService(LoggingMixin):
    """Mock service for testing correlation propagation."""

    def __init__(self) -> None:
        """Initialize mock service."""
        pass

    def process_request(self, request_id: int) -> dict[str, Any]:
        """Process a request and return logged data."""
        return {"request_id": request_id}


@pytest.fixture
def app_with_middleware() -> FastAPI:
    """Create a FastAPI app with CorrelationIdMiddleware installed."""
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/test")
    async def test_handler() -> dict[str, str]:
        """Test handler that returns a simple response."""
        from mixin_logging import get_correlation_id

        corr_id = get_correlation_id()
        return {"correlation_id": corr_id or "none"}

    @app.get("/test-with-request")
    async def test_handler_with_request(request: Request) -> dict[str, str]:
        """Test handler that accesses request headers."""
        from mixin_logging import get_correlation_id

        corr_id = get_correlation_id()
        header_value = request.headers.get("x-correlation-id", "none")
        return {"correlation_id": corr_id or "none", "header_value": header_value}

    return app


@pytest.fixture
def test_client(app_with_middleware: FastAPI) -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app_with_middleware)


@pytest.fixture
def correlation_id_abc() -> str:
    """Test correlation ID: abc."""
    return "abc123"


@pytest.fixture
def correlation_id_custom() -> str:
    """Test correlation ID: custom."""
    return "custom-456"


@pytest.fixture
def correlation_id_some() -> str:
    """Test correlation ID: some."""
    return "some-789"
