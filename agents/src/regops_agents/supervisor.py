"""Router -> workers -> synthesiser, with one budget and one place to stop.

The prep plan asks for a supervisor over `{retriever, obligation-extractor,
gap-analyst, citation-checker}` and then tells you the honest answer is often
that a single well-toolled agent is cheaper. Both halves are taken seriously
here: the graph is real, and `compare.py` runs it against Day 6's single agent on
the same questions and publishes the result whichever way it falls.

Three things this graph does that Day 6's agent could not.

**Arguments are grounded by the graph, not guessed by the model.** See
`workers.py`. It is the structural answer to F1 and F7, which Day 6 left open
with a note saying the fix belonged here.

**A failure is routed, not surrendered.** Two nodes can send a run backwards.
`check` is mechanical -- a dictionary lookup, no model -- and when it finds an
unresolvable citation it returns to `retrieve` once rather than to the user. F5's
finding was that the single agent, handed a tool error naming its own recovery
path, stopped and asked the human; a supervisor can take the path on its behalf,
and that is the clearest thing the extra machinery buys. `approve` does the same
with a *human's* rejection: the reason is a retrieval instruction, so it goes
back into the query rather than into a footnote on the answer.

**Every ceiling lands in the same place.** `_ceiling` is checked at the top of
each node and, when it fires, the run jumps straight to `synthesise` with
`stopped_by` set. The answer is still written, from whatever material was
gathered. Day 6 argued this shape for a step limit -- an agent that has searched
and read two clauses has done real work, and discarding it turns a degraded
answer into no answer -- and a cost ceiling deserves it more, not less.

Written by hand rather than with `langgraph-supervisor` (0.0.31, verified
importable). The three things above are exactly what a prebuilt supervisor owns,
and F12 -- an integration package a major version behind the protocol -- is four
days old. ADR-028 carries the argument and its cost.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from operator import add
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt
from regops_retrieval.index import Index

from regops_agents.budget import (
    Budget,
    merge_findings,
    merge_spend,
    new_spend,
    spent,
    summary,
)
from regops_agents.checkpoint import checkpointer
from regops_agents.llm import MODEL
from regops_agents.mcp_tools import PARSER_RESULT_CHARS, mcp_tools
from regops_agents.workers import (
    COVERAGE_TOP_K,
    TOP_K,
    Toolbox,
    check,
    extract,
    inspect_one,
    retrieve,
    route,
    synthesise,
)

# One retrieval retry after a failed citation check. Two would be a loop with a
# different name: the second retry searches the same corpus with the same query.
MAX_RETRIES = 1

# How many documents a coverage sweep fans out over. Bounded because each branch
# is a model call and, on this hardware, they queue -- see `results/day7/fanout.json`.
FAN_WIDTH = 4


class SupervisorState(TypedDict, total=False):
    """JSON-shaped throughout, because the checkpointer serialises it.

    Two fields carry reducers. `findings` and `spend` are both written by every
    branch of the fan-out in the same super-step; without a reducer that is an
    `InvalidUpdateError`, and with a replacing one it is a silent undercount.
    """

    question: str
    route: str
    query: str
    hits: list[dict]
    context: str
    draft: str
    sufficient: bool
    citations: list[dict]
    violations: list[str]
    findings: Annotated[list[dict], merge_findings]
    approved: bool
    rejected_because: str
    retries: int
    answer: str
    stopped_by: str
    notes: Annotated[list[str], add]
    spend: Annotated[dict, merge_spend]


def _cfg(config: dict) -> tuple[Toolbox, Budget, float, bool]:
    c = config["configurable"]
    return c["toolbox"], c["budget"], c["t0"], c.get("approve", True)


def _ceiling(state: SupervisorState, budget: Budget, t0: float) -> str:
    """Which ceiling has fired, counting wall clock live rather than from state.

    Elapsed time is the one currency a node cannot debit accurately after the
    fact: a worker that blocks for 90s on a queued model call has spent 90s of
    the run's wall clock whether or not it recorded them. So it is measured from
    the run's start every time it is checked.
    """
    live = dict(state.get("spend") or new_spend())
    live["seconds"] = max(live.get("seconds", 0.0), time.perf_counter() - t0)
    return budget.exceeded(live)


# -- nodes -------------------------------------------------------------------


async def node_router(state: SupervisorState, config) -> Command:
    box, budget, t0, _ = _cfg(config)
    if hit := _ceiling(state, budget, t0):
        return Command(goto="synthesise", update={"stopped_by": hit})

    r, cost = route(state["question"], box)
    if r is None:
        return Command(
            goto="retrieve",
            update={
                "route": "factual_lookup",
                "query": state["question"],
                "spend": cost,
                "notes": ["router: unparseable, fell back to the question as its own query"],
            },
        )
    return Command(
        goto="retrieve",
        update={
            "route": r.route,
            "query": r.query or state["question"],
            "spend": cost,
            "notes": [f"router: {r.route} · query={r.query!r}"],
        },
    )


async def node_retrieve(state: SupervisorState, config) -> Command:
    box, budget, t0, _ = _cfg(config)
    if hit := _ceiling(state, budget, t0):
        return Command(goto="synthesise", update={"stopped_by": hit})

    t = time.perf_counter()
    coverage = state.get("route") == "coverage"
    hits, context, warnings = await retrieve(
        state["query"], box, top_k=COVERAGE_TOP_K if coverage else TOP_K
    )
    cost = spent(steps=1, seconds=time.perf_counter() - t)
    note = f"retrieve: {len(hits)} hits, {len(context):,} chars of context"

    update = {"hits": hits, "context": context, "spend": cost, "notes": [*warnings, note]}
    return Command(goto="fan_out" if coverage else "extract", update=update)


async def node_extract(state: SupervisorState, config) -> Command:
    box, budget, t0, _ = _cfg(config)
    if hit := _ceiling(state, budget, t0):
        return Command(goto="synthesise", update={"stopped_by": hit})

    ans, cost = extract(
        state["question"], state.get("context", ""), box, route=state.get("route", "")
    )
    return Command(
        goto="check",
        update={
            "draft": ans.answer if ans else "",
            "sufficient": bool(ans and ans.sufficient),
            "citations": [c.model_dump() for c in ans.citations] if ans else [],
            "spend": cost,
            "notes": [f"extract: {len(ans.citations) if ans else 0} citation(s) claimed"],
        },
    )


async def node_check(state: SupervisorState, config) -> Command:
    """Layer 2: free, mechanical, and one of the two nodes that can reroute."""
    box, budget, t0, _ = _cfg(config)

    from regops_agents.structured import Answer, Citation

    ans = Answer(
        answer=state.get("draft", ""),
        citations=[Citation(**c) for c in state.get("citations", [])],
        sufficient=bool(state.get("sufficient")),
    )
    violations, good = check(ans, box)
    update = {
        "violations": violations,
        "citations": good,
        "notes": [f"check: {len(good)} resolved, {len(violations)} violation(s)"],
    }

    # Two things send a run back, and only one of them is a citation problem.
    # The other is the extractor saying the context did not answer the question,
    # which on this corpus is usually the router's rewritten query missing the
    # clause's wording rather than the corpus being silent. Retrying once with
    # the user's own words is cheap and is the single clearest thing the extra
    # machinery buys: Day 6's agent, handed a recovery path, asked the human.
    reason = ""
    if violations:
        reason = "unresolved citation"
    elif not state.get("sufficient"):
        reason = "context did not answer the question"

    retries = state.get("retries", 0)
    if reason and retries < MAX_RETRIES and not _ceiling(state, budget, t0):
        return Command(
            goto="retrieve",
            update={
                **update,
                "retries": retries + 1,
                "query": state["question"],
                "notes": [*update["notes"], f"check: rerouting to retrieve — {reason}"],
            },
        )
    return Command(goto="synthesise", update=update)


def node_fan_out(state: SupervisorState, config) -> Command:
    """The only genuinely independent subtasks in this graph.

    One document per branch, one context window per branch, no shared
    intermediate. If parallel fan-out earns its keep anywhere here it is here --
    which is why the measurement is taken on this node and nowhere else.

    Hits are grouped by document rather than deduplicated down to one. A coverage
    sweep asks whether a *document* addresses a topic, and the retriever usually
    matched several of its clauses; keeping all of them is the difference between
    asking that question and asking whether one arbitrary clause happens to
    answer it.
    """
    grouped: dict[str, dict] = {}
    for h in state.get("hits", []):
        doc = grouped.setdefault(
            h["doc_id"],
            {
                "doc_id": h["doc_id"],
                "title": h.get("title", ""),
                "excerpt": h.get("snippet", ""),
                "hits": [],
            },
        )
        doc["hits"].append(h)

    docs = list(grouped.values())[:FAN_WIDTH]
    sends = [Send("inspect", {"topic": state["question"], "doc": d}) for d in docs]
    # A `Command` whose `goto` is a list of `Send`s *is* the fan-out. Doing it
    # here rather than in a conditional edge keeps every routing decision in this
    # module in one shape, which matters more than it sounds: a graph that routes
    # two different ways is a graph where the second way gets forgotten.
    return Command(
        goto=sends or ["synthesise"],
        update={"notes": [f"fan_out: {len(sends)} branch(es)"]},
    )


async def node_inspect(payload: dict, config) -> dict:
    """One fan-out branch. Receives the `Send` payload, not the graph state."""
    box, _, _, _ = _cfg(config)
    doc = payload["doc"]
    finding, cost = await inspect_one(payload["topic"], doc, box)
    return {
        "findings": [
            {
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "covered": bool(finding and finding.covered),
                "section_path": finding.section_path if finding else "",
                "quote": finding.quote if finding else "",
            }
        ],
        "spend": cost,
    }


def node_check_findings(state: SupervisorState, config) -> Command:
    """Layer 2 on the coverage path, which otherwise never meets it.

    A coverage finding is a citation: *this document covers the topic, at clause
    8.2*. The first version of this graph carried those straight to the answer
    without checking them, so the coverage route was the one path on which a
    claim could reach a reader unverified -- and it is also the path whose answer
    a compliance officer is most likely to act on, because it names documents.

    Free, mechanical, and it downgrades rather than rejects: a finding whose
    clause does not resolve becomes an uncovered one with the violation recorded,
    which is the conservative direction. Claiming coverage that cannot be looked
    up is the failure worth avoiding; missing coverage is visible to anyone who
    reads the document.
    """
    box, _, _, _ = _cfg(config)
    kept, violations = [], []
    for f in state.get("findings", []):
        if f["covered"] and box.clause(f["doc_id"], f["section_path"]) is None:
            violations.append(
                f"reference: ({f['doc_id']}, {f['section_path']}) is not in the index"
            )
            kept.append({**f, "covered": False, "unverified": True})
        else:
            kept.append(f)

    covered = [f for f in kept if f["covered"]]
    return Command(
        goto="approve",
        update={
            "findings": None if not kept else [*kept],
            "citations": [
                {"doc_id": f["doc_id"], "section_path": f["section_path"]} for f in covered
            ],
            "violations": violations,
            "notes": [f"check: {len(covered)} verified, {len(violations)} unverifiable"],
        },
    )


def node_approve(state: SupervisorState, config) -> Command:
    """Human in the loop, and the reason `interrupt()` is the first statement.

    Measured: the body of an interrupting node runs **twice** for one logical
    visit -- once on the interrupting pass and once on resume, because
    `interrupt()` replays its node from the top. Anything expensive placed above
    this line is billed twice, silently. That is F13, and
    `test_checkpoint.py::test_the_interrupting_node_body_runs_once_per_logical_visit`
    is what keeps this comment from being only a comment.
    """
    _, _, _, approve = _cfg(config)
    if not approve:
        return Command(goto="synthesise", update={"approved": True, "notes": ["approve: skipped"]})

    covered = [f for f in state.get("findings", []) if f["covered"]]
    decision = interrupt(
        {
            "question": state["question"],
            "covered": [f"{f['title'][:60]} · {f['section_path']}" for f in covered],
            "silent": [f["title"][:60] for f in state.get("findings", []) if not f["covered"]],
            "ask": "approve this coverage report? reply 'approve' or a reason to reject",
        }
    )
    ok = str(decision).strip().lower() in {"approve", "approved", "yes", "y"}
    if ok:
        return Command(
            goto="synthesise",
            update={"approved": True, "notes": ["approve: approved"]},
        )

    # A rejection that only annotates the answer is a confirmation dialog with
    # extra steps. The reason is a *retrieval* instruction -- "you missed the
    # trust companies notice" is a query -- so it goes back into the sweep once,
    # appended to the search text. Bounded by the same retry counter as the
    # citation check, because a reviewer who keeps rejecting is a conversation,
    # not a loop the graph should run on its own.
    retries = state.get("retries", 0)
    reason = str(decision)
    if retries < MAX_RETRIES:
        return Command(
            goto="retrieve",
            update={
                "approved": False,
                "rejected_because": reason,
                "retries": retries + 1,
                "query": f"{state.get('query', state['question'])} {reason}",
                "findings": None,
                "notes": [f"approve: rejected — {reason}; re-running the sweep"],
            },
        )
    return Command(
        goto="synthesise",
        update={
            "approved": False,
            "rejected_because": reason,
            "notes": [f"approve: rejected again — {reason}; answering with what there is"],
        },
    )


async def node_synthesise(state: SupervisorState, config) -> dict:
    """The one exit. Everything that stops early stops here, with an answer."""
    box, budget, t0, _ = _cfg(config)
    stopped = state.get("stopped_by", "")

    findings = state.get("findings", [])
    extra = ""
    if findings:
        lines = [
            f"- {f['title'][:70]}: "
            + (f"covers it at clause {f['section_path']}" if f["covered"] else "silent")
            for f in findings
        ]
        extra = "COVERAGE SWEEP\n" + "\n".join(lines)
    if state.get("rejected_because"):
        extra += f"\n\nA reviewer rejected the draft: {state['rejected_because']}"

    if stopped:
        # No further model call once a ceiling has fired -- that would spend past
        # the budget to report that the budget was spent.
        gathered = state.get("draft") or extra or "no material was gathered"
        answer = f"[stopped by {stopped}] {gathered}"
        return {"answer": answer, "stopped_by": stopped}

    text, cost = synthesise(
        state["question"], state.get("draft", ""), state.get("citations", []), box, extra
    )
    hit = _ceiling({"spend": merge_spend(state.get("spend"), cost)}, budget, t0)
    return {
        "answer": text,
        "spend": cost,
        "stopped_by": hit,
        "notes": [f"synthesise: {len(text):,} chars"],
    }


# -- the graph ---------------------------------------------------------------


def build(*, plan_and_execute: bool = False):
    """The supervisor. `plan_and_execute=True` is Phase 5's variant, not a mode.

    The difference is one edge: the supervisor re-consults `check` and may send
    the run back to `retrieve`; the plan-and-execute variant commits to the
    router's plan and runs it through once. Everything else -- workers, prompts,
    budget, ceilings -- is identical, so the comparison is of the control flow and
    not of two implementations that happen to differ everywhere.
    """
    g = StateGraph(SupervisorState)
    g.add_node("router", node_router, destinations=("retrieve", "synthesise"))
    g.add_node("retrieve", node_retrieve, destinations=("extract", "fan_out", "synthesise"))
    g.add_node("extract", node_extract, destinations=("check", "synthesise"))
    g.add_node(
        "check",
        node_check if not plan_and_execute else _check_once,
        destinations=("retrieve", "synthesise"),
    )
    g.add_node("fan_out", node_fan_out, destinations=("inspect", "synthesise"))
    g.add_node("inspect", node_inspect)
    g.add_node("check_findings", node_check_findings, destinations=("approve",))
    g.add_node("approve", node_approve, destinations=("retrieve", "synthesise"))
    g.add_node("synthesise", node_synthesise)

    g.add_edge(START, "router")
    g.add_edge("inspect", "check_findings")
    g.add_edge("synthesise", END)
    return g


async def _check_once(state: SupervisorState, config) -> Command:
    """Plan-and-execute's checker: reports, never reroutes."""
    box, _, _, _ = _cfg(config)
    from regops_agents.structured import Answer, Citation

    ans = Answer(
        answer=state.get("draft", ""),
        citations=[Citation(**c) for c in state.get("citations", [])],
        sufficient=bool(state.get("sufficient")),
    )
    violations, good = check(ans, box)
    return Command(
        goto="synthesise",
        update={
            "violations": violations,
            "citations": good,
            "notes": [f"check (plan-and-execute): {len(good)} resolved, no reroute"],
        },
    )


# -- running one ------------------------------------------------------------


@asynccontextmanager
async def running(
    index: Path,
    *,
    model: str = MODEL,
    budget: Budget | None = None,
    plan_and_execute: bool = False,
    persist: bool = False,
    approve: bool = True,
) -> AsyncIterator[tuple]:
    """Everything a run needs, opened once and closed once.

    The MCP server is a subprocess and the DuckDB handle is a file lock, so both
    are held for the life of the caller rather than per question. A benchmark
    that reopened them per item would be measuring process startup -- which on
    the MCP side is a `uv run` of a second project.

    `persist=False` uses an in-memory saver. That is the right default for the
    comparison harness: Postgres is being proved by the resume test, and paying
    a round trip per super-step inside a wall-clock measurement would put the
    database in a number that is about the model.
    """
    graph = build(plan_and_execute=plan_and_execute)
    ix = Index(index)
    try:
        async with (
            # The graph parses tool results and compacts them itself, so it takes
            # them whole. The model-facing cap stays where Day 6 put it, on the
            # agent that puts raw results into a prompt. See F14.
            mcp_tools(index, max_result_chars=PARSER_RESULT_CHARS) as tools,
            checkpointer(required=persist) as saver,
        ):
            box = Toolbox(index=index, tools={t.name: t for t in tools}, ix=ix, model=model)
            app = graph.compile(checkpointer=saver)

            def config(thread: str) -> dict:
                return {
                    "configurable": {
                        "toolbox": box,
                        "budget": budget or Budget(),
                        "t0": time.perf_counter(),
                        "approve": approve,
                        "thread_id": thread,
                    },
                    # The graph's own limit, well above the budget's step ceiling,
                    # so that the *budget* is what stops a run and F9 -- a framework
                    # ceiling that neither raises nor reports -- cannot fire first.
                    "recursion_limit": 60,
                }

            yield app, config
    finally:
        ix.close()


async def ask(
    app,
    config,
    question: str,
    *,
    thread: str | None = None,
) -> dict:
    """One question through the graph. Returns state plus what it cost.

    Never raises on a ceiling -- that is the contract Day 6 established and the
    prep plan asks for in as many words: *"a partial result returned rather than
    an exception"*.
    """
    thread = thread or f"q-{time.time_ns()}"
    cfg = config(thread)
    t0 = time.perf_counter()
    state = {
        "question": question,
        "spend": new_spend(),
        "retries": 0,
        "findings": [],
        "notes": [],
    }
    out = await app.ainvoke(state, cfg)
    out["thread_id"] = thread
    out["wall_seconds"] = round(time.perf_counter() - t0, 3)
    out["cost"] = summary(out.get("spend") or new_spend(), cfg["configurable"]["budget"])
    return out
