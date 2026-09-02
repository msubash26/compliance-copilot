"""A ReAct agent over the MCP server, with ceilings that return rather than raise.

Two design points carry the day's findings.

**The system prompt is a measured mitigation, not boilerplate.** Day 6's probe
ran 30 golden questions through `qwen3.5:9b` and `qwen3.8` with the four tool
schemas the server publishes. Given only the schemas, the 9B model set a filter
nobody asked for on 5 of 29 calls and one of those filters removed the gold
document from the results. Adding the sentence in `SYSTEM` below takes that to
**0 of 30** -- matching the 2.6x larger model at half the latency. The prompt is
the mitigation; the model size was not the binding constraint. See
`toolcall_probe.py` and F1 in `FAILURE_MODES.md`.

**A ceiling that raises is not a ceiling.** The prep plan asks for a hard step
limit "with a partial result returned rather than an exception", and that is the
shape a cost ceiling takes on Day 7. An agent that exhausts its budget has
usually done real work -- searched, read two clauses -- and throwing that away
turns a degraded answer into no answer. So both ceilings are reported in the
result, and `Run.stopped_by` says which one fired.

**And the framework does not tell you when its own ceiling fires.** Measured on
langgraph 1.2.11: hitting `recursion_limit` raises nothing on either `stream` or
`invoke`. The run simply stops and returns, with the last message an `AIMessage`
carrying tool calls that were never answered. An agent written to catch
`GraphRecursionError` -- which is what the exception exists for and what older
versions did -- would therefore report an exhausted run as a *completed* one, and
its caller could not tell a finished answer from a truncated one. So exhaustion
is detected structurally here, from the message state, and the exception is still
caught in case a version raises it. See F4 in `FAILURE_MODES.md`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

MODEL = "qwen3.5:9b"

# Day 6's measured prompt. The second paragraph is the whole of F1's mitigation,
# and its cost is stated in FAILURE_MODES.md: on a multi-issuer corpus it would
# suppress a filter that is sometimes genuinely useful. This corpus is MAS-only,
# so here it suppresses only guesses.
SYSTEM = (
    "You are a regulatory compliance assistant with access to a search index of "
    "Singapore MAS notices and guidelines. Use the tools to find the clause that "
    "answers the user's question. Do not answer from memory.\n"
    "Search broadly first. Do not set issuer, doc_type or date_from unless the "
    "user's question names one explicitly -- a wrong filter silently removes the "
    "answer from the results, and you will not be told that it did.\n"
    "Cite every claim with the doc_id and section_path of the clause it came from. "
    "If the corpus does not answer the question, say so rather than inferring."
)

# Each ReAct turn is two graph steps (model, then tools), so 12 is six tool calls.
# Six is above what any Day 5 question needed and below the point where a loop is
# indistinguishable from work.
MAX_STEPS = 12

# Wall-clock. `qwen3.5:9b` answers in ~1.9s over five clauses (Day 5) and a
# `search_local` call carries a ~400ms rerank, so a well-behaved run is seconds.
# 180s is a loop, not a hard question.
MAX_SECONDS = 180.0


@dataclass
class Run:
    """One question, and everything the failure work needs to read afterwards."""

    question: str
    answer: str = ""
    messages: list[BaseMessage] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    steps: int = 0
    seconds: float = 0.0
    stopped_by: str = ""  # "" | "step_ceiling" | "wall_clock" | "error"
    error: str = ""

    @property
    def partial(self) -> bool:
        return bool(self.stopped_by)


def build_agent(tools: list, *, model: str = MODEL, num_ctx: int | None = None):
    """A ReAct agent. `num_ctx` is left at the server default unless F3 sets it.

    Research 6 measured that a `num_ctx` below the prompt truncates it **from the
    front**, with no error -- taking the system prompt and the question before it
    touches an over-long tool result. It is exposed here so that failure can be
    provoked deliberately, and it is `None` in normal use.
    """
    kwargs: dict = {"model": model, "temperature": 0.0, "reasoning": False}
    if num_ctx is not None:
        kwargs["num_ctx"] = num_ctx
    return create_react_agent(ChatOllama(**kwargs), tools, prompt=SYSTEM)


def _exhausted(messages: list[BaseMessage], steps: int, max_steps: int) -> bool:
    """Did the graph stop because it ran out of budget rather than because it finished?

    Two independent signals, because the framework offers none. A completed ReAct
    run ends on an `AIMessage` with no tool calls; a run cut off mid-flight ends
    on one whose tool calls were never answered. The step count is the second
    signal, for the case where the cut lands on a tool result instead.
    """
    if steps >= max_steps:
        return True
    last = messages[-1] if messages else None
    return isinstance(last, AIMessage) and bool(last.tool_calls)


def _harvest(messages: list[BaseMessage]) -> tuple[str, list[dict]]:
    """The final answer text, and every tool call with its arguments and size."""
    calls: list[dict] = []
    pending: dict[str, dict] = {}
    for m in messages:
        if isinstance(m, AIMessage):
            for tc in m.tool_calls or []:
                rec = {"tool": tc["name"], "args": tc["args"], "result_chars": 0, "error": False}
                calls.append(rec)
                if tc.get("id"):
                    pending[tc["id"]] = rec
        elif isinstance(m, ToolMessage):
            rec = pending.get(m.tool_call_id)
            if rec is not None:
                text = str(m.content)
                rec["result_chars"] = len(text)
                rec["error"] = text.startswith("TOOL ERROR")
    answer = ""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and not m.tool_calls and str(m.content).strip():
            answer = str(m.content).strip()
            break
    return answer, calls


async def ask(
    agent,
    question: str,
    *,
    max_steps: int = MAX_STEPS,
    max_seconds: float = MAX_SECONDS,
) -> Run:
    """One question. Ceilings return a partial `Run`; they never raise.

    Async because the MCP tools are. `StructuredTool` built from a coroutine
    refuses sync invocation outright -- "StructuredTool does not support sync
    invocation" -- so driving this graph with `stream` rather than `astream`
    fails on the first tool call, before any tool has run. Worth knowing that the
    failure is immediate and loud rather than a silent fallback to a blocking
    call, which is the friendlier of the two possible designs.
    """
    run = Run(question=question)
    t0 = time.perf_counter()
    state = {"messages": [HumanMessage(content=question)]}
    cfg = {"recursion_limit": max_steps}

    try:
        # Streaming rather than `invoke` so the wall clock is enforced *between*
        # steps. A single model call cannot be interrupted from here, so the
        # ceiling is checked at the only place the graph yields control.
        last = None
        async for chunk in agent.astream(state, cfg, stream_mode="values"):
            last = chunk
            run.steps += 1
            if time.perf_counter() - t0 > max_seconds:
                run.stopped_by = "wall_clock"
                break
        run.messages = list((last or state)["messages"])
        if not run.stopped_by and _exhausted(run.messages, run.steps, max_steps):
            run.stopped_by = "step_ceiling"
    except GraphRecursionError:  # not raised by langgraph 1.2.11; kept for versions that do
        run.stopped_by = "step_ceiling"
        run.messages = list(state["messages"])
    except Exception as exc:  # noqa: BLE001 -- a tool or transport failure is a result
        run.stopped_by = "error"
        run.error = f"{type(exc).__name__}: {exc}"[:300]
        run.messages = list(state["messages"])

    run.seconds = time.perf_counter() - t0
    run.answer, run.tool_calls = _harvest(run.messages)
    if run.stopped_by:
        # Always marked, never only when the answer is empty. At its recursion
        # limit langgraph 1.2.11 appends an `AIMessage` of its own reading
        # "Sorry, need more steps to process this request." -- fluent, plausible,
        # and indistinguishable from a model that decided to decline. A caller
        # reading `answer` alone would record that as the agent's judgement.
        run.answer = (
            f"[stopped by {run.stopped_by} after {run.steps} steps, "
            f"{run.seconds:.1f}s, {len(run.tool_calls)} tool call(s)] "
            f"{run.answer}"
        ).strip()
    return run
