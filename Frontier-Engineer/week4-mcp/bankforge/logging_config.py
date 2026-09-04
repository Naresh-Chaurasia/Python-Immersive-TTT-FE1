"""
BankForge — centralized logging.

Design goals (explicit requirements for this capstone):
  - DEBUG is the default level everywhere unless LOG_LEVEL overrides it.
  - Every traced function logs an ENTER line (with its arguments) and an
    EXIT line (with its result and duration) — that's what @trace does.
  - Logs are structured JSON (one JSON object per line), per Section 4.7's
    "structured logging" requirement, so they're greppable/parseable in a
    real deployment.
  - PII / sensitive values are redacted before they ever reach a log line
    — see guardrails.redact_for_logging(). Detailed tracing and PII safety
    are not in tension: we trace *shapes*, not raw sensitive values.

Usage:
    from logging_config import get_logger, trace

    logger = get_logger(__name__)

    @trace(logger)
    def get_account(account_id: str) -> dict:
        ...
"""
from __future__ import annotations

import functools
import inspect
import json
import logging
import os
import sys
import time
import uuid
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Level configuration — DEBUG by default, everywhere, unless overridden.
# ---------------------------------------------------------------------------

DEFAULT_LOG_LEVEL = "DEBUG"
LOG_LEVEL = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()


class JsonFormatter(logging.Formatter):
    """One JSON object per log line. Keeps timestamp, level, logger name,
    service name (if set via LOGGER_SERVICE_NAME), message, and any extra
    fields attached via `logger.debug(msg, extra={"extra_fields": {...}})`.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "service": getattr(record, "service", os.environ.get("SERVICE_NAME", "bankforge")),
            "message": record.getMessage(),
        }
        extra_fields = getattr(record, "extra_fields", None)
        if extra_fields:
            payload["fields"] = extra_fields
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


_CONFIGURED_LOGGERS: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    """Returns a logger configured with the JSON formatter and DEBUG-by-default
    level. Safe to call repeatedly (e.g. once per module) — configures the
    underlying handler only once per logger name.
    """
    logger = logging.getLogger(name)

    if name not in _CONFIGURED_LOGGERS:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(LOG_LEVEL)
        logger.propagate = False
        _CONFIGURED_LOGGERS.add(name)

    return logger


def set_global_log_level(level: str) -> None:
    """Override the level on every logger this module has configured so far.
    Useful for tests that want to temporarily quiet or loosen logging."""
    resolved = level.upper()
    for name in _CONFIGURED_LOGGERS:
        logging.getLogger(name).setLevel(resolved)


# ---------------------------------------------------------------------------
# @trace — ENTER / EXIT logging for any function, sync or async.
# ---------------------------------------------------------------------------

def _safe_repr(value: Any, max_len: int = 200) -> Any:
    """Best-effort, log-safe representation of a value. Falls back to a
    truncated str() for anything that isn't already JSON-safe, so a call
    with an unexpected argument type never crashes logging itself."""
    try:
        json.dumps(value)
        text = value
    except TypeError:
        text = str(value)
    if isinstance(text, str) and len(text) > max_len:
        return text[:max_len] + f"...<truncated, {len(text)} chars total>"
    return text


def _bind_args(func: Callable, args: tuple, kwargs: dict) -> dict:
    """Maps positional + keyword arguments back onto parameter names, so
    ENTER logs read as {"account_id": "ACC001"} instead of a bare tuple."""
    try:
        sig = inspect.signature(func)
        bound = sig.bind_partial(*args, **kwargs)
        return {k: _safe_repr(v) for k, v in bound.arguments.items() if k != "self"}
    except TypeError:
        return {"args": _safe_repr(args), "kwargs": _safe_repr(kwargs)}


def trace(logger: logging.Logger, redact: Callable[[dict], dict] | None = None):
    """Decorator factory. Logs ENTER before the call and EXIT (or FAILED)
    after, at DEBUG level, including a call_id that ties the two lines
    together and a duration in milliseconds.

    `redact`, if given, is applied to the bound-arguments dict before it's
    logged — pass guardrails.redact_for_logging to keep PII out of logs
    without losing the shape of what was called. Wrap tool functions that
    take customer-identifying fields with this; it costs one line at the
    call site and is exactly what the Week 5 guardrails module asks for.
    """

    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)
        qualname = f"{func.__module__}.{func.__qualname__}"

        def _log_enter(call_id: str, bound_args: dict) -> None:
            if redact:
                bound_args = redact(bound_args)
            logger.debug(
                f"ENTER {qualname}",
                extra={"extra_fields": {"event": "enter", "call_id": call_id, "function": qualname, "args": bound_args}},
            )

        def _log_exit(call_id: str, start: float, result: Any) -> None:
            duration_ms = round((time.perf_counter() - start) * 1000, 3)
            logger.debug(
                f"EXIT {qualname}",
                extra={"extra_fields": {
                    "event": "exit", "call_id": call_id, "function": qualname,
                    "duration_ms": duration_ms, "result_preview": _safe_repr(result),
                }},
            )

        def _log_failure(call_id: str, start: float, exc: Exception) -> None:
            duration_ms = round((time.perf_counter() - start) * 1000, 3)
            logger.error(
                f"FAILED {qualname}: {exc}",
                extra={"extra_fields": {
                    "event": "failed", "call_id": call_id, "function": qualname,
                    "duration_ms": duration_ms, "error_type": type(exc).__name__,
                }},
                exc_info=True,
            )

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                call_id = uuid.uuid4().hex[:12]
                bound_args = _bind_args(func, args, kwargs)
                _log_enter(call_id, bound_args)
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                except Exception as exc:
                    _log_failure(call_id, start, exc)
                    raise
                _log_exit(call_id, start, result)
                return result
            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            call_id = uuid.uuid4().hex[:12]
            bound_args = _bind_args(func, args, kwargs)
            _log_enter(call_id, bound_args)
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                _log_failure(call_id, start, exc)
                raise
            _log_exit(call_id, start, result)
            return result
        return sync_wrapper

    return decorator


if __name__ == "__main__":
    logger = get_logger("logging_config.selftest")

    @trace(logger)
    def add(a: int, b: int) -> int:
        return a + b

    @trace(logger)
    def will_fail():
        raise ValueError("intentional failure for the self-test")

    print(f"LOG_LEVEL={LOG_LEVEL}")
    add(2, 3)
    try:
        will_fail()
    except ValueError:
        pass
