"""@logged: start/error logging envelope for LoggingMixin service methods."""

from __future__ import annotations

import functools
import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, TypeVar

from mixin_logging.decorators.constants import decorators as const
from mixin_logging.decorators.logged import logged_objects as objs
from mixin_logging.mixin.mixin import LoggingMixin

if TYPE_CHECKING:
    from collections.abc import Callable

Service = TypeVar("Service", bound=LoggingMixin)
Params = ParamSpec("Params")
Result = TypeVar("Result")


@dataclass(frozen=True, slots=True)
class LoggedClient:
    """Emit <event>.start / <event>.error and re-raise on LoggingMixin methods."""

    container: objs.LoggedContainer

    @classmethod
    def for_event(cls, event: str) -> LoggedClient:
        """Create a LoggedClient from a base event name."""
        return cls(objs.LoggedContainer(event))

    def __call__(self, target: Any) -> Any:
        """Wrap a callable or fan out to all public methods of a class."""
        if inspect.isclass(target):
            return self._decorate_class(target)

        if callable(target):
            return self._wrap_callable(target)  # type: ignore[arg-type]

        msg = const.ERROR_MSG_TARGET_NOT_CLASS_OR_CALLABLE
        raise TypeError(msg)

    def _wrap_callable(  # type: ignore[misc]
        self,
        method: Callable[Concatenate[Service, Params], Result],
        for_static_or_class: bool = False,
    ) -> Callable[Concatenate[Service, Params], Result]:
        """Wrap a single callable with start/error logging envelope.

        Args:
            method: The callable to wrap.
            for_static_or_class: If True, skip logging (method has no LoggingMixin instance).
        """

        if for_static_or_class:

            @functools.wraps(method)
            def static_or_class_wrapper(
                *args: Params.args, **kwargs: Params.kwargs
            ) -> Result:
                return method(*args, **kwargs)  # type: ignore[arg-type, return-value]

            setattr(static_or_class_wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
            return static_or_class_wrapper  # type: ignore[return-value]

        @functools.wraps(method)
        def wrapper(
            instance: Service,
            *args: Params.args,
            **kwargs: Params.kwargs,
        ) -> Result:
            instance.log_info(self.container.start)
            try:
                return method(instance, *args, **kwargs)
            except Exception as error:
                instance.log_error(
                    self.container.error,
                    **{
                        const.LOG_FIELD_ERROR_TYPE: type(error).__name__,
                        const.LOG_FIELD_ERROR_CODE: getattr(
                            error,
                            const.ATTRIBUTE_CODE,
                            None,
                        ),
                    },
                )
                raise

        setattr(wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
        return wrapper

    def _decorate_class(self, cls: type) -> type:
        """Fan out decorator to all public methods of a class."""
        for name, value in cls.__dict__.items():
            if self._should_skip_member(name, value):
                continue

            if hasattr(value, const.ATTRIBUTE_LOGGED_MARKER):
                continue

            if isinstance(value, classmethod):
                method_event = f"{self.container.event}{const.EVENT_SEPARATOR}{name}"
                method_client = LoggedClient.for_event(method_event)
                wrapped = method_client._wrap_callable(  # type: ignore[arg-type, type-var]
                    value.__func__,
                    for_static_or_class=True,
                )
                setattr(cls, name, classmethod(wrapped))
            elif isinstance(value, staticmethod):
                method_event = f"{self.container.event}{const.EVENT_SEPARATOR}{name}"
                method_client = LoggedClient.for_event(method_event)
                wrapped = method_client._wrap_callable(  # type: ignore[arg-type, type-var]
                    value.__func__,
                    for_static_or_class=True,
                )
                setattr(cls, name, staticmethod(wrapped))
            elif callable(value):
                method_event = f"{self.container.event}{const.EVENT_SEPARATOR}{name}"
                method_client = LoggedClient.for_event(method_event)
                wrapped = method_client._wrap_callable(value)
                setattr(cls, name, wrapped)

        return cls

    @staticmethod
    def _should_skip_member(name: str, value: object) -> bool:
        """Check if a class member should be skipped from decoration."""
        if name.startswith("_"):
            return True

        if isinstance(value, property):
            return True

        if inspect.isclass(value):
            return True

        return False


logged = LoggedClient.for_event
"""Factory function to create @logged decorators from event names."""
