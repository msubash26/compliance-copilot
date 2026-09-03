"""Persistence that has never been read back by another process is a cache.

These tests spawn real interpreters. `sys.executable` inside `uv run pytest` is
the workspace venv's python, so the child resolves the same packages without a
`uv run` of its own.

Both tests skip without `CHECKPOINTER_DSN`. That is deliberate rather than
regrettable: CI has no Postgres, and a test that silently passes against an
in-memory saver would be asserting nothing at all -- the run would "survive"
only because it never left the process.
"""

from __future__ import annotations

import subprocess
import sys
import time

import pytest
from regops_agents.checkpoint import checkpointer, dsn

needs_postgres = pytest.mark.skipif(not dsn(), reason="CHECKPOINTER_DSN is not set")

# A three-node graph that interrupts in the middle, written to a temp file and
# run twice. `interrupt()` is the *first* statement of `review` -- the placement
# rule the double-execution measurement forced (F13) -- and the body after it
# appends to `PROBE_COUNTER` so the second test can count logical visits.
PROBE = """
import os, sys
from typing import Annotated, TypedDict
from operator import add
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.postgres import PostgresSaver

COUNTER = os.environ["PROBE_COUNTER"]

class S(TypedDict):
    steps: Annotated[list[str], add]
    verdict: str

def draft(s):
    return {"steps": ["draft"]}

def review(s):
    decision = interrupt({"ask": "approve?"})
    with open(COUNTER, "a") as fh:
        fh.write("body\\n")
    return {"steps": ["review"], "verdict": decision}

def finalise(s):
    return {"steps": ["finalise:" + s["verdict"]]}

g = StateGraph(S)
for name, fn in (("draft", draft), ("review", review), ("finalise", finalise)):
    g.add_node(name, fn)
g.add_edge(START, "draft")
g.add_edge("draft", "review")
g.add_edge("review", "finalise")
g.add_edge("finalise", END)

mode, thread = sys.argv[1], sys.argv[2]
with PostgresSaver.from_conn_string(os.environ["CHECKPOINTER_DSN"]) as cp:
    app = g.compile(checkpointer=cp)
    cfg = {"configurable": {"thread_id": thread}}
    if mode == "start":
        app.invoke({"steps": [], "verdict": ""}, cfg)
        print("PENDING", app.get_state(cfg).next[0])
    else:
        print("PENDING", app.get_state(cfg).next[0])
        out = app.invoke(Command(resume="approved"), cfg)
        print("FINAL", ",".join(out["steps"]), out["verdict"])
"""


def _run(script, mode, thread, counter, env_extra=None):
    import os

    env = {**os.environ, "PROBE_COUNTER": str(counter), "CHECKPOINTER_DSN": dsn()}
    env.update(env_extra or {})
    proc = subprocess.run(
        [sys.executable, str(script), mode, thread],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    return proc.stdout


@pytest.fixture
def probe(tmp_path):
    script = tmp_path / "probe.py"
    script.write_text(PROBE)
    return script, tmp_path / "counter.txt"


@needs_postgres
def test_a_run_interrupted_in_one_process_resumes_in_another(probe):
    """The prep plan's bullet, taken literally: nothing is shared but Postgres."""
    script, counter = probe
    thread = f"t-{time.time_ns()}"

    started = _run(script, "start", thread, counter)
    assert "PENDING review" in started

    # A different interpreter. The first one has exited; no state is in memory.
    resumed = _run(script, "resume", thread, counter)
    assert "PENDING review" in resumed
    assert "FINAL draft,review,finalise:approved approved" in resumed


@needs_postgres
def test_the_interrupting_node_body_runs_once_per_logical_visit(probe):
    """The regression guard for F13, and the reason `interrupt()` goes first.

    `interrupt()` replays its node from the top on resume. Measured: a body
    placed *before* the interrupt executes twice for one logical visit. On a
    node that calls a model that is a second inference bill, silently, and any
    non-idempotent side effect happens twice.

    Here the body is *after* the interrupt, so it must run exactly once. If a
    later refactor moves work above the `interrupt()` call, this fails -- which
    is the only thing standing between the rule and a comment.
    """
    script, counter = probe
    thread = f"t-{time.time_ns()}"
    _run(script, "start", thread, counter)
    _run(script, "resume", thread, counter)
    assert counter.read_text().count("body") == 1


async def test_without_a_dsn_the_checkpointer_is_in_memory_and_says_so(monkeypatch):
    """The CI path. `required=True` must refuse rather than quietly degrade."""
    monkeypatch.setenv("CHECKPOINTER_DSN", "")
    monkeypatch.setattr("regops_agents.checkpoint.dsn", lambda: "")

    async with checkpointer() as cp:
        assert type(cp).__name__ == "InMemorySaver"

    with pytest.raises(RuntimeError, match="needs real persistence"):
        async with checkpointer(required=True):
            pass
