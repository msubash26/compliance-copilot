"""The graph, the ceilings and the harvester -- none of which need a model.

What a working demo proves is that the happy path works. What it hides is every
path where the agent runs out of budget, a tool errors, or a result is too big to
read. Those are the ones `FAILURE_MODES.md` is about, so they are the ones tested
here, against a scripted model that cannot be flaky.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from regops_agents.agent import MAX_STEPS, SYSTEM, Run, _harvest, ask
from regops_agents.mcp_tools import MAX_RESULT_CHARS, _render

pytest_plugins = ["fixtures_agents"]

from fixtures_agents import ScriptedModel, tool_call  # noqa: E402


def _agent(replies, tools):
    from langgraph.prebuilt import create_react_agent

    return create_react_agent(ScriptedModel(replies=replies), tools, prompt=SYSTEM)


# -- the ceilings ----------------------------------------------------------


async def test_a_step_ceiling_returns_a_partial_run_rather_than_raising(echo_tool):
    """The whole point of the ceiling. `GraphRecursionError` must not escape."""
    looping = [tool_call("search_notices", {"query": "again"}, "c1")]
    run = await ask(_agent(looping, [echo_tool]), "what does the notice require?", max_steps=6)
    assert isinstance(run, Run)
    assert run.stopped_by == "step_ceiling"
    assert run.partial
    assert run.answer, "a stopped run still reports what it has"


async def test_a_stopped_run_says_how_far_it_got(echo_tool):
    looping = [tool_call("search_notices", {"query": "again"}, "c1")]
    run = await ask(_agent(looping, [echo_tool]), "q", max_steps=6)
    assert "step_ceiling" in run.answer
    assert run.tool_calls, "the work it did before stopping is not thrown away"


async def test_the_frameworks_own_apology_does_not_pass_as_an_answer(echo_tool):
    """langgraph 1.2.11 appends its own message at the recursion limit.

    "Sorry, need more steps to process this request." -- fluent, plausible, and
    exactly what a model that decided to decline would say. Nothing raises, so a
    caller reading `answer` alone records an exhausted run as the agent's
    considered judgement. The marker is what makes the two distinguishable.
    """
    looping = [tool_call("search_notices", {"query": "again"}, "c1")]
    run = await ask(_agent(looping, [echo_tool]), "q", max_steps=6)
    assert run.answer.startswith("[stopped by step_ceiling")
    assert "need more steps" in run.answer, "the framework's text is kept, not hidden"


async def test_a_wall_clock_ceiling_stops_a_run_that_is_not_looping_on_steps(echo_tool):
    """Zero seconds: the first yield is already over budget."""
    replies = [tool_call("search_notices", {"query": "x"}, "c1")]
    run = await ask(_agent(replies, [echo_tool]), "q", max_steps=MAX_STEPS, max_seconds=0.0)
    assert run.stopped_by == "wall_clock"


async def test_a_run_that_finishes_is_not_marked_partial(echo_tool):
    replies = [
        tool_call("search_notices", {"query": "beneficial owner"}, "c1"),
        AIMessage(content="Clause 6.14 requires it. (d0000001, 6.14)"),
    ]
    run = await ask(_agent(replies, [echo_tool]), "q")
    assert run.stopped_by == ""
    assert not run.partial
    assert run.answer.startswith("Clause 6.14")


# -- the harvester ---------------------------------------------------------


def test_a_tool_result_is_paired_with_the_call_that_asked_for_it():
    """Pairing by id, not by position -- a failed call must not shift the rest."""
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "search_notices", "args": {"query": "a"}, "id": "c1", "type": "tool_call"},
                {"name": "search_local", "args": {"query": "b"}, "id": "c2", "type": "tool_call"},
            ],
        ),
        ToolMessage(content="x" * 50, tool_call_id="c2"),
        ToolMessage(content="TOOL ERROR from search_notices: no", tool_call_id="c1"),
        AIMessage(content="done"),
    ]
    answer, calls = _harvest(msgs)
    assert answer == "done"
    by_tool = {c["tool"]: c for c in calls}
    assert by_tool["search_local"]["result_chars"] == 50
    assert by_tool["search_notices"]["error"] is True
    assert by_tool["search_local"]["error"] is False


def test_the_answer_is_the_last_message_with_no_tool_calls():
    msgs = [
        AIMessage(content="thinking", tool_calls=[
            {"name": "t", "args": {}, "id": "c1", "type": "tool_call"}
        ]),
        ToolMessage(content="r", tool_call_id="c1"),
        AIMessage(content="the answer"),
    ]  # fmt: skip
    assert _harvest(msgs)[0] == "the answer"


def test_no_final_answer_is_an_empty_string_not_a_tool_call_body():
    msgs = [
        AIMessage(content="", tool_calls=[
            {"name": "t", "args": {}, "id": "c1", "type": "tool_call"}
        ]),
        ToolMessage(content="a result", tool_call_id="c1"),
    ]  # fmt: skip
    assert _harvest(msgs)[0] == ""


# -- the mitigation, pinned ------------------------------------------------


def test_the_system_prompt_still_carries_the_measured_filter_mitigation():
    """F1's fix is one sentence, and deleting it costs 1-in-29 gold documents.

    Measured: bare schemas gave `qwen3.5:9b` 5 unasked-for filters in 29 calls,
    one of which removed the gold document; this sentence took both to zero. A
    prompt edit that drops it would be invisible without this test.
    """
    for field in ("issuer", "doc_type", "date_from"):
        assert field in SYSTEM
    assert "unless the user's question names one" in SYSTEM


# -- result size -----------------------------------------------------------


def test_an_oversized_tool_result_is_cut_and_says_that_it_was():
    """`list_obligations` on Notice 637 is 59,307 characters for one page.

    Silence about the cut is the failure research 6 measured: an over-long prompt
    is truncated from the *front*, so the instructions go before the result does.
    """

    class R:
        content = [type("C", (), {"text": "y" * (MAX_RESULT_CHARS + 5_000)})()]
        structured_content = None

    out = _render(R())
    assert len(out) < MAX_RESULT_CHARS + 200
    assert "truncated" in out
    assert f"{MAX_RESULT_CHARS:,} shown" in out


def test_a_result_within_budget_is_returned_whole():
    class R:
        content = [type("C", (), {"text": "short"})()]
        structured_content = None

    assert _render(R()) == "short"


# -- the Pydantic AI build, without connecting to anything -----------------


def test_the_pydantic_ai_agent_is_built_from_the_same_prompt_and_schema():
    """Constructs only. The stdio server is not spawned until the agent is entered.

    The comparison in ADR-027 is only worth anything if both agents are given the
    same task, so the two things that define the task -- the measured system
    prompt and the `Answer` schema -- are asserted to be shared rather than
    reimplemented. A framework comparison whose two arms drifted apart would
    measure the drift.
    """
    from regops_agents.pydai import build
    from regops_agents.structured import Answer

    agent, toolset = build(index=Path("index/regdocs.duckdb"))
    assert agent.output_type is Answer
    texts = [getattr(i, "instruction", str(i)) for i in (agent._instructions or [])]
    assert any(t == SYSTEM for t in texts), "both agents must carry the identical prompt"
    assert toolset is not None


def test_the_pydantic_ai_agent_talks_to_the_same_server():
    from regops_agents.pydai import build

    _, toolset = build(index=Path("index/regdocs.duckdb"))
    transport = getattr(toolset, "_transport", None) or getattr(toolset, "transport", None)
    if transport is None:  # the attribute is private and may be renamed upstream
        pytest.skip("transport attribute not exposed by this pydantic-ai version")
    assert "regdocs-mcp" in " ".join(getattr(transport, "args", []))
