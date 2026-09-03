"""Did instrumenting the agents change them?

Risk 5 of the Day 8 plan: *instrumenting every tool call changes the thing being
measured*. The overhead is not the worry -- research 2 measured 0.8 ms for four
spans against a 5.9s run -- the worry is behaviour. A recorder that appends a dict
per call cannot plausibly change an answer, and "cannot plausibly" is exactly the
kind of claim this project has been wrong about before (F15 was a shared DuckDB
connection that returned one caller's rows to another, and nothing about that was
plausible either).

So it is checked rather than argued. Two eval artifacts, produced by two separate
processes, are compared item by item on **everything the metrics read**: route,
citations, documents read, steps, tokens and the answer text itself. Latency is
excluded because it is the one quantity that legitimately moves -- research 1
measured a 6.5% spread across four runs whose outputs were byte-identical.

**The bar is zero.** Not "close": research 1 established that this pipeline is
exactly deterministic across process boundaries -- 0 of 10 items differed and the
token total was identical to the digit at 39,737. That is what temperature 0,
`think: false`, constrained decoding and two ranking-determinism fixes (ADR-022
here, ADR-008 in `regdocs-mcp`) bought, and it is also what makes the gate able to
be exact rather than banded. **If instrumentation moved a single answer, that is a
bug and not a cost.**

**It also answers a question nobody asked.** Run over more than one arm, this
compares the *architectures* on reproducibility, and they do not compare: on the
same thirty tasks across two processes the supervisor moved **0 of 30** items and
Day 6's ReAct agent moved **25 of 30**, including its step count, its tool calls,
and on one task whether it succeeded at all. Both run at temperature 0. The graph
asks for a small typed answer through constrained decoding on every call; the ReAct
agent generates free-form text over the full vocabulary and lets the framework
parse it. That is the most likely cause and it is a hypothesis, not a measurement
-- what *is* measured is that only one of these two arms can be gated exactly, and
it is the one the gate gates.
"""

from __future__ import annotations

import json
from pathlib import Path

# What must match. `seconds`, `usd` and anything derived from the clock are out:
# they are a fact about Ollama's queue rather than about the agent.
COMPARED = (
    "route",
    "answer",
    "cited_uids",
    "asserted",
    "unresolvable",
    "docs_read",
    "n_tool_calls",
    "steps",
    "in_tokens",
    "out_tokens",
    "stopped_by",
    "abstained",
    "success",
)


def diff_rows(a: dict, b: dict) -> list[str]:
    return [f for f in COMPARED if a.get(f) != b.get(f)]


def compare(left: Path, right: Path, *, arm: str = "supervisor") -> dict:
    la = json.loads(Path(left).read_text())
    lb = json.loads(Path(right).read_text())
    rows_a = {r["task_id"]: r for r in la.get("rows", {}).get(arm, [])}
    rows_b = {r["task_id"]: r for r in lb.get("rows", {}).get(arm, [])}
    shared = sorted(set(rows_a) & set(rows_b))

    differing = []
    for tid in shared:
        fields = diff_rows(rows_a[tid], rows_b[tid])
        if fields:
            differing.append({"task_id": tid, "fields": fields})

    ma = la.get("metrics", {}).get(arm, {})
    mb = lb.get("metrics", {}).get(arm, {})
    return {
        "arm": arm,
        "left": str(left),
        "right": str(right),
        "compared_fields": list(COMPARED),
        "items": len(shared),
        "only_in_left": sorted(set(rows_a) - set(rows_b)),
        "only_in_right": sorted(set(rows_b) - set(rows_a)),
        "differing": differing,
        "identical": not differing and not (set(rows_a) ^ set(rows_b)),
        "tokens": [ma.get("cost", {}).get("tokens"), mb.get("cost", {}).get("tokens")],
        "steps_identical": ma.get("trajectory") == mb.get("trajectory"),
        # The one thing allowed to move, reported so the spread is visible.
        "p50_s": [ma.get("latency", {}).get("p50_s"), mb.get("latency", {}).get("p50_s")],
    }


def run_determinism(
    left: Path,
    right: Path,
    *,
    arms: tuple[str, ...] = ("supervisor",),
    gated: str = "supervisor",
    out: Path | None = None,
) -> int:
    """Compare every named arm. Only the gated one's verdict decides the exit code.

    The others are measured because the comparison is free once both runs exist,
    and because "which architecture can be gated exactly" turns out to be a real
    question with a real answer.
    """
    report = {"gated_arm": gated, "arms": {}}
    for arm in arms:
        rep = compare(left, right, arm=arm)
        report["arms"][arm] = rep
        print(
            f"determinism · arm '{arm}' · {rep['items']} items compared on {len(COMPARED)} fields"
        )
        for row in rep["differing"]:
            print(f"    {row['task_id']}  differs in {', '.join(row['fields'])}")
        for tid in rep["only_in_left"] + rep["only_in_right"]:
            print(f"    {tid}  present in only one run")
        ta, tb = rep["tokens"]
        pa, pb = rep["p50_s"]
        print(f"    tokens   {ta:,} vs {tb:,}" if ta and tb else f"    tokens   {ta} vs {tb}")
        if pa and pb:
            print(f"    p50      {pa:.2f}s vs {pb:.2f}s  ({(pb - pa) / pa:+.1%}, not compared)")
        verdict = (
            f"IDENTICAL: {rep['items']}/{rep['items']} items match on every compared field."
            if rep["identical"]
            else f"DIFFERENT: {len(rep['differing'])} of {rep['items']} items moved."
        )
        print(f"    {verdict}\n")

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"-> {out}")
    return 0 if report["arms"].get(gated, {}).get("identical") else 1
