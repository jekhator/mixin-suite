"""Fixtures for retry decorator tests."""

import pytest


class SimpleService:
    """Simple test service for decorator testing."""

    def __init__(self) -> None:
        """Initialize the service."""
        self.call_count = 0
        self.async_call_count = 0

    def success_method(self) -> str:
        """Return success on first call."""
        return "success"

    def failing_method(self) -> str:
        """Always raise an exception."""
        raise ValueError("Test failure")

    def eventually_succeeds(self, fail_until: int = 2) -> str:
        """Fail N times, then succeed."""
        self.call_count += 1
        if self.call_count <= fail_until:
            raise IOError(f"Attempt {self.call_count}")

        return f"success after {self.call_count} attempts"

    async def async_success(self) -> str:
        """Async method that succeeds immediately."""
        return "async success"

    async def async_failing(self) -> str:
        """Async method that always fails."""
        raise ValueError("Async failure")

    async def async_eventually_succeeds(self, fail_until: int = 2) -> str:
        """Async method that fails N times, then succeeds."""
        self.async_call_count += 1
        if self.async_call_count <= fail_until:
            raise IOError(f"Async attempt {self.async_call_count}")

        return f"async success after {self.async_call_count} attempts"


@pytest.fixture
def service() -> SimpleService:
    """Create a fresh SimpleService instance for each test."""
    return SimpleService()


class CallCounter:
    """Stateful call counter for testing."""

    def __init__(self) -> None:
        """Initialize counter."""
        self.count = 0

    def reset(self) -> None:
        """Reset counter to 0."""
        self.count = 0

    def eventually_succeeds(self, fail_until: int = 2) -> str:
        """Fail N times then succeed."""
        self.count += 1
        if self.count <= fail_until:
            raise IOError(f"Attempt {self.count}")

        return f"success after {self.count} attempts"

    async def async_eventually_succeeds(
        self, fail_until: int = 2
    ) -> str:
        """Async version that fails N times then succeeds."""
        self.count += 1
        if self.count <= fail_until:
            raise IOError(f"Async attempt {self.count}")

        return f"async success after {self.count} attempts"


@pytest.fixture
def call_counter() -> CallCounter:
    """Create a fresh call counter for each test."""
    return CallCounter()
