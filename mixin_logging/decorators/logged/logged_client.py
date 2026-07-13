"""@logged: start/error logging envelope for LoggingMixin service methods."""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
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
        class_module_name: str | None = None,
        class_name: str | None = None,
    ) -> Callable[Concatenate[Service, Params], Result]:
        """Wrap a single callable with start/error logging envelope.

        Args:
            method: The callable to wrap.
            for_static_or_class: If True, use module-level logger fallback.
            class_module_name: Module of the decorated class (for fallback logger).
            class_name: Name of the decorated class (for fallback logger).
        """

        if for_static_or_class:
            if class_module_name and class_name:
                module_logger = logging.getLogger(class_module_name).getChild(
                    class_name,
                )

                if asyncio.iscoroutinefunction(method):

                    @functools.wraps(method)
                    async def async_static_or_class_wrapper(
                        *args: Params.args, **kwargs: Params.kwargs
                    ) -> Result:
                        module_logger.info(self.container.start)
                        try:
                            return await method(*args, **kwargs)  # type: ignore[arg-type, return-value]
                        except Exception as error:
                            module_logger.error(
                                self.container.error,
                                extra={
                                    const.LOG_FIELD_ERROR_TYPE: type(
                                        error,
                                    ).__name__,
                                    const.LOG_FIELD_ERROR_CODE: getattr(
                                        error,
                                        const.ATTRIBUTE_CODE,
                                        None,
                                    ),
                                },
                            )
                            raise

                    setattr(
                        async_static_or_class_wrapper,
                        const.ATTRIBUTE_LOGGED_MARKER,
                        True,
                    )
                    return async_static_or_class_wrapper  # type: ignore[return-value]

                @functools.wraps(method)
                def static_or_class_wrapper(
                    *args: Params.args, **kwargs: Params.kwargs
                ) -> Result:
                    module_logger.info(self.container.start)
                    try:
                        return method(*args, **kwargs)  # type: ignore[arg-type, return-value]
                    except Exception as error:
                        module_logger.error(
                            self.container.error,
                            extra={
                                const.LOG_FIELD_ERROR_TYPE: type(error).__name__,
                                const.LOG_FIELD_ERROR_CODE: getattr(
                                    error,
                                    const.ATTRIBUTE_CODE,
                                    None,
                                ),
                            },
                        )
                        raise

                setattr(static_or_class_wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
                return static_or_class_wrapper  # type: ignore[return-value]

            @functools.wraps(method)  # pragma: no cover
            def static_or_class_wrapper_no_logging(  # pragma: no cover
                *args: Params.args, **kwargs: Params.kwargs
            ) -> Result:  # pragma: no cover
                return method(*args, **kwargs)  # type: ignore[arg-type, return-value] # pragma: no cover

            setattr(  # pragma: no cover
                static_or_class_wrapper_no_logging,
                const.ATTRIBUTE_LOGGED_MARKER,
                True,
            )
            return static_or_class_wrapper_no_logging  # type: ignore[return-value] # pragma: no cover

        if asyncio.iscoroutinefunction(method):

            @functools.wraps(method)
            async def async_wrapper(
                instance: Service,
                *args: Params.args,
                **kwargs: Params.kwargs,
            ) -> Result:
                instance.log_info(self.container.start)
                try:
                    return await method(instance, *args, **kwargs)  # type: ignore[arg-type, return-value]
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

            setattr(async_wrapper, const.ATTRIBUTE_LOGGED_MARKER, True)
            return async_wrapper  # type: ignore[return-value]

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
                    class_module_name=cls.__module__,
                    class_name=cls.__name__,
                )
                setattr(cls, name, classmethod(wrapped))
            elif isinstance(value, staticmethod):
                method_event = f"{self.container.event}{const.EVENT_SEPARATOR}{name}"
                method_client = LoggedClient.for_event(method_event)
                wrapped = method_client._wrap_callable(  # type: ignore[arg-type, type-var]
                    value.__func__,
                    for_static_or_class=True,
                    class_module_name=cls.__module__,
                    class_name=cls.__name__,
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
