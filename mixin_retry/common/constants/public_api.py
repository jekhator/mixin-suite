"""Public API surface for mixin_retry."""

from __future__ import annotations

import inspect

PUBLIC_API: frozenset[str] = frozenset(
    [
        "RetryClient",
        "RetryContainer",
        "retried",
    ]
)
"""Public API names exported from mixin_retry."""


class PublicAPIValidator:
    """Validates PUBLIC_API exports at module load."""

    @staticmethod
    def validate() -> None:
        """Validate that PUBLIC_API names are actually exported from root."""
        import mixin_retry

        for name in PUBLIC_API:
            if not hasattr(mixin_retry, name):  # pragma: no cover
                raise ImportError(
                    f"PUBLIC_API includes {name} but it is not exported "
                    "from mixin_retry.__init__"
                )

            exported = getattr(mixin_retry, name)
            if inspect.isclass(exported) or inspect.isfunction(exported):
                continue

            if callable(exported):
                continue

            raise TypeError(  # pragma: no cover
                f"PUBLIC_API includes {name} but it is not callable or a class"
            )


PublicAPIValidator.validate()
