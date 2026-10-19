# mixin-logging. Decorators (Diagrams)

> **WARNING REMOVED IN 0.5.0**: The `@logged` decorator and `LoggedClient` were removed in mixin-suite 0.5.0. Use `LoggingMixin` or the ambient `log_*` functions instead.
> This page is archived for historical reference only. Its diagrams describe code that no longer exists.
> **Location:** `docs/mixin_logging/apps/decorators/diagrams.md`
> **Status:** Archived. Diagrams last updated 2026-06-04, before the removal.
> **Sibling docs:** `docs/mixin_logging/apps/decorators/logged.md` (archived)

## Removed in 0.5.0: `@logged` Subsystem Structure

> **File path:** `mixin_logging/decorators/logged/`

```
mixin_logging/decorators/logged/logged_objects.py
================================================
  Imports: from __future__ import annotations
           from dataclasses import dataclass
           from mixin_logging.decorators.constants import decorators as const

--------------------------------------------------------------------------
[FROZEN]  LoggedContainer                         <- log-event names derived from one base event
--------------------------------------------------------------------------
  +- event : str                                  (base event name, e.g. "process")
  |
  +- [vld] __post_init__(self) -> None            <- raise ValueError if event empty
  +- [prp] start -> str                           <- f"{event}{EVENT_SUFFIX_START}" (e.g. "process.start")
  +- [prp] error -> str                           <- f"{event}{EVENT_SUFFIX_ERROR}" (e.g. "process.error")


mixin_logging/decorators/logged/logged_client.py
================================================
  Imports: from __future__ import annotations
           import functools
           from collections.abc import Callable
           from dataclasses import dataclass
           from typing import Concatenate, ParamSpec, TypeVar
           from mixin_logging.decorators.constants import decorators as const
           from mixin_logging.decorators.logged import logged_objects as objs
           from mixin_logging.mixin.mixin import LoggingMixin

  Type aliases:
    Service = TypeVar("Service", bound=LoggingMixin)
    Params  = ParamSpec("Params")
    Result  = TypeVar("Result")

--------------------------------------------------------------------------
[FROZEN]  LoggedClient                            <- @logged decorator implementation
--------------------------------------------------------------------------
  +- container : objs.LoggedContainer
  |
  +- [fct @classmethod] for_event(cls, event: str) -> LoggedClient
  |                                               <- cls(objs.LoggedContainer(event))
  |
  +- [mth] __call__(self, method) -> wrapped      <- wraps a LoggingMixin method:
                                                    1. instance.log_info(container.start) on entry
                                                    2. method(instance, *args, **kwargs)
                                                    3. on Exception: instance.log_error(container.error,
                                                         error_type=type(e).__name__,
                                                         code=getattr(e, "code", None)) + re-raise

  Module public alias:
    logged = LoggedClient.for_event   <- public decorator entry (`@logged("event.name")`)

--------------------------------------------------------------------------
Module constants, mixin_logging/decorators/constants/decorators.py
--------------------------------------------------------------------------
  EVENT_SUFFIX_START    = ".start"
  EVENT_SUFFIX_ERROR    = ".error"
  LOG_FIELD_ERROR_TYPE  = "error_type"
  LOG_FIELD_ERROR_CODE  = "code"
```

## Data Flow at Method Invocation

```
svc.process_order("ORD-123")
         |
         v
    wrapper(instance, "ORD-123")
         |
         +-> log_info("process_order.start")
         |       v
         |  [LogRecord: event="process_order.start", correlation_id=<current>]
         |
         +-> method(instance, "ORD-123")
         |       |
         |       +-> Success: return result
         |       |
         |       +-> Exception: caught by wrapper
         |               v
         |         log_error(
         |           event="process_order.error",
         |           error_type=<exception class name>,
         |           code=<exception.code if present>
         |         )
         |               v
         |         [LogRecord: event="process_order.error", 
         |                     error_type=..., code=...]
         |               v
         |         raise (unchanged)
         |
         +-> Return result
```

## Module Structure

```
mixin_logging/
+-- __init__.py               <- Curated public API (imports from defining files)
|   from .decorators.logged.logged_client import LoggedClient, logged
|   from .decorators.logged.logged_objects import LoggedContainer
+-- decorators/
|   +-- __init__.py          <- Empty (docstring only, no re-exports)
|   +-- logged/
|   |   +-- __init__.py      <- Empty (docstring only, no re-exports)
|   |   +-- logged_objects.py <- LoggedContainer (value object)
|   |   +-- logged_client.py  <- LoggedClient (decorator), logged = .for_event
|   +-- ...
+-- constants/
    +-- decorators.py        <- EVENT_SUFFIX_START, EVENT_SUFFIX_ERROR

Public Access Points (preferred):
  from mixin_logging import logged, LoggingMixin, LoggedClient, LoggedContainer
```
