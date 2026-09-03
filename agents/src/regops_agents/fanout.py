"""What did fanning the sub-agents out in parallel actually buy?

The prep plan asks for "parallel fan-out where the subtasks are independent, and
a measurement of what that bought you in wall-clock time". This is that
measurement, and it is allowed to come back negative -- which it does.

The measurement is taken **inside the graph**, on `gap_analyst`'s fan-out, not
against the raw API. That distinction matters: a benchmark of four bare HTTP
calls would be measuring Ollama, and the question is what the *architecture*
bought. The sequential arm runs the identical branches through the identical
worker, one after another, so the only variable is concurrency.

Two things are reported, because a speedup on its own answers nothing.

**The ceiling, `sum / max`.** It bounds what *any* amount of orchestration could
win on this work. A speedup quoted without it hides whether the prize was ever
worth chasing.

**The queued fraction.** Each branch is timed in two halves -- the MCP and DuckDB
work, which is not contended, and the model call, which is. That ratio is the
thing that generalises: fan-out earns its keep when the un-queued half is large,
and this graph is the case where it is not.

The arms alternate, sequential and parallel in turn, and the reported total is
the **median** of `--repeats` rounds. A single four-branch round takes a few
seconds and the first one pays for warm caches; alternating and taking medians
cancels that drift instead of arguing about it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from regops_agents.budget import merge_spend, new_spend
from regops_agents.llm import MODEL
from regops_agents.mcp_tools import PARSER_RESULT_CHARS, mcp_tools
from regops_agents.workers import (
    COVERAGE_TOP_K,
    Toolbox,
    clauses_of,
    inspect_one,
    search,
)

# The coverage question the sweep is measured on. One topic, so both arms do
# identical work; declared here rather than sampled, so a re-run is the same run.
TOPIC = "politically exposed persons"
QUERY = "politically exposed persons obligation"
WIDTH = 4


def _docs(hits: list[dict], width: int) -> list[dict]:
    """Hits grouped by document, exactly as `node_fan_out` groups them."""
    grouped: dict[str, dict] = {}
    for h in hits:
        d = grouped.setdefault(
            h["doc_id"],
            {
                "doc_id": h["doc_id"],
                "title": h.get("title", ""),
                "excerpt": h.get("snippet", ""),
                "hits": [],
            },
        )
        d["hits"].append(h)
    return list(grouped.values())[:width]


async def _branch(doc: dict, box: Toolbox) -> dict:
    """One fan-out branch, timed in its two halves.

    `clauses_of` is several MCP round trips over stdio plus DuckDB work in the
    server -- uncontended. The model call is the one that queues. Timing them
    apart is what turns "the speedup was 1.2x" into a statement about *why*, and
    into one that transfers to hardware this project does not have.
    """
    t = time.perf_counter()
    text = await clauses_of(TOPIC, doc, box)
    read_s = time.perf_counter() - t

    t = time.perf_counter()
    finding, cost = await inspect_one(TOPIC, doc, box, prefetched=text)
    model_s = time.perf_counter() - t

    return {
        "seconds": read_s + model_s,
        "read_s": read_s,
        "model_s": model_s,
        "cost": cost,
        "covered": bool(finding and finding.covered),
    }


async def _arm(docs: list[dict], box: Toolbox, parallel: bool) -> dict:
    t0 = time.perf_counter()
    if parallel:
        rows = await asyncio.gather(*(_branch(d, box) for d in docs))
    else:
        rows = [await _branch(d, box) for d in docs]
    total = time.perf_counter() - t0

    spend = new_spend()
    for r in rows:
        spend = merge_spend(spend, r["cost"])
    per = [round(r["seconds"], 2) for r in rows]
    return {
        "parallel": parallel,
        "total_s": round(total, 3),
        "per_branch_s": per,
        "sum_s": round(sum(per), 2),
        "max_s": round(max(per), 2) if per else 0.0,
        "read_s": round(sum(r["read_s"] for r in rows), 3),
        "model_s": round(sum(r["model_s"] for r in rows), 3),
        "covered": sum(1 for r in rows if r["covered"]),
        "tokens": spend["in_tokens"] + spend["out_tokens"],
    }


def _median(xs: list[float]) -> float:
    xs = sorted(xs)
    return xs[len(xs) // 2]


async def run(index: Path, model: str, repeats: int, out: Path) -> int:
    import os

    async with mcp_tools(index, max_result_chars=PARSER_RESULT_CHARS) as tools:
        box = Toolbox(index=index, tools={t.name: t for t in tools}, model=model)

        hits, _ = await search(QUERY, box, COVERAGE_TOP_K)
        docs = _docs(hits, WIDTH)
        print(f"{len(docs)} branch(es): " + ", ".join(d["title"][:32] for d in docs))

        # Warm the model so no round pays the 6.6 GB load. Without this whichever
        # arm runs first carries it, and the "speedup" measures when the weights
        # arrived rather than what concurrency bought.
        await _branch(docs[0], box)

        rounds = []
        for i in range(repeats):
            seq = await _arm(docs, box, parallel=False)
            par = await _arm(docs, box, parallel=True)
            rounds.append({"round": i + 1, "sequential": seq, "parallel": par})
            print(
                f"  round {i + 1}: sequential {seq['total_s']:>6.2f}s   "
                f"parallel {par['total_s']:>6.2f}s"
            )

    seq_t = _median([r["sequential"]["total_s"] for r in rounds])
    par_t = _median([r["parallel"]["total_s"] for r in rounds])
    last = rounds[-1]["sequential"]
    ceiling = last["sum_s"] / last["max_s"] if last["max_s"] else 1.0
    speedup = seq_t / par_t if par_t else 1.0
    queued = last["model_s"] / (last["read_s"] + last["model_s"])

    summary = {
        "sequential_median_s": round(seq_t, 2),
        "parallel_median_s": round(par_t, 2),
        "speedup": round(speedup, 2),
        "ceiling": round(ceiling, 2),
        # The fraction of the *available* saving that was captured, not of the
        # ceiling itself. `speedup / ceiling` would report a run that got slower
        # as having captured 31%, which is not a thing that happened.
        "captured": round((speedup - 1) / (ceiling - 1), 3) if ceiling > 1 else 0.0,
        "saved_s": round(seq_t - par_t, 2),
        "queued_fraction": round(queued, 3),
        "read_s_total": last["read_s"],
        "model_s_total": last["model_s"],
    }

    print(
        f"\nmedian of {repeats}: sequential {seq_t:.2f}s   parallel {par_t:.2f}s   "
        f"speedup {speedup:.2f}x   ceiling {ceiling:.2f}x   "
        f"captured {summary['captured']:.0%}"
    )
    print(
        f"one branch is {queued:.0%} queued model time "
        f"({last['model_s']:.2f}s) and {1 - queued:.0%} uncontended tool time "
        f"({last['read_s']:.2f}s)"
    )

    payload = {
        "model": model,
        "topic": TOPIC,
        "width": WIDTH,
        "repeats": repeats,
        "ollama_num_parallel": os.environ.get("OLLAMA_NUM_PARALLEL", "(unset)"),
        "summary": summary,
        "rounds": rounds,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"-> {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--out", type=Path, default=Path("results/day7/fanout.json"))
    a = ap.parse_args(argv)
    return asyncio.run(run(a.index, a.model, a.repeats, a.out))


if __name__ == "__main__":
    raise SystemExit(main())
