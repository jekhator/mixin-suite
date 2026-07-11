# mixin_logging Flow Trace

## Architecture Overview

mixin_logging/decorators/logged/logged_client.py  (+ mixin, adapters, context)
═══════════════════════════════════════════════════════════════════════════════
Imports: functools, inspect, logging, asyncio; dataclass LoggedContainer + LoggingMixin
┌─ [DATACLASS,frozen,slots] LoggedContainer ──────────┐  event: str ; start[prop] → "{event}.start" ; error[prop] → "{event}.error"  └─...
┌─ [CLASS,slots] LoggingMixin ──────────┐  _logger[prop] → logging.Logger per-class ; log_info(event, **extra) ; log_error(event, **extra)  └─...
┌─ [DATACLASS,frozen,slots] LoggedClient ──────────┐  container: LoggedContainer ; for_event[cls_meth] ; __call__[mth] ; _decorate_class[mth] ; _wrap_callable[mth]  └─...

## FLOW TRACE

① CONSTRUCT  LoggedClient.for_event("document_service")
      └─ LoggedContainer(event="document_service")
      └─ return LoggedClient(container=...)

② DECORATE   @logged("document_service") on a class

   a. CLASS path (target is a class):
      ├─ __call__(target=DocumentService)
      ├─ inspect.isclass(target) → True ──▶ _decorate_class(target)
      │     └─ for name, value in cls.__dict__.items():
      │           ├─ _should_skip_member(name, value)
      │           │     ├─ name.startswith("_") → True ──▶ skip
      │           │     ├─ isinstance(value, property) → True ──▶ skip
      │           │     └─ inspect.isclass(value) → True ──▶ skip
      │           ├─ hasattr(value, "__logged_decorated__") ──▶ skip if already wrapped
      │           ├─ isinstance(value, classmethod):
      │           │     ├─ method_event = "document_service.create"
      │           │     ├─ wrapped = _wrap_callable(value.__func__, for_static_or_class=True, class_module_name=cls.__module__, class_name=cls.__name__)
      │           │     ├─ setattr(cls, name, classmethod(wrapped))
      │           │     └─ setattr(wrapped, "__logged_decorated__", True)
      │           ├─ isinstance(value, staticmethod):
      │           │     ├─ method_event = "document_service.validate"
      │           │     ├─ wrapped = _wrap_callable(value.__func__, for_static_or_class=True, ...)
      │           │     ├─ setattr(cls, name, staticmethod(wrapped))
      │           │     └─ setattr(wrapped, "__logged_decorated__", True)
      │           └─ callable(value) ── instance methods:
      │                 ├─ method_event = "document_service.process"
      │                 ├─ wrapped = _wrap_callable(value)  ← no for_static_or_class
      │                 ├─ setattr(cls, name, wrapped)
      │                 └─ setattr(wrapped, "__logged_decorated__", True)
      └─ return target (class now has wrapped methods)

   b. CALLABLE path (target is a single function):
      ├─ __call__(target=some_func)
      ├─ callable(target) → True ──▶ _wrap_callable(target)  ← for_static_or_class=False (default)
      └─ return wrapper

③ CALL-TIME (instance method example)

   a. Instance method path (default, for_static_or_class=False):
      ├─ service.process("doc-123") ──▶ wrapper(instance=service, ...)
      │     ├─ instance.log_info(self.container.start)  ← "document_service.process.start"
      │     │     └─ _logger.info(event, extra=self._log_extra({"correlation_id": _client.current_id() or "-"}))
      │     ├─ try: return method(instance, ...) ──▶ original process() returns result
      │     └─ except Exception as error:
      │           ├─ instance.log_error(self.container.error, error_type=type(error).__name__, code=error.code)
      │           ├─ extra = {correlation_id: ..., error_type: "ValueError", code: None}
      │           └─ raise
      └─ returns "Processed doc-123"

   b. Classmethod path (for_static_or_class=True, class_module_name + class_name set):
      ├─ DocumentService.create() ──▶ static_or_class_wrapper(...)
      │     ├─ module_logger = logging.getLogger(cls.__module__).getChild(cls.__name__)
      │     │     └─ getChild("DocumentService")
      │     ├─ module_logger.info(self.container.start)  ← "document_service.create.start"
      │     ├─ try: return method(...) ──▶ original create()
      │     └─ except Exception: module_logger.error(...); raise
      └─ returns DocumentService instance

   c. Staticmethod path (for_static_or_class=True, class_module_name + class_name set):
      ├─ DocumentService.validate("doc-456") ──▶ static_or_class_wrapper(...)
      │     ├─ module_logger = logging.getLogger(cls.__module__).getChild(cls.__name__)
      │     ├─ module_logger.info(self.container.start)  ← "document_service.validate.start"
      │     ├─ try: return method(...) ──▶ original validate()
      │     └─ except Exception: module_logger.error(...); raise
      └─ returns True

   d. Async method path (for_static_or_class=False, asyncio.iscoroutinefunction=True):
      ├─ await service.async_process() ──▶ async_wrapper(instance=service, ...)
      │     ├─ instance.log_info(self.container.start)
      │     ├─ try: return await method(instance, ...)
      │     └─ except Exception: instance.log_error(...); raise
      └─ returns awaited result

## REAL RUN OUTPUT

Example output from mixin_logging with @logged decorator:
```
__main__.DocumentService - INFO - document_service.process.start
__main__.DocumentService - INFO - processing_document
__main__.DocumentService - INFO - document_service.create.start
__main__.DocumentService - INFO - document_service.validate.start
Instance method result: Processed doc-123
Factory result: <__main__.DocumentService object at 0x7f6c2645c950>
Static method result: True
```

Key observations:
- Decorator fan-out wraps instance methods, classmethods, and staticmethods in the class
- Instance methods use instance._logger (LoggingMixin bound per-class logger)
- Class/static methods fall back to module_logger (logging.getLogger(cls.__module__).getChild(cls.__name__))
- All paths emit event.start at entry, event.error on exception
- Correlation ID injected via _log_extra() → _client.current_id()
- setattr(wrapper, "__logged_decorated__", True) marks already-decorated methods to prevent double wrapping
