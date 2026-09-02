"""Does the model call the right tool with arguments that can find the answer?

Day 6's research step measured `qwen3.5:9b` emitting a tool call for 29 of 30
questions and inventing a filter that excluded the gold document on 9 of them.
Tool-*calling* works; argument *selection* is what loses answers, and it loses
them before the retriever is ever consulted.

This module is that measurement, made re-runnable and made comparable across
models. It is also F1's trigger in `FAILURE_MODES.md`: an entry without a
reproduction is a story, not evidence.

Three properties it has to hold on to:

**The schemas come from the server.** They are read over a real `tools/list`
against `regdocs-mcp`, not copied into a literal here. A hand-written copy drifts
from the server it claims to describe, and the whole question is what the model
does with the descriptions the server actually publishes.

**"Excludes the gold document" is decided by the server's own filter semantics**,
not by a guess at them -- `issuer` and `doc_type` are equality, and `date_from`
additionally drops every document with no stated effective date. Re-implementing
that predicate loosely would understate the failure.

**Both models see the identical sample**, chosen deterministically from the
golden set with no RNG, so the comparison is of models rather than of draws.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx
from regdocs_mcp import index as rindex

# Ollama's native endpoint, for the reason ADR-009 and ADR-015 give: `think` is
# ignored by the OpenAI-compatible path, and reasoning on this model is a 15x
# difference. A tool-call decision does not need a chain of thought.
OLLAMA_TIMEOUT_S = 300.0

# The three filters `search_notices` advertises. The probe's whole subject.
FILTERS = ("issuer", "doc_type", "date_from")

# Proportional to the golden set's own grounded strata (45/30/25/15 over 115),
# rounded to 30. Declared here rather than sampled, so a re-run is the same run.
SAMPLE = {"factual_lookup": 12, "multi_hop": 8, "comparative": 6, "temporal": 4}

# Two system prompts, because the difference between them is a measurement, not a
# style choice. `bare` is the tool schemas and nothing else -- the model is left
# to infer from the descriptions alone what the filters are for. `steered` adds
# one sentence telling it not to narrow the search unasked. F1's mitigation is
# whichever of these costs fewer lost gold documents, and the cost of the
# mitigation is one sentence of prompt.
SYSTEMS = {
    "bare": (
        "You are a regulatory compliance assistant with access to a search index of "
        "Singapore MAS notices and guidelines. Use the tools to find the clause that "
        "answers the user's question. Do not answer from memory."
    ),
    "steered": (
        "You are a regulatory compliance assistant with access to a search index of "
        "Singapore MAS notices and guidelines. Use the tools to find the clause that "
        "answers the user's question. Do not answer from memory.\n"
        "Search broadly first. Do not set issuer, doc_type or date_from unless the "
        "user's question names one explicitly -- a wrong filter silently removes the "
        "answer from the results, and you will not be told that it did."
    ),
}


def base_url() -> str:
    import os

    return os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


# -- the sample ------------------------------------------------------------


def load_sample(golden: Path, sample: dict[str, int] = SAMPLE) -> list[dict]:
    """The first N grounded items of each type, by id. Deterministic, no RNG."""
    items = [json.loads(ln) for ln in golden.read_text().splitlines() if ln.strip()]
    grounded = [it for it in items if it.get("gold_spans")]
    out: list[dict] = []
    for qtype, n in sample.items():
        rows = sorted((it for it in grounded if it["query_type"] == qtype), key=lambda it: it["id"])
        out.extend(rows[:n])
    return sorted(out, key=lambda it: it["id"])


# -- the tool schemas, from the server -------------------------------------


async def _fetch_schemas(index_path: Path) -> list[dict]:
    import os

    from mcp import ClientSession
    from mcp.client._memory import InMemoryTransport

    os.environ["REGDOCS_INDEX"] = str(index_path)
    import regdocs_mcp.server as srv

    srv._conn = None
    async with (
        InMemoryTransport(srv.mcp, raise_exceptions=False) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        tools = (await session.list_tools()).tools
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.input_schema,
            },
        }
        for t in tools
    ]


def tool_schemas(index_path: Path) -> list[dict]:
    """The four tools exactly as an MCP host would receive them."""
    return asyncio.run(_fetch_schemas(index_path))


# -- the verdict on one call -----------------------------------------------


def excludes(gold: dict, args: dict) -> list[str]:
    """Which of the model's filters would remove the gold document from results.

    Mirrors `regdocs_mcp.index.search_sections`: equality on `issuer` and
    `doc_type`, and `date_from` requires a stated effective date at or after it.
    """
    bad = []
    if (v := args.get("issuer")) and v != gold["issuer"]:
        bad.append("issuer")
    if (v := args.get("doc_type")) and v != gold["doc_type"]:
        bad.append("doc_type")
    if v := args.get("date_from"):
        eff = gold.get("effective_date")
        if eff is None or str(eff) < str(v):
            bad.append("date_from")
    return bad


@dataclass
class Call:
    item_id: str
    query_type: str
    emitted: bool
    tool: str = ""
    args: dict = field(default_factory=dict)
    filters_added: list[str] = field(default_factory=list)
    excludes_gold: list[str] = field(default_factory=list)
    top_k: int | None = None
    wall_s: float = 0.0
    error: str = ""


def _chat(model: str, question: str, tools: list[dict], system: str) -> tuple[dict, float, str]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        "tools": tools,
        "think": False,
        "stream": False,
        "options": {"temperature": 0.0},
    }
    t0 = time.perf_counter()
    try:
        r = httpx.post(f"{base_url()}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT_S)
        r.raise_for_status()
        body = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {}, time.perf_counter() - t0, str(exc)[:200]
    return body.get("message", {}) or {}, time.perf_counter() - t0, ""


def run_model(
    model: str, items: list[dict], tools: list[dict], conn, system: str = SYSTEMS["bare"]
) -> list[Call]:
    """One model over the whole sample. Batched by model -- Ollama serialises."""
    calls: list[Call] = []
    for i, it in enumerate(items, 1):
        msg, wall, err = _chat(model, it["question"], tools, system)
        tcs = msg.get("tool_calls") or []
        if err or not tcs:
            calls.append(Call(it["id"], it["query_type"], emitted=False, wall_s=wall, error=err))
            print(f"  [{i:>2}/{len(items)}] {it['id']}  no tool call{'  ' + err if err else ''}")
            continue

        fn = tcs[0].get("function", {}) or {}
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}

        gold_doc = rindex.document(conn, it["gold_spans"][0]["doc_id"]) or {}
        added = [f for f in FILTERS if args.get(f)]
        bad = excludes(gold_doc, args) if gold_doc else []
        top_k = args.get("top_k")
        calls.append(
            Call(
                item_id=it["id"],
                query_type=it["query_type"],
                emitted=True,
                tool=fn.get("name", ""),
                args=args,
                filters_added=added,
                excludes_gold=bad,
                top_k=int(top_k) if isinstance(top_k, int | float | str) and top_k else None,
                wall_s=wall,
            )
        )
        mark = f"  EXCLUDES GOLD via {','.join(bad)}" if bad else ""
        print(f"  [{i:>2}/{len(items)}] {it['id']}  {fn.get('name', '')}  {added or '-'}{mark}")
    return calls


# -- aggregation -----------------------------------------------------------


def aggregate(calls: list[Call]) -> dict:
    n = len(calls)
    emitted = [c for c in calls if c.emitted]
    e = len(emitted)
    lat = sorted(c.wall_s for c in calls)
    filtered = [c for c in emitted if c.filters_added]
    lost = [c for c in emitted if c.excludes_gold]
    return {
        "n": n,
        "emitted": e,
        "emitted_rate": round(e / n, 4) if n else 0.0,
        "tools": dict(Counter(c.tool for c in emitted)),
        "added_a_filter": len(filtered),
        "added_a_filter_rate": round(len(filtered) / e, 4) if e else 0.0,
        "excludes_gold": len(lost),
        "excludes_gold_rate": round(len(lost) / e, 4) if e else 0.0,
        "excluded_by": dict(Counter(f for c in lost for f in c.excludes_gold)),
        "top_k_below_5": sum(1 for c in emitted if c.top_k is not None and c.top_k < 5),
        "p50_s": round(lat[len(lat) // 2], 3) if lat else 0.0,
        "max_s": round(lat[-1], 3) if lat else 0.0,
        "errors": sum(1 for c in calls if c.error),
        "by_type": {
            qt: {
                "n": sum(1 for c in calls if c.query_type == qt),
                "excludes_gold": sum(1 for c in calls if c.query_type == qt and c.excludes_gold),
            }
            for qt in SAMPLE
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    ap.add_argument("--golden", type=Path, default=Path("golden/v1/golden.jsonl"))
    ap.add_argument("--models", nargs="+", default=["qwen3.5:9b", "qwen3.8:latest"])
    ap.add_argument("--system", choices=sorted(SYSTEMS), default="bare")
    ap.add_argument("--out", type=Path, default=Path("results/day6/toolcall_probe.json"))
    a = ap.parse_args(argv)

    items = load_sample(a.golden)
    tools = tool_schemas(a.index)
    conn = rindex.connect(a.index)
    print(f"{len(items)} questions, {len(tools)} tool schemas from the server\n")

    out: dict = {"sample": [it["id"] for it in items], "system": a.system, "models": {}}
    for model in a.models:  # one model fully, then the next: ADR-015's rule
        print(f"== {model}  (system: {a.system})")
        calls = run_model(model, items, tools, conn, SYSTEMS[a.system])
        out["models"][model] = {"summary": aggregate(calls), "calls": [asdict(c) for c in calls]}
        print()

    conn.close()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2) + "\n")

    hdr = f"{'model':<18}{'emitted':>9}{'filtered':>10}{'lost gold':>11}{'p50':>8}{'max':>8}"
    print(hdr)
    print("-" * len(hdr))
    for model, blk in out["models"].items():
        s = blk["summary"]
        print(
            f"{model:<18}{s['emitted']:>4}/{s['n']:<4}{s['added_a_filter']:>5}/{s['emitted']:<4}"
            f"{s['excludes_gold']:>6}/{s['emitted']:<4}{s['p50_s']:>8.2f}{s['max_s']:>8.2f}"
        )
    print(f"\n-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
