"""Tests for logging functionality."""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path

from kairo.config import Config
from kairo.logging import log
from kairo.storage import IndexManager


class TestLoggingConfiguration:
    """Tests for logging configuration."""

    def test_logging_configuration(self):
        """Test that logging configuration is correctly set up."""

        handlers = list(log._core.handlers.values())
        assert len(handlers) == 1

        handler = handlers[0]
        # Verify output stream is stderr
        assert handler._sink._stream == sys.stderr
        # Verify format by checking the formatter tokens
        format_tokens = handler._formatter._tokens
        expected_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        # Reconstruct format from tokens (excluding exception token added by loguru)
        reconstructed = "".join(token[1] for token in format_tokens if token[1])
        assert expected_format in reconstructed
        # Verify default log level is INFO (20)
        assert handler._levelno == 20
        # Verify colorize
        assert handler._colorize is True

    def test_logging_output_format(self):
        """Test that log messages are output with correct format."""

        sink = StringIO()
        handler_id = log.add(
            sink, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

        try:
            test_message = "Test log message"
            log.info(test_message)

            output = sink.getvalue()
            assert test_message in output
            assert "| INFO |" in output
            assert "Test log message" in output
        finally:
            log.remove(handler_id)

    def test_debug_suppressed_at_info_level(self):
        """Test that log.debug output is correctly suppressed when log level is INFO."""

        sink = StringIO()
        # Add handler with INFO level (same as default)
        handler_id = log.add(sink, level="INFO", format="{message}")

        try:
            # Send debug message
            log.debug("This debug message should not appear")

            # Send info message (should appear)
            log.info("This info message should appear")

            output = sink.getvalue()
            # Debug should be suppressed
            assert "This debug message should not appear" not in output
            # Info should appear
            assert "This info message should appear" in output
        finally:
            log.remove(handler_id)


class TestAccountConfigLogging:
    """Tests for AccountConfig initialization logging."""

    def test_account_config_invalid_data_logging(self):
        """Test that invalid AccountConfig (missing username) data triggers warning and debug logs."""

        sink = StringIO()
        handler_id = log.add(
            sink, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

        try:
            config_data = {
                "accounts": {"invalid_account": {"provider": "gmail"}},
                "storage": {"path": "/tmp/test"},
            }

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".json"
            ) as f:
                json.dump(config_data, f)
                config_path = f.name

            try:
                _ = Config(config_path)

                output = sink.getvalue()
                assert "Skipping invalid account: invalid_account" in output
                assert (
                    "validation error" in output.lower() or "missing" in output.lower()
                )
            finally:
                Path(config_path).unlink()
        finally:
            log.remove(handler_id)


class TestIndexEmailMetadataLogging:
    """Tests for IndexEmailMetadata initialization logging."""

    def test_index_email_metadata_invalid_data_logging(self):
        """Test that invalid IndexEmailMetadata (bool as str) data triggers warning and debug logs."""

        sink = StringIO()
        handler_id = log.add(
            sink, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )

        try:
            index_dict = {
                "folders": {
                    "inbox": [
                        {
                            "email_id": "test123",
                            "from_address": "test@example.com",
                            "to_addresses": [],
                            "subject": "Test",
                            "date": "2024-01-01",
                            "folder": "inbox",
                            "attachments": [],
                            "has_attachments": "random_string",
                            "processed": False,
                        }
                    ]
                }
            }

            _ = IndexManager.load_from_dict(index_dict)

            output = sink.getvalue()
            assert "Skip invalid email" in output
            assert "test@example.com" in output
            assert "validation error" in output.lower() or "bool" in output.lower()
        finally:
            log.remove(handler_id)
