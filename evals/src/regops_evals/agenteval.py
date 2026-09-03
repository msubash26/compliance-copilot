"""Five metrics over three agent architectures, on thirty derived tasks.

Days 6 and 7 measured two agents once each. This makes the measurement
repeatable and mechanical, which is a different thing and the harder one: a
number in a write-up is a claim about a day, and a gate is a claim about every
day after it.

**Every metric is defined here before it is computed.** A metric bug shows up as
a good number, consistently, in every cell, and nothing downstream can detect it
(`metrics.py` makes the same argument about ranking).

1. **Task success** -- four mechanical outcomes, every one derived from the golden
   set rather than asserted here, plus the composite that requires all of them.
   Reported both ways, because the composite is what the gate needs and the four
   are what a person needs in order to fix anything.

   - `retrieved_gold` -- the agent *read* every gold document. Reading, not
     retrieving: a `doc_id` that appeared in a search result was offered to the
     agent, not used by it, and crediting that measures BM25.
   - `cited_resolvable` -- it cited at least one clause that resolves against the
     index (Day 6's layer 2). Required of every grounded task.
   - `abstained_correctly` -- it declined on the five tasks the corpus does not
     answer, and did not decline on the twenty-five it does. Two rates, not one:
     ADR-021's point is that false abstention and false answering are different
     failures and a single "accuracy" averages them into nothing.
   - `within_budget` -- it finished rather than hitting a ceiling.

2. **Tool-call precision and recall** against `gold_doc_ids`. Recall is *did it
   read the gold document*; precision is *what fraction of what it read was
   gold*. Precision is reported and not gated: a coverage-shaped question makes a
   supervisor read four documents on purpose, and a metric that punishes breadth
   would gate the architecture rather than the regression.

3. **Trajectory efficiency** -- `min_tool_calls / actual`, capped at 1.0, with the
   raw pair kept beside it. A 0.5 from two calls instead of one is a different
   animal from a 0.5 from twelve instead of six, and the ratio alone cannot tell
   them apart. The floor comes from the golden set (`tasks.min_tool_calls`), not
   from a guess.

4. **Cost per task** -- tokens, which are exact, and the ADR-029 dollar
   conversion, which is an assumed rate on a machine with no per-token price.
   The write-up leads with tokens for that reason.

5. **Latency** -- p50, p95 and max, with `n` printed beside them. p95 over thirty
   tasks is a single order statistic and is reported, never gated. Re-running does
   not tighten it either: the outputs of this pipeline are byte-identical across
   processes (`--determinism`), so a repeat resamples only Ollama's queue, which
   is a fact about the server rather than about the agent.

**Abstention is decided textually, and that is stated rather than hidden.**
`REFUSAL` below is a list of markers, and `abstained` is true when one matches or
when the answer cites nothing at all. It is the weakest mechanism in this module.
It is kept mechanical anyway -- the alternative is asking the judge, and then the
gate depends on a model's opinion. Both signals are recorded per row so that a
disagreement between them is visible instead of averaged away.

**What is gated and what is not.** Decision 2 of the Day 8 plan: all three arms
are measured, only the supervisor is gated. Measuring the other two keeps Day 7's
comparison alive as a regression surface for free; gating them triples the ways a
build can fail for reasons nobody is working on.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from regops_agents.architectures import cited_pairs
from regops_agents.budget import Budget, new_spend, summary, usd
from regops_agents.llm import MODEL
from regops_agents.record import Recorder
from regops_agents.trace import tracer
from regops_retrieval.index import Index

from regops_evals.gate_agent import tasks_sha
from regops_evals.prompts import stamp
from regops_evals.tasks import COVERAGE_TASKS, Task, read_tasks

ARMS = ("single_agent", "supervisor", "plan_and_execute")

# The arm the gate enforces. See the module docstring.
GATED_ARM = "supervisor"

# Textual abstention markers. Lower-cased substring match, deliberately narrow:
# a marker that fires on "the notice does not apply to banks" would score a
# correct grounded answer as a refusal.
REFUSAL = (
    "does not contain",
    "does not address",
    "does not cover",
    "do not contain",
    "do not address",
    "does not answer",
    "not addressed in the corpus",
    "no clause",
    "no provision",
    "could not find",
    "cannot be answered",
    "is not answered",
    "unable to find",
    "corpus does not",
    "material does not answer",
    "not stated in the",
)


def looks_like_refusal(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in REFUSAL)


@dataclass
class Row:
    """One task, through one arm. Everything a metric or a judge needs, and no state."""

    arm: str
    task_id: str
    golden_id: str
    query_type: str
    question: str
    gold_answer: str
    gold_doc_ids: list[str]
    gold_uids: list[str]
    must_cite: bool
    must_abstain: bool
    min_tool_calls: int

    answer: str = ""
    route: str = ""
    cited_uids: list[str] = field(default_factory=list)  # resolvable, in the index
    asserted: int = 0  # everything it claimed, resolvable or not
    unresolvable: int = 0
    docs_read: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    n_tool_calls: int = 0
    steps: int = 0
    seconds: float = 0.0
    in_tokens: int = 0
    out_tokens: int = 0
    tokens: int = 0
    usd: float = 0.0
    stopped_by: str = ""
    refusal_marker: bool = False
    abstained: bool = False
    error: str = ""

    # -- the four mechanical outcomes ---------------------------------------

    @property
    def retrieved_gold(self) -> bool:
        """Every gold document read in full. Negatives have none, and pass."""
        return set(self.gold_doc_ids) <= set(self.docs_read)

    @property
    def cited_resolvable(self) -> bool:
        return (not self.must_cite) or bool(self.cited_uids)

    @property
    def abstained_correctly(self) -> bool:
        return self.abstained == self.must_abstain

    @property
    def within_budget(self) -> bool:
        return not self.stopped_by and not self.error

    @property
    def success(self) -> bool:
        return (
            self.retrieved_gold
            and self.cited_resolvable
            and self.abstained_correctly
            and self.within_budget
        )

    # -- trajectory ----------------------------------------------------------

    @property
    def efficiency(self) -> float:
        """`min / actual`, capped at 1.0. Zero calls is zero efficiency, not infinite."""
        if not self.n_tool_calls:
            return 0.0
        return round(min(1.0, self.min_tool_calls / self.n_tool_calls), 4)

    @property
    def tool_recall(self) -> float | None:
        if not self.gold_doc_ids:
            return None
        return round(len(set(self.gold_doc_ids) & set(self.docs_read)) / len(self.gold_doc_ids), 4)

    @property
    def tool_precision(self) -> float | None:
        if not self.docs_read or not self.gold_doc_ids:
            return None
        return round(len(set(self.gold_doc_ids) & set(self.docs_read)) / len(self.docs_read), 4)

    def to_json(self) -> dict:
        d = asdict(self)
        d |= {
            "retrieved_gold": self.retrieved_gold,
            "cited_resolvable": self.cited_resolvable,
            "abstained_correctly": self.abstained_correctly,
            "within_budget": self.within_budget,
            "success": self.success,
            "efficiency": self.efficiency,
            "tool_recall": self.tool_recall,
            "tool_precision": self.tool_precision,
        }
        # The full call list is kept out of the artifact: thirty tasks times three
        # arms times a dozen calls is a diff nobody reads, and the derived columns
        # above are what the gate compares. `--calls` writes them separately.
        d.pop("tool_calls")
        return d


def _blank(task: Task, arm: str) -> Row:
    return Row(
        arm=arm,
        task_id=task.task_id,
        golden_id=task.golden_id,
        query_type=task.query_type,
        question=task.question,
        gold_answer=task.gold_answer,
        gold_doc_ids=list(task.gold_doc_ids),
        gold_uids=list(task.gold_uids),
        must_cite=task.must_cite,
        must_abstain=task.must_abstain,
        min_tool_calls=task.min_tool_calls,
    )


def _finish(row: Row, ix: Index, pairs: list[tuple[str, str]]) -> Row:
    """Layer 2 and the abstention decision, applied identically to every arm."""
    resolved, bad = [], 0
    for doc, sec in pairs:
        uid = f"{doc}:{sec}"
        if sec and ix.clause_by_uid(uid) is not None:
            if uid not in resolved:
                resolved.append(uid)
        else:
            bad += 1
    row.cited_uids = resolved
    row.asserted = len(pairs)
    row.unresolvable = bad
    row.refusal_marker = looks_like_refusal(row.answer)
    row.abstained = row.refusal_marker or not pairs
    row.tokens = row.in_tokens + row.out_tokens
    row.usd = usd({"in_tokens": row.in_tokens, "out_tokens": row.out_tokens})
    row.n_tool_calls = len(row.tool_calls)
    return row


# -- the three arms ----------------------------------------------------------


async def run_single(tasks: list[Task], index: Path, model: str, budget: Budget, ix: Index, trc):
    """Day 6's ReAct agent, unchanged, over the same MCP server and the same recorder."""
    from regops_agents.agent import ask, build_agent
    from regops_agents.mcp_tools import mcp_tools

    rec = Recorder()
    rows: list[Row] = []
    async with mcp_tools(index, recorder=rec, tracer=trc) as tools:
        agent = build_agent(tools, model=model)
        for i, t in enumerate(tasks, 1):
            rec.reset(t.task_id)
            row = _blank(t, "single_agent")
            t0 = time.perf_counter()
            with trc.trace(f"single_agent · {t.task_id}", input={"question": t.question}) as root:
                r = await ask(agent, t.question, max_steps=budget.max_steps)
                root.update(output={"answer": r.answer[:2000]})
            row.answer = r.answer
            row.steps = r.steps
            row.seconds = round(time.perf_counter() - t0, 2)
            row.stopped_by = r.stopped_by
            row.error = r.error
            # LangChain reports usage on the AI messages; summing them is the
            # only way this arm gets a token column at all.
            for m in r.messages:
                u = getattr(m, "usage_metadata", None) or {}
                row.in_tokens += int(u.get("input_tokens", 0))
                row.out_tokens += int(u.get("output_tokens", 0))
            row.tool_calls = rec.snapshot()
            row.docs_read = rec.documents_read()
            rows.append(_finish(row, ix, cited_pairs(r.answer)))
            _line(i, len(tasks), rows[-1])
    return rows


async def run_graph(
    tasks: list[Task],
    index: Path,
    model: str,
    budget: Budget,
    ix: Index,
    trc,
    *,
    plan_and_execute: bool,
):
    from regops_agents.supervisor import ask, running

    arm = "plan_and_execute" if plan_and_execute else "supervisor"
    rec = Recorder()
    rows: list[Row] = []
    async with running(
        index,
        model=model,
        budget=budget,
        plan_and_execute=plan_and_execute,
        approve=False,  # unattended; the interrupt is proved in `test_checkpoint.py`
        recorder=rec,
        tracer=trc,
    ) as (app, config):
        for i, t in enumerate(tasks, 1):
            rec.reset(t.task_id)
            row = _blank(t, arm)
            out = await ask(app, config, t.question, trace_name=f"{arm} · {t.task_id}")
            cost = out.get("cost") or summary(new_spend(), budget)
            row.answer = out.get("answer", "")
            row.route = out.get("route", "")
            row.steps = int(cost.get("steps", 0))
            row.seconds = float(out.get("wall_seconds", 0.0))
            row.in_tokens = int(cost.get("in_tokens", 0))
            row.out_tokens = int(cost.get("out_tokens", 0))
            row.stopped_by = out.get("stopped_by", "") or ""
            row.tool_calls = rec.snapshot()
            row.docs_read = rec.documents_read()
            # The graph's citations are already layer-2 filtered, so what it
            # *asserted* is those plus what `check` rejected. Reporting only the
            # survivors would score a strict architecture as if it never erred.
            pairs = [(c["doc_id"], c["section_path"]) for c in (out.get("citations") or [])]
            row = _finish(row, ix, pairs)
            row.unresolvable = len(out.get("violations") or [])
            row.asserted += row.unresolvable
            rows.append(row)
            _line(i, len(tasks), rows[-1])
    return rows


def _line(i: int, n: int, r: Row) -> None:
    flag = f"  {r.stopped_by}" if r.stopped_by else ""
    print(
        f"  [{i:>2}/{n}] {r.task_id} {r.query_type[:12]:<12} {r.steps:>2}st "
        f"{r.n_tool_calls:>2}tc {r.seconds:>6.1f}s {r.tokens:>6,}tok "
        f"cite {len(r.cited_uids)}({r.unresolvable} bad) "
        f"{'GOLD' if r.retrieved_gold else '----'} "
        f"{'ABS' if r.abstained else '   '} "
        f"{'OK' if r.success else 'FAIL'}{flag}",
        flush=True,
    )


# -- scoring -----------------------------------------------------------------


def _pct(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def score(rows: list[Row]) -> dict:
    """Every metric in the docstring, over one arm's rows. Counts beside rates."""
    n = len(rows)
    grounded = [r for r in rows if not r.must_abstain]
    negatives = [r for r in rows if r.must_abstain]
    secs = sorted(r.seconds for r in rows)

    def p(q: float) -> float:
        if not secs:
            return 0.0
        return round(secs[min(len(secs) - 1, int(q * len(secs)))], 2)

    recalls = [r.tool_recall for r in grounded if r.tool_recall is not None]
    precisions = [r.tool_precision for r in grounded if r.tool_precision is not None]

    return {
        "n": n,
        "success": {
            "composite": {"passed": sum(r.success for r in rows), "n": n},
            "retrieved_gold": {"passed": sum(r.retrieved_gold for r in rows), "n": n},
            "cited_resolvable": {"passed": sum(r.cited_resolvable for r in rows), "n": n},
            "abstained_correctly": {"passed": sum(r.abstained_correctly for r in rows), "n": n},
            "within_budget": {"passed": sum(r.within_budget for r in rows), "n": n},
            "rate": _pct(sum(r.success for r in rows), n),
        },
        # Two rates, never one. ADR-021: refusing a question you have the clause
        # for and answering one you do not are different failures.
        "abstention": {
            "false_abstention": {
                "n": len(grounded),
                "count": sum(r.abstained for r in grounded),
                "rate": _pct(sum(r.abstained for r in grounded), len(grounded)),
            },
            "false_answer": {
                "n": len(negatives),
                "count": sum(not r.abstained for r in negatives),
                "rate": _pct(sum(not r.abstained for r in negatives), len(negatives)),
            },
        },
        "tool_calls": {
            "recall_mean": round(statistics.mean(recalls), 4) if recalls else None,
            "precision_mean": round(statistics.mean(precisions), 4) if precisions else None,
            "gold_fully_read": {
                "passed": sum(r.retrieved_gold for r in grounded),
                "n": len(grounded),
            },
            "calls_total": sum(r.n_tool_calls for r in rows),
            "errors": sum(sum(1 for c in r.tool_calls if c["error"]) for r in rows),
        },
        "trajectory": {
            "efficiency_mean": (
                round(statistics.mean([r.efficiency for r in rows]), 4) if n else None
            ),
            "min_total": sum(r.min_tool_calls for r in rows),
            "actual_total": sum(r.n_tool_calls for r in rows),
        },
        "citations": {
            "resolvable": sum(len(r.cited_uids) for r in rows),
            "asserted": sum(r.asserted for r in rows),
            "unresolvable": sum(r.unresolvable for r in rows),
        },
        "cost": {
            "tokens": sum(r.tokens for r in rows),
            "in_tokens": sum(r.in_tokens for r in rows),
            "out_tokens": sum(r.out_tokens for r in rows),
            "tokens_per_task": round(sum(r.tokens for r in rows) / n, 1) if n else None,
            "usd": round(sum(r.usd for r in rows), 6),
            "usd_note": "ADR-029: an assumed rate, not a quote. This box has no per-token price.",
        },
        # p95 over thirty tasks is one order statistic. Reported with n, never gated.
        "latency": {
            "n": n,
            "p50_s": p(0.50),
            "p95_s": p(0.95),
            "max_s": round(max(secs), 2) if secs else 0.0,
            "total_s": round(sum(secs), 1),
        },
        "stopped_by": {
            k: sum(1 for r in rows if r.stopped_by == k)
            for k in sorted({r.stopped_by for r in rows if r.stopped_by})
        },
        "per_query_type": {
            qt: {
                "n": len(g),
                "success": sum(r.success for r in g),
                "retrieved_gold": sum(r.retrieved_gold for r in g),
                "tokens": sum(r.tokens for r in g),
            }
            for qt in sorted({r.query_type for r in rows})
            if (g := [r for r in rows if r.query_type == qt])
        },
    }


def _coverage_tasks() -> list[Task]:
    """Day 7's three, given the shape a `Task` has and no derived expectations.

    `must_cite` is true (a coverage claim naming no clause is worthless) and
    `min_tool_calls` is the honest floor for a sweep: one search plus one read.
    Everything else about them is hand-written, which is why they are scored
    separately and never gated.
    """
    return [
        Task(
            task_id=f"t-9{n:02d}",
            golden_id="gs-0000",
            question=c["question"],
            query_type="coverage",
            gold_doc_ids=[],
            gold_uids=[],
            must_cite=True,
            must_abstain=False,
            min_tool_calls=2,
            gold_answer="",
        )
        for n, c in enumerate(COVERAGE_TASKS, 1)
    ]


# -- the driver --------------------------------------------------------------


async def main_async(a) -> int:
    tasks = read_tasks(a.tasks)
    if a.limit:
        tasks = tasks[: a.limit]
    coverage = _coverage_tasks() if a.coverage else []
    arms = a.arms if a.arms != ["all"] else list(ARMS)
    budget = Budget(max_steps=a.max_steps, max_seconds=a.max_seconds, max_tokens=a.max_tokens)
    trc = tracer(a.trace)
    ix = Index(a.index)

    runners = {
        "single_agent": lambda ts: run_single(ts, a.index, a.model, budget, ix, trc),
        "supervisor": lambda ts: run_graph(
            ts, a.index, a.model, budget, ix, trc, plan_and_execute=False
        ),
        "plan_and_execute": lambda ts: run_graph(
            ts, a.index, a.model, budget, ix, trc, plan_and_execute=True
        ),
    }

    rows: dict[str, list[Row]] = {}
    cover: dict[str, list[Row]] = {}
    t0 = time.perf_counter()
    try:
        # One arm at a time, all of it before the judge is loaded. Batching by
        # model is the sixth day this has mattered: interleaving `qwen3.5:9b` and
        # `qwen3.8` is a 17.7 GB swap per item on a 24 GB card.
        for arm in arms:
            print(f"\n== {arm} · {len(tasks)} tasks", flush=True)
            rows[arm] = await runners[arm](tasks)
            if coverage:
                print(f"\n== {arm} · {len(coverage)} coverage tasks", flush=True)
                cover[arm] = await runners[arm](coverage)
        trc.flush()

        verdicts: dict[str, list] = {}
        if a.judge:
            from regops_evals.agentjudge import judge_rows, summarise

            print(f"\n== judge ({a.judge_model}), after every agent run", flush=True)
            for arm in arms:
                vs = await judge_rows(
                    [r.to_json() | {"arm": arm} for r in rows[arm]],
                    ix,
                    model=a.judge_model,
                )
                verdicts[arm] = vs
                s = summarise(vs)
                print(
                    f"  {arm:<18} "
                    + "  ".join(f"{k} {v['passed']}/{v['n']}" for k, v in s["axes"].items())
                )
    finally:
        ix.close()

    from regops_evals.agentjudge import summarise

    report = {
        "produced_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": a.model,
        "tasks": str(a.tasks),
        # The task file, hashed. Editing the tasks without re-running the eval is
        # staleness in exactly the same sense a prompt edit is.
        "tasks_sha": tasks_sha(a.tasks),
        "n_tasks": len(tasks),
        "arms": arms,
        "gated_arm": GATED_ARM,
        "budget": {
            "max_steps": budget.max_steps,
            "max_seconds": budget.max_seconds,
            "max_tokens": budget.max_tokens,
        },
        "traced": trc.enabled,
        "wall_s": round(time.perf_counter() - t0, 1),
        # The staleness stamp. CI recomputes this from the working tree and
        # fails on a mismatch -- see `prompts.py`.
        **stamp(),
        "metrics": {arm: score(rows[arm]) for arm in arms},
        "judge": {arm: summarise(verdicts[arm]) for arm in verdicts},
        "coverage": {arm: score(cover[arm]) for arm in cover},
        "rows": {arm: [r.to_json() for r in rows[arm]] for arm in arms},
        "coverage_rows": {arm: [r.to_json() for r in cover[arm]] for arm in cover},
        "judge_rows": {arm: [asdict(v) for v in vs] for arm, vs in verdicts.items()},
    }

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"\n-> {a.out}")

    if a.calls:
        a.calls.parent.mkdir(parents=True, exist_ok=True)
        # Coverage rows included: the paging sweep is where a model invents a
        # cursor, and leaving it out of the call log is how F16 stayed invisible
        # to everything except a human reading the server's stderr.
        a.calls.write_text(
            json.dumps(
                {
                    arm: [
                        {"task_id": r.task_id, "calls": r.tool_calls}
                        for r in rs + cover.get(arm, [])
                    ]
                    for arm, rs in rows.items()
                },
                indent=1,
            )
            + "\n"
        )
        print(f"-> {a.calls}")

    _table(report)
    return 0


def _table(report: dict) -> None:
    print(
        f"\n{'architecture':<18}{'success':>9}{'gold':>7}{'cite':>7}{'abst':>7}"
        f"{'eff':>7}{'p50 s':>8}{'tokens':>9}{'bad':>5}"
    )
    print("-" * 77)
    for arm, m in report["metrics"].items():
        s = m["success"]
        print(
            f"{arm:<18}{s['composite']['passed']:>4}/{s['composite']['n']:<4}"
            f"{s['retrieved_gold']['passed']:>7}{s['cited_resolvable']['passed']:>7}"
            f"{s['abstained_correctly']['passed']:>7}"
            f"{(m['trajectory']['efficiency_mean'] or 0):>7.2f}"
            f"{m['latency']['p50_s']:>8.1f}{m['cost']['tokens']:>9,}"
            f"{m['citations']['unresolvable']:>5}"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    ap.add_argument("--tasks", type=Path, default=Path("golden/tasks/v1/tasks.jsonl"))
    ap.add_argument("--arms", nargs="+", default=["all"], help="'all' or explicit arm names")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--judge-model", default="qwen3.8:latest")
    ap.add_argument("--limit", type=int, default=None, help="first N tasks; for smoke runs")
    ap.add_argument("--coverage", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--judge", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--trace", action="store_true", help="send spans to LangFuse (opt-in)")
    ap.add_argument("--max-steps", type=int, default=Budget().max_steps)
    ap.add_argument("--max-seconds", type=float, default=Budget().max_seconds)
    ap.add_argument("--max-tokens", type=int, default=Budget().max_tokens)
    ap.add_argument("--out", type=Path, default=Path("results/day8/eval.json"))
    ap.add_argument("--calls", type=Path, default=None, help="write the raw tool-call log here")
    return asyncio.run(main_async(ap.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
