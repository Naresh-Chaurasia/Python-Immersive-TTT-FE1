"""Tests for logging_config.py. Run with: python3 -m pytest tests/ -v"""
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import logging_config


@pytest.fixture
def captured_logger():
    """A logger writing to an in-memory stream instead of stdout, so tests
    can assert on the exact JSON emitted."""
    import io
    logger = logging.getLogger("test.captured")
    logger.handlers.clear()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging_config.JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel("DEBUG")
    logger.propagate = False
    yield logger, stream


def test_default_log_level_is_debug():
    assert logging_config.DEFAULT_LOG_LEVEL == "DEBUG"


def test_json_formatter_produces_valid_json(captured_logger):
    logger, stream = captured_logger
    logger.info("hello world")
    line = stream.getvalue().strip()
    parsed = json.loads(line)
    assert parsed["message"] == "hello world"
    assert parsed["level"] == "INFO"


def test_trace_logs_enter_and_exit(captured_logger):
    logger, stream = captured_logger

    @logging_config.trace(logger)
    def add(a, b):
        return a + b

    add(2, 3)
    lines = [json.loads(l) for l in stream.getvalue().strip().splitlines()]
    assert len(lines) == 2
    assert lines[0]["fields"]["event"] == "enter"
    assert lines[0]["fields"]["args"] == {"a": 2, "b": 3}
    assert lines[1]["fields"]["event"] == "exit"
    assert lines[1]["fields"]["result_preview"] == 5
    # ENTER and EXIT share the same call_id
    assert lines[0]["fields"]["call_id"] == lines[1]["fields"]["call_id"]


def test_trace_logs_failure_and_reraises(captured_logger):
    logger, stream = captured_logger

    @logging_config.trace(logger)
    def will_fail():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        will_fail()

    lines = [json.loads(l) for l in stream.getvalue().strip().splitlines()]
    assert lines[-1]["level"] == "ERROR"
    assert lines[-1]["fields"]["event"] == "failed"
    assert lines[-1]["fields"]["error_type"] == "ValueError"


def test_trace_applies_redact_function(captured_logger):
    logger, stream = captured_logger

    def redact(args):
        return {k: ("***" if k == "secret" else v) for k, v in args.items()}

    @logging_config.trace(logger, redact=redact)
    def handle(secret, public):
        return "ok"

    handle(secret="s3nsitive", public="fine")
    lines = [json.loads(l) for l in stream.getvalue().strip().splitlines()]
    assert lines[0]["fields"]["args"]["secret"] == "***"
    assert lines[0]["fields"]["args"]["public"] == "fine"
