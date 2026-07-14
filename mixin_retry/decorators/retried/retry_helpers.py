"""Helper functions for retry decoration."""

from __future__ import annotations

import inspect
from typing import Any


def should_skip_member(name: str, value: object) -> bool:
    """Check if class member should be skipped during decoration.

    Args:
        name: Member name.
        value: Member value.

    Returns:
        True if member should be skipped.
    """
    if name.startswith("_"):
        return True

    if isinstance(value, property):
        return True

    if inspect.isclass(value):
        return True

    return False


def is_standalone_callable(target: Any) -> bool:
    """Check if target appears to be a standalone function vs method.

    Args:
        target: The target to check.

    Returns:
        True if the callable appears to be a standalone function.
    """
    if not callable(target):
        return False

    try:
        sig = inspect.signature(target)
        params = list(sig.parameters.keys())

        if not params:
            return True

        first_param = params[0]
        if first_param in ("self", "cls"):
            return False

        return True
    except (ValueError, TypeError):
        return True
