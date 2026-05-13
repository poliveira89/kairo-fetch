"""Pytest fixtures and helpers for kairo-fetch tests."""

import pytest

from kairo.config import Config


@pytest.fixture(autouse=True)
def reset_config():
    """Reset Config singleton before each test."""
    Config.reset()
    yield
    Config.reset()


def assert_raises_on_connect(retriever_class, **kwargs):
    """Helper to test that a retriever raises an exception on connect."""
    with pytest.raises(ValueError):
        retriever = retriever_class(**kwargs)
        retriever.connect()
