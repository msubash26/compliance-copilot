"""The whole graph, in CI, with no GPU: recorded tool results and a scripted model.

This is the third of the gate's three mechanisms (`regops_evals.gate_agent`), and
the one that needs its limits stated first.

**It gates structure, not quality.** Nothing here can tell you the agent got
better or worse at answering, because the model is a script and the corpus is a
frozen dict. What it can tell you is whether the graph still *works*: whether the
router still reaches the retriever, whether a coverage question still fans out
into four sibling branches, whether an unresolvable citation still sends a run
backwards exactly once, whether a ceiling still returns a partial answer instead
of raising, and whether the tool recorder still sees every call. Those are the
things that break when someone edits an edge, and every one of them is invisible
to a metrics artifact that was produced before the edit.

**The tool results are real.** `replay/tools.json` is 44 recorded MCP results
captured from two live runs -- one `factual_lookup`, one `coverage` -- keyed by
`[tool, args]`. A call the fixture does not hold raises, loudly, naming what was
asked for. That matters more than it sounds: a replay whose misses fall back to
an empty result would pass forever while testing nothing, which is the failure
mode of every recorded-fixture suite that has one.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from regops_agents.budget import Budget, new_spend
from regops_agents.llm import Reply
from regops_agents.record import Recorder
from regops_agents.supervisor import build
from regops_agents.workers import Toolbox

FIXTURE = Path(__file__).parent / "replay" / "tools.json"

LOOKUP_Q = "How often should an FMC monitor its managed assets to ensure compliance?"
COVERAGE_Q = (
    "Which documents in the corpus state an obligation about politically "
    "exposed persons, and which are silent on it?"
)

# The search text the router actually wrote on the recorded runs. The script has
# to reproduce it because the fixture is keyed by arguments -- which is the point:
# a graph that starts passing a different `top_k`, or stops rewriting the query,
# is a graph whose recorded corpus no longer applies to it, and the replay says so
# rather than quietly answering from a neighbouring recording.
LOOKUP_QUERY = "FMC managed assets monitoring frequency compliance"
COVERAGE_QUERY = "politically exposed persons obligation"


class MissingRecording(KeyError):
    """A tool call the fixture does not hold. Loud on purpose -- see the docstring."""


class ReplayTool:
    """One MCP tool, answering from the recording and refusing to improvise."""

    def __init__(self, name: str, recorded: dict[str, str], calls: list):
        self.name = name
        self.recorded = recorded
        self.calls = calls

    async def ainvoke(self, args: dict) -> str:
        key = json.dumps([self.name, args], sort_keys=True)
        self.calls.append((self.name, args))
        if key not in self.recorded:
            raise MissingRecording(
                f"{self.name}{args} is not in {FIXTURE.name}. Re-record the fixture, "
                "or the replay is testing a path the real server never served."
            )
        return self.recorded[key]


class ReplayIndex:
    """Layer 2 over the recording: a clause exists if the recorded search found it."""

    def __init__(self, uids: set[str]):
        self.uids = uids

    def clause_by_uid(self, uid: str):
        if uid not in self.uids:
            return None
        doc, _, path = uid.partition(":")
        return type("Clause", (), {"title": f"doc {doc[:8]}", "section_path": path, "text": ""})()


@pytest.fixture(scope="module")
def recorded() -> dict[str, str]:
    return json.loads(FIXTURE.read_text())


@pytest.fixture(scope="module")
def known_uids(recorded) -> set[str]:
    """Every clause the recorded searches returned, as layer 2's universe."""
    uids: set[str] = set()
    for key, value in recorded.items():
        if json.loads(key)[0] != "search_notices":
            continue
        for h in json.loads(value).get("hits", []):
            uids.add(f"{h['doc_id']}:{h['section_path']}")
    return uids


class Script:
    """The model, as a lookup on the worker that called it.

    Keyed by `chat(..., name=)` rather than by call order: the order changes when
    a reroute fires, and a positional script would then be testing the script.
    The `llm:` prefix each worker passes is stripped here so the script reads as
    `Script(route=..., extract=...)` -- it is a LangFuse naming convention
    (`trace.py`), not part of the graph's contract.
    """

    def __init__(self, **by_name: str):
        self.by_name = by_name
        self.seen: list[str] = []

    def __call__(self, prompt, **kw) -> Reply:
        name = kw.get("name", "chat").removeprefix("llm:")
        self.seen.append(name)
        content = self.by_name.get(name)
        if content is None:
            raise AssertionError(f"the script has no reply for worker {name!r}")
        if callable(content):
            content = content(len([s for s in self.seen if s == name]))
        return Reply(content=content, seconds=0.001, in_tokens=100, out_tokens=20)


def _route(route: str, query: str) -> str:
    return json.dumps({"route": route, "query": query})


def _answer(uid: str, sufficient: bool = True) -> str:
    doc, _, path = uid.partition(":")
    return json.dumps(
        {
            "answer": "The manager must monitor on an ongoing basis.",
            "citations": [{"doc_id": doc, "section_path": path}],
            "sufficient": sufficient,
        }
    )


FINDING = json.dumps({"covered": True, "section_path": "8.2", "quote": "a PEP obligation"})


def harness(recorded, known_uids, script, monkeypatch, *, budget=None, plan_and_execute=False):
    """The compiled graph, a replay toolbox and the config, with nothing live in it."""
    monkeypatch.setattr("regops_agents.workers.chat", script)
    calls: list = []
    tools = {
        name: ReplayTool(name, recorded, calls)
        for name in ("search_notices", "get_document_section", "list_obligations", "diff_versions")
    }
    rec = Recorder()
    box = Toolbox(index=Path("none"), tools=tools, ix=ReplayIndex(known_uids), recorder=rec)
    app = build(plan_and_execute=plan_and_execute).compile(checkpointer=InMemorySaver())
    cfg = {
        "configurable": {
            "toolbox": box,
            "budget": budget or Budget(),
            # Live, not zero: `_ceiling` reads the wall clock from here, and a t0
            # of 0.0 is an instantly exhausted run (ADR-029).
            "t0": time.perf_counter(),
            "approve": False,
            "thread_id": "replay",
        },
        "recursion_limit": 60,
    }
    return app, cfg, calls, rec


def _state(question: str) -> dict:
    return {
        "question": question,
        "spend": new_spend(),
        "retries": 0,
        "findings": [],
        "notes": [],
    }


# -- the two shapes the graph has ------------------------------------------


async def test_a_lookup_question_runs_end_to_end_and_answers(recorded, known_uids, monkeypatch):
    uid = sorted(known_uids)[0]
    script = Script(
        route=_route("factual_lookup", LOOKUP_QUERY),
        extract=_answer(uid),
        synthesise="The manager must monitor on an ongoing basis (doc, clause 1).",
    )
    app, cfg, calls, rec = harness(recorded, known_uids, script, monkeypatch)
    out = await app.ainvoke(_state(LOOKUP_Q), cfg)

    assert out["route"] == "factual_lookup"
    assert out["answer"]
    assert not out.get("stopped_by")
    assert out["citations"] == [{"doc_id": uid.split(":")[0], "section_path": uid.split(":")[1]}]
    # One search and five reads is this retriever's fixed shape (READ_N).
    assert [c[0] for c in calls] == ["search_notices"] + ["get_document_section"] * 5
    assert script.seen == ["route", "extract", "synthesise"]


async def test_a_coverage_question_fans_out_into_sibling_branches(
    recorded, known_uids, monkeypatch
):
    script = Script(
        route=_route("coverage", COVERAGE_QUERY),
        inspect=FINDING,
        synthesise="Four documents were examined.",
    )
    app, cfg, calls, rec = harness(recorded, known_uids, script, monkeypatch)
    out = await app.ainvoke(_state(COVERAGE_Q), cfg)

    # FAN_WIDTH branches, one verdict per document, no document judged twice.
    findings = out["findings"]
    assert len(findings) == 4
    assert len({f["doc_id"] for f in findings}) == 4
    assert script.seen.count("inspect") == 4
    # The route never touches the extractor: coverage goes retrieve -> fan_out.
    assert "extract" not in script.seen
    assert any(c[0] == "list_obligations" for c in calls)


# -- the behaviours a metrics artifact cannot see ---------------------------


async def test_an_unresolvable_citation_sends_the_run_back_exactly_once(
    recorded, known_uids, monkeypatch
):
    """The reroute is one edge. Deleting it is invisible to `eval.json` until a re-run."""
    good = sorted(known_uids)[0]

    def extract(nth: int) -> str:
        # First pass cites a clause that is not in the index; second cites a real one.
        return _answer("deadbeefdeadbeef:99.99") if nth == 1 else _answer(good)

    script = Script(
        route=_route("factual_lookup", LOOKUP_QUERY),
        extract=extract,
        synthesise="answered on the second pass",
    )
    app, cfg, calls, rec = harness(recorded, known_uids, script, monkeypatch)
    out = await app.ainvoke(_state(LOOKUP_Q), cfg)

    assert out["retries"] == 1
    assert script.seen.count("extract") == 2
    assert [c[0] for c in calls].count("search_notices") == 2
    assert out["violations"] == []
    assert out["citations"] == [{"doc_id": good.split(":")[0], "section_path": good.split(":")[1]}]


async def test_an_insufficient_answer_also_sends_it_back(recorded, known_uids, monkeypatch):
    good = sorted(known_uids)[0]
    script = Script(
        route=_route("factual_lookup", LOOKUP_QUERY),
        extract=lambda nth: _answer(good, sufficient=nth != 1),
        synthesise="answered on the second pass",
    )
    app, cfg, _, _ = harness(recorded, known_uids, script, monkeypatch)
    out = await app.ainvoke(_state(LOOKUP_Q), cfg)
    assert out["retries"] == 1 and script.seen.count("extract") == 2


async def test_plan_and_execute_reports_the_same_problem_and_does_not_reroute(
    recorded, known_uids, monkeypatch
):
    """One edge is the whole difference between the two architectures (ADR-028)."""
    script = Script(
        route=_route("factual_lookup", LOOKUP_QUERY),
        extract=_answer("deadbeefdeadbeef:99.99"),
        synthesise="answered once",
    )
    app, cfg, calls, _ = harness(recorded, known_uids, script, monkeypatch, plan_and_execute=True)
    out = await app.ainvoke(_state(LOOKUP_Q), cfg)

    assert out["retries"] == 0
    assert script.seen.count("extract") == 1
    assert len(out["violations"]) == 1  # reported, not repaired
    assert [c[0] for c in calls].count("search_notices") == 1


async def test_a_step_ceiling_returns_a_partial_answer_rather_than_raising(
    recorded, known_uids, monkeypatch
):
    """Day 6's contract, and the prep plan's words: a partial result, not an exception."""
    script = Script(
        route=_route("factual_lookup", LOOKUP_QUERY),
        extract=_answer(sorted(known_uids)[0]),
        synthesise="never reached",
    )
    app, cfg, _, _ = harness(recorded, known_uids, script, monkeypatch, budget=Budget(max_steps=2))
    out = await app.ainvoke(_state(LOOKUP_Q), cfg)

    assert out["stopped_by"] == "step_ceiling"
    assert out["answer"].startswith("[stopped by step_ceiling]")
    # No model call is spent to report that the budget is spent.
    assert "synthesise" not in script.seen


async def test_the_recorder_sees_every_call_and_reads_are_not_searches(
    recorded, known_uids, monkeypatch
):
    """Tool-call recall is a claim about what was *read*; crediting a search hit
    would measure BM25 rather than the agent (`record.documents_read`)."""
    script = Script(
        route=_route("factual_lookup", LOOKUP_QUERY),
        extract=_answer(sorted(known_uids)[0]),
        synthesise="answered",
    )
    app, cfg, calls, rec = harness(recorded, known_uids, script, monkeypatch)
    await app.ainvoke(_state(LOOKUP_Q), cfg)

    # The recorder lives on the MCP bridge, which the replay tools bypass, so the
    # graph's own call list is what is asserted here; `test_record.py` covers the
    # bridge. What matters is that the two agree on the shape.
    assert len(calls) == 6
    assert sum(1 for c in calls if c[0] == "search_notices") == 1


async def test_a_tool_call_the_fixture_does_not_hold_fails_loudly(
    recorded, known_uids, monkeypatch
):
    """The property that keeps this suite from passing forever while testing nothing."""
    script = Script(route=_route("factual_lookup", "a query nobody recorded"))
    app, cfg, _, _ = harness(recorded, known_uids, script, monkeypatch)
    with pytest.raises(MissingRecording):
        await app.ainvoke(_state(LOOKUP_Q), cfg)
