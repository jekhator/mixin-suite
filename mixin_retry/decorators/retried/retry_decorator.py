"""@retried decorator factory."""

from __future__ import annotations

from mixin_retry.decorators.retried.retried_client import RetryClient

retried = RetryClient.with_params
"""Decorator factory: create @retried decorator with exponential backoff parameters.

Usage:
    @retried(max_attempts=5, retry_on=lambda e: isinstance(e, IOError))
    def might_fail():
        pass
"""
