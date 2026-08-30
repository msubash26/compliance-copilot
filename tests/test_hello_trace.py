"""Offline checks for the B3 hello-trace script.

Deliberately no network: CI has neither Ollama nor the LangFuse stack, so these cover the
parts that can regress silently — the env-var guard and the token budget from ADR-009.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hello_trace.py"


def _load():
    spec = importlib.util.spec_from_file_location("hello_trace", _PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["hello_trace"] = module
    spec.loader.exec_module(module)
    return module


hello_trace = _load()


def test_require_exits_with_a_useful_message(monkeypatch):
    monkeypatch.delenv("SOME_MISSING_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        hello_trace._require("SOME_MISSING_KEY")
    assert ".env" in str(exc.value)


def test_require_returns_the_value(monkeypatch):
    monkeypatch.setenv("SOME_KEY", "value")
    assert hello_trace._require("SOME_KEY") == "value"


def test_token_budget_exceeds_observed_reasoning_usage():
    """ADR-009: reasoning is billed to the completion budget.

    A one-sentence answer measured at ~1170 completion tokens on qwen3.5:9b, nearly all of it
    thinking. Anything at or below that silently returns empty content, so the budget needs
    real headroom rather than a limit sized for the visible answer.
    """
    assert hello_trace.MAX_TOKENS >= 2048
