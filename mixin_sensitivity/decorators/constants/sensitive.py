"""Sensitive decorator constants. Imported as const."""

from __future__ import annotations

from typing import Final

__all__ = [
    "DEFAULT_PLACEHOLDER",
    "ERR_SENSITIVE_TARGET_NOT_DATACLASS",
]


"""Default masking placeholder for fields without a policy."""

DEFAULT_PLACEHOLDER: Final = "***"


"""Error messages raised at the API surface (source-side; tests match against these via const.ERR_*)."""

ERR_SENSITIVE_TARGET_NOT_DATACLASS: Final = "@sensitive requires a dataclass target"
