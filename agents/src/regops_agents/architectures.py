"""Day 6's single agent, the supervisor, and plan-and-execute, on the same tasks.

The prep plan asks for the plan-and-execute comparison and then, in the same
breath, asks you to be ready to argue *against* multi-agent: *"the honest answer
for many tasks is that a single well-toolled agent is cheaper, faster and easier
to debug"*. That argument is only worth making with the losing number in hand, so
this harness runs the single agent too, on two task sets chosen to make each
architecture look bad at something.

**Lookup** is six golden questions -- the same six Day 6 measured, so the numbers
sit next to `results/day6/frameworks.json` rather than replacing it. One clause
answers each. The supervisor is expected to lose here and the interesting
question is by how much.

**Coverage** is three hand-written tasks that ask which documents in the corpus
address a topic. They are unscored on purpose: Day 8 owns the eval and its judge
calibration, and inventing a rubric today would produce a second one to
reconcile. What is measured is structural -- how many *distinct documents* the
answer reaches a verdict on -- because that is the dimension a single context
window cannot buy its way out of.

Every architecture is measured through the same layer 2. A claim carrying an
identifier that does not resolve is the failure Day 6 built `check_references`
for, and it is the one quality signal available here that needs no judge.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from pathlib import Path

from regops_retrieval.index import Index

from regops_agents.budget import Budget, new_spend, summary, usd
from regops_agents.llm import MODEL
from regops_agents.toolcall_probe import load_sample

# Three coverage tasks. Declared, not sampled: a re-run must be the same run, and
# these are the shape the supervisor exists for -- one context window per document
# and a verdict per document, which is not a thing a single window can hold.
COVERAGE_TASKS = [
    {
        "id": "cv-001",
        "question": (
            "Which documents in the corpus state an obligation about politically "
            "exposed persons, and which are silent on it?"
        ),
    },
    {
        "id": "cv-002",
        "question": (
            "Which documents in the corpus place an obligation to keep records, "
            "and which are silent on it?"
        ),
    },
    {
        "id": "cv-003",
        "question": (
            "Which documents in the corpus require the filing of suspicious "
            "transaction reports, and which are silent on it?"
        ),
    },
]

# How a free-text answer gets held to the same layer 2 as a structured one.
#
# The pairing has to work in **both** directions, and getting this wrong is the
# easiest way to rig this comparison. Day 6's agent writes
#
#     "...specifically in section 6.14 (doc_id: `1b9b9f6db2876069`)"
#
# with the clause *before* the id. A pattern that only matched id-then-clause
# scored that answer as citing nothing resolvable, which would have made the
# single agent look far worse than it is. So each id is found first, and the
# clause is looked for in a window on either side of it.
DOC_ID = re.compile(r"\b([0-9a-f]{16})\b")
CLAUSE = re.compile(r"\b\d+(?:\.\d+)+\b|(?<=clause )\d+\b|(?<=section )\d+\b")
WINDOW = 140


def cited_pairs(text: str) -> list[tuple[str, str]]:
    """Every (doc_id, section_path) a prose answer can be read as asserting."""
    text = text or ""
    out = []
    for m in DOC_ID.finditer(text):
        before = text[max(0, m.start() - WINDOW) : m.start()]
        after = text[m.end() : m.end() + WINDOW]
        # Nearest clause number wins: the last one before the id, or the first
        # one after it, whichever sits closer.
        left = list(CLAUSE.finditer(before))
        right = CLAUSE.search(after)
        cand = []
        if left:
            cand.append((len(before) - left[-1].end(), left[-1].group()))
        if right:
            cand.append((right.start(), right.group()))
        out.append((m.group(1), min(cand)[1] if cand else ""))
    return out


def resolve(pairs: list[tuple[str, str]], ix: Index) -> tuple[int, int]:
    """(asserted, unresolvable) -- layer 2, applied identically to every arm."""
    bad = sum(1 for d, s in pairs if not s or ix.clause_by_uid(f"{d}:{s}") is None)
    return len(pairs), bad


def docs_judged(text: str, pairs: list[tuple[str, str]], findings: list[dict]) -> int:
    """How many distinct documents the answer reaches a verdict on.

    Structural, and deliberately generous to the single agent: it is credited for
    every distinct document id it cites, without asking whether it said anything
    about coverage. If it still loses this column, the loss is not an artefact of
    the measure.
    """
    if findings:
        return len({f["doc_id"] for f in findings})
    return len({d for d, _ in pairs})


# -- the three arms ----------------------------------------------------------


async def run_single(items, index: Path, model: str, budget: Budget, ix: Index) -> list[dict]:
    """Day 6's ReAct agent, unchanged, over the same MCP server."""
    from regops_agents.agent import ask, build_agent
    from regops_agents.mcp_tools import mcp_tools

    rows = []
    async with mcp_tools(index) as tools:
        agent = build_agent(tools, model=model)
        for i, it in enumerate(items, 1):
            t0 = time.perf_counter()
            r = await ask(agent, it["question"], max_steps=budget.max_steps)
            pairs = cited_pairs(r.answer)
            asserted, bad = resolve(pairs, ix)
            # LangChain reports usage on the AI messages; summing them is the only
            # way this arm gets a token column at all.
            tokens = sum(
                (getattr(m, "usage_metadata", None) or {}).get("total_tokens", 0)
                for m in r.messages
            )
            rows.append(
                {
                    "item_id": it["id"],
                    "completed": not r.stopped_by,
                    "stopped_by": r.stopped_by,
                    "steps": r.steps,
                    "tool_calls": len(r.tool_calls),
                    "seconds": round(time.perf_counter() - t0, 2),
                    "tokens": tokens,
                    "usd": usd({"in_tokens": tokens, "out_tokens": 0}),
                    "cited": asserted,
                    "unresolvable": bad,
                    "docs_judged": docs_judged(r.answer, pairs, []),
                    "answer_chars": len(r.answer),
                }
            )
            _line(i, len(items), rows[-1])
    return rows


async def run_graph(
    items, index: Path, model: str, budget: Budget, ix: Index, *, plan_and_execute: bool
) -> list[dict]:
    from regops_agents.supervisor import ask, running

    rows = []
    async with running(
        index,
        model=model,
        budget=budget,
        plan_and_execute=plan_and_execute,
        approve=False,  # unattended; the interrupt is proved in `test_checkpoint.py`
    ) as (app, config):
        for i, it in enumerate(items, 1):
            out = await ask(app, config, it["question"])
            cost = out.get("cost") or summary(new_spend(), budget)
            # The graph's own citations are already layer-2 filtered, so the
            # honest count of what it *asserted* is those plus what `check`
            # rejected. Reporting only the survivors would score a strict
            # architecture as though it had never made a mistake.
            good = out.get("citations") or []
            bad = len(out.get("violations") or [])
            rows.append(
                {
                    "item_id": it["id"],
                    "completed": not out.get("stopped_by"),
                    "stopped_by": out.get("stopped_by", ""),
                    "steps": cost.get("steps", 0),
                    "tool_calls": cost.get("steps", 0),
                    "seconds": out.get("wall_seconds", 0.0),
                    "tokens": cost.get("tokens", 0),
                    "usd": cost.get("usd", 0.0),
                    "cited": len(good) + bad,
                    "unresolvable": bad,
                    "docs_judged": docs_judged(
                        out.get("answer", ""),
                        [(c["doc_id"], c["section_path"]) for c in good],
                        out.get("findings") or [],
                    ),
                    "answer_chars": len(out.get("answer", "")),
                }
            )
            _line(i, len(items), rows[-1])
    return rows


def _line(i: int, n: int, row: dict) -> None:
    flag = f"  {row['stopped_by']}" if row["stopped_by"] else ""
    print(
        f"  [{i:>2}/{n}] {row['item_id']}  {row['steps']:>2} steps  "
        f"{row['seconds']:>6.1f}s  {row['tokens']:>6,} tok  "
        f"cites {row['cited']}({row['unresolvable']} bad)  "
        f"docs {row['docs_judged']}{flag}"
    )


def aggregate(name: str, rows: list[dict]) -> dict:
    n = len(rows) or 1
    secs = sorted(r["seconds"] for r in rows)
    return {
        "architecture": name,
        "n": len(rows),
        "completed": sum(r["completed"] for r in rows),
        "steps_total": sum(r["steps"] for r in rows),
        "p50_s": round(secs[len(secs) // 2], 2) if secs else 0.0,
        "total_s": round(sum(secs), 2),
        "tokens": sum(r["tokens"] for r in rows),
        "usd": round(sum(r["usd"] for r in rows), 6),
        "cited": sum(r["cited"] for r in rows),
        "unresolvable": sum(r["unresolvable"] for r in rows),
        "docs_judged_mean": round(sum(r["docs_judged"] for r in rows) / n, 2),
        "rows": rows,
    }


async def main_async(a) -> int:
    ix = Index(a.index)
    budget = Budget(max_steps=a.max_steps, max_seconds=a.max_seconds, max_tokens=a.max_tokens)
    lookup = load_sample(a.golden)[: a.n_lookup]
    coverage = COVERAGE_TASKS[: a.n_coverage]

    arms = {
        "single_agent": lambda items: run_single(items, a.index, a.model, budget, ix),
        "supervisor": lambda items: run_graph(
            items, a.index, a.model, budget, ix, plan_and_execute=False
        ),
        "plan_and_execute": lambda items: run_graph(
            items, a.index, a.model, budget, ix, plan_and_execute=True
        ),
    }

    out: dict = {"model": a.model, "sets": {}}
    try:
        for set_name, items in (("lookup", lookup), ("coverage", coverage)):
            out["sets"][set_name] = []
            for arm_name, fn in arms.items():
                print(f"\n== {set_name} · {arm_name}")
                out["sets"][set_name].append(aggregate(arm_name, await fn(items)))
    finally:
        ix.close()

    for set_name, results in out["sets"].items():
        print(
            f"\n{set_name:>9}  {'architecture':<18}{'done':>6}{'steps':>7}{'p50 s':>8}"
            f"{'tokens':>9}{'usd':>10}{'cites':>7}{'bad':>5}{'docs':>6}"
        )
        print(" " * 10 + "-" * 76)
        for r in results:
            print(
                f"{'':>10}{r['architecture']:<18}{r['completed']}/{r['n']:<4}"
                f"{r['steps_total']:>7}{r['p50_s']:>8.2f}{r['tokens']:>9,}"
                f"{r['usd']:>10.5f}{r['cited']:>7}{r['unresolvable']:>5}"
                f"{r['docs_judged_mean']:>6.1f}"
            )

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n-> {a.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    ap.add_argument("--golden", type=Path, default=Path("golden/v1/golden.jsonl"))
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--n-lookup", type=int, default=6)
    ap.add_argument("--n-coverage", type=int, default=3)
    ap.add_argument("--max-steps", type=int, default=Budget().max_steps)
    ap.add_argument("--max-seconds", type=float, default=Budget().max_seconds)
    ap.add_argument("--max-tokens", type=int, default=Budget().max_tokens)
    ap.add_argument("--out", type=Path, default=Path("results/day7/architectures.json"))
    return asyncio.run(main_async(ap.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
