"""@logged: start/error logging envelope for LoggingMixin service methods."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, TypeVar

from mixin_logging.decorators.constants import decorators as const
from mixin_logging.decorators.logged import logged_objects as objs
from mixin_logging.decorators.logged._wrapper_factory import handle_wrap_callable
from mixin_logging.mixin.mixin import LoggingMixin

if TYPE_CHECKING:
    from collections.abc import Callable

Service = TypeVar("Service", bound=LoggingMixin)
Params = ParamSpec("Params")
Result = TypeVar("Result")


@dataclass(frozen=True, slots=True)
class LoggedClient:
    """Emit <event>.start / <event>.end / <event>.error on LoggingMixin methods."""

    container: objs.LoggedContainer
    payload_from_result: Callable[[Any], dict[str, object]] | None = None
    payload_from_exc: Callable[[BaseException], dict[str, object]] | None = None
    payload_from_request: Callable[..., dict[str, object]] | None = None
    timed: bool = False

    @classmethod
    def for_event(
        cls,
        event: str,
        payload_from_result: Callable[[Any], dict[str, object]] | None = None,
        payload_from_exc: Callable[[BaseException], dict[str, object]] | None = None,
        payload_from_request: Callable[..., dict[str, object]] | None = None,
        timed: bool = False,
    ) -> LoggedClient:
        """Create a LoggedClient from a base event name and optional callbacks."""
        return cls(
            objs.LoggedContainer(event),
            payload_from_result=payload_from_result,
            payload_from_exc=payload_from_exc,
            payload_from_request=payload_from_request,
            timed=timed,
        )

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
        class_module_name: str | None = None,
        class_name: str | None = None,
    ) -> Callable[Concatenate[Service, Params], Result]:
        """Wrap a single callable with start/error logging envelope."""
        return handle_wrap_callable(
            self.container,
            method,
            self.payload_from_result,
            self.payload_from_exc,
            self.payload_from_request,
            self.timed,
            for_static_or_class,
            class_module_name,
            class_name,
        )

    def _decorate_class(self, cls: type) -> type:
        """Fan out decorator to all public methods of a class."""
        for name, value in cls.__dict__.items():
            if self._should_skip_member(name, value):
                continue

            if hasattr(value, const.ATTRIBUTE_LOGGED_MARKER):
                continue

            if isinstance(value, classmethod):
                method_event = f"{self.container.event}{const.EVENT_SEPARATOR}{name}"
                method_client = LoggedClient.for_event(
                    method_event,
                    payload_from_result=self.payload_from_result,
                    payload_from_exc=self.payload_from_exc,
                    payload_from_request=self.payload_from_request,
                    timed=self.timed,
                )
                wrapped = method_client._wrap_callable(  # type: ignore[arg-type, type-var]
                    value.__func__,
                    for_static_or_class=True,
                    class_module_name=cls.__module__,
                    class_name=cls.__name__,
                )
                setattr(cls, name, classmethod(wrapped))
            elif isinstance(value, staticmethod):
                method_event = f"{self.container.event}{const.EVENT_SEPARATOR}{name}"
                method_client = LoggedClient.for_event(
                    method_event,
                    payload_from_result=self.payload_from_result,
                    payload_from_exc=self.payload_from_exc,
                    payload_from_request=self.payload_from_request,
                    timed=self.timed,
                )
                wrapped = method_client._wrap_callable(  # type: ignore[arg-type, type-var]
                    value.__func__,
                    for_static_or_class=True,
                    class_module_name=cls.__module__,
                    class_name=cls.__name__,
                )
                setattr(cls, name, staticmethod(wrapped))
            elif callable(value):
                method_event = f"{self.container.event}{const.EVENT_SEPARATOR}{name}"
                method_client = LoggedClient.for_event(
                    method_event,
                    payload_from_result=self.payload_from_result,
                    payload_from_exc=self.payload_from_exc,
                    payload_from_request=self.payload_from_request,
                    timed=self.timed,
                )
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
