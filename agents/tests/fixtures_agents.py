"""Fixtures for the agent suite, in a uniquely named module.

Four workspace members now ship a `tests/` directory and pytest's default import
mode resolves test modules by basename. `ingest/tests/` is a package (so
`tests.conftest`) and `evals/tests/` is not (so `conftest`) -- both spellings are
taken, and a third `conftest.py` collides with `ImportPathMismatchError`.
`retrieval/tests/` solved this with `fixtures_retrieval.py`; this is the same
move for the same reason.

**No model, no server, no GPU.** The scripted chat model below is what makes the
graph testable in CI: what can be wrong in a way a demo hides is the plumbing --
does the step ceiling return instead of raising, does the harvester pair a tool
result with the call that asked for it -- not the model's opinion.
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedModel(BaseChatModel):
    """Returns a written-down sequence of replies, then repeats the last one.

    Repeating rather than exhausting is deliberate: a model that keeps calling a
    tool is precisely the loop the step ceiling exists to stop, and a script that
    ran out would end the run for the wrong reason.
    """

    replies: list[AIMessage]
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> BaseChatModel:  # noqa: ARG002
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        i = min(self.calls, len(self.replies) - 1)
        self.calls += 1
        return ChatResult(generations=[ChatGeneration(message=self._fresh(self.replies[i]))])

    def _fresh(self, template: AIMessage) -> AIMessage:
        """A new message with new ids on every reply.

        Returning the same instance twice does not loop the graph, it *ends* it:
        `add_messages` merges by message id, so the second identical reply
        replaces the first instead of appending, the tool call reads as already
        answered, and the run terminates. A scripted model that cannot repeat
        itself cannot exercise the step ceiling -- which is what the ceiling is
        for.
        """
        n = self.calls
        return AIMessage(
            content=template.content,
            id=f"scripted-{n}",
            tool_calls=[
                {**tc, "id": f"{tc.get('id', 'call')}-{n}"} for tc in (template.tool_calls or [])
            ],
        )


def tool_call(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}],
    )


@pytest.fixture
def echo_tool():
    """A tool that returns what it was asked for, so a test can assert on it."""
    from langchain_core.tools import StructuredTool

    def search_notices(query: str, top_k: int = 10) -> str:
        return f'{{"hits": [], "total": 0, "echo": "{query}", "top_k": {top_k}}}'

    return StructuredTool.from_function(
        func=search_notices,
        name="search_notices",
        description="stub",
    )
