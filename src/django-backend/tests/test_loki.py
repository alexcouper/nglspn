# ruff: noqa: SLF001
import json
import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from project_showcase.loki import LokiHandler


@pytest.fixture
def handler():
    h = LokiHandler(
        url="https://loki.example.com/loki/api/v1/push",
        auth_token="test-token",
        labels={"service": "backend"},
        flush_interval=0.1,
    )
    yield h
    h.close()


class TestLokiPayloadFormat:
    def test_payload_contains_static_and_record_labels(self, handler):
        record = logging.LogRecord(
            name="django.request",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="something broke",
            args=(),
            exc_info=None,
        )
        handler.format(record)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock()
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            handler._flush([record])

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data)

        stream = payload["streams"][0]
        assert stream["stream"]["service"] == "backend"
        assert stream["stream"]["level"] == "error"
        assert stream["stream"]["logger"] == "django.request"

    def test_payload_values_are_nanosecond_timestamp_and_message(self, handler):
        record = logging.LogRecord(
            name="app",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        handler.format(record)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock()
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            handler._flush([record])

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)
        ts, msg = payload["streams"][0]["values"][0]

        assert ts == str(int(record.created * 1e9))
        assert "hello" in msg


class TestLokiAuthHeader:
    def test_request_includes_x_token_header(self, handler):
        record = logging.LogRecord(
            name="app",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hi",
            args=(),
            exc_info=None,
        )
        handler.format(record)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock()
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            handler._flush([record])

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("X-token") == "test-token"
        assert req.get_header("Content-type") == "application/json"


class TestLokiBatching:
    def test_records_grouped_by_level_and_logger(self, handler):
        records = []
        for level, name in [
            (logging.INFO, "app"),
            (logging.ERROR, "app"),
            (logging.INFO, "app"),
        ]:
            r = logging.LogRecord(
                name=name,
                level=level,
                pathname="",
                lineno=0,
                msg="msg",
                args=(),
                exc_info=None,
            )
            handler.format(r)
            records.append(r)

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock()
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            handler._flush(records)

        req = mock_urlopen.call_args[0][0]
        payload = json.loads(req.data)

        # Two streams: (info, app) and (error, app)
        assert len(payload["streams"]) == 2
        levels = {s["stream"]["level"] for s in payload["streams"]}
        assert levels == {"info", "error"}

    def test_background_thread_flushes_on_interval(self, handler):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__ = MagicMock()
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

            handler.emit(
                logging.LogRecord(
                    name="app",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg="auto-flush",
                    args=(),
                    exc_info=None,
                )
            )
            # Wait for flush_interval (0.1s) + some margin
            time.sleep(0.3)

        assert mock_urlopen.called


class TestLokiGracefulFailure:
    def test_network_error_does_not_raise(self, handler):
        record = logging.LogRecord(
            name="app",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="fail",
            args=(),
            exc_info=None,
        )
        handler.format(record)

        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            # Should not raise
            handler._flush([record])

    def test_emit_after_close_is_ignored(self, handler):
        handler.close()
        # Should not raise or queue anything
        handler.emit(
            logging.LogRecord(
                name="app",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="after close",
                args=(),
                exc_info=None,
            )
        )
        assert handler._queue.empty()
