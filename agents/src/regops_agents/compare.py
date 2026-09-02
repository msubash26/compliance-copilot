"""The same questions through both frameworks, so the tradeoff is a table.

"Which framework is nicer" is not a finding. This runs LangGraph and Pydantic AI
over an identical question set, with the same model, the same system prompt, the
same `Answer` schema and the same MCP server, and reports four things — plus
lines of code, which is reported and explicitly **not** treated as a quality
signal.

Read the wall-clock column with the caveat it carries: LangChain's `ChatOllama`
posts to Ollama's native `/api/chat` and can set `reasoning=False`, which is a
15x difference on `qwen3.5:9b` (ADR-009). Pydantic AI's Ollama provider speaks
the OpenAI-compatible `/v1`, which ignores it. That is a real cost of choosing
the framework, and it is not a fact about the framework's design quality.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from regops_agents.toolcall_probe import load_sample


async def _langgraph(items: list[dict], index: Path, model: str) -> dict:
    from regops_agents.agent import ask, build_agent
    from regops_agents.mcp_tools import mcp_tools

    rows = []
    async with mcp_tools(index) as tools:
        agent = build_agent(tools, model=model)
        for i, it in enumerate(items, 1):
            r = await ask(agent, it["question"])
            rows.append(
                {
                    "item_id": it["id"],
                    "completed": not r.stopped_by,
                    "tool_calls": len(r.tool_calls),
                    "tools": [c["tool"] for c in r.tool_calls],
                    "tool_errors": sum(1 for c in r.tool_calls if c["error"]),
                    "steps": r.steps,
                    "seconds": round(r.seconds, 2),
                    "stopped_by": r.stopped_by,
                }
            )
            print(
                f"  [{i:>2}/{len(items)}] {it['id']}  {len(r.tool_calls)} calls  {r.seconds:.1f}s"
            )
    return _summary("langgraph", rows)


async def _pydantic_ai(items: list[dict], index: Path, model: str, behavior: str) -> dict:
    from regops_agents.pydai import ask, build

    agent, _ = build(model, index=index, tool_error_behavior=behavior)
    rows = []
    async with agent:
        for i, it in enumerate(items, 1):
            r = await ask(agent, it["question"])
            rows.append(
                {
                    "item_id": it["id"],
                    "completed": r.ok,
                    "tool_calls": len(r.tool_calls),
                    "tools": [c["tool"] for c in r.tool_calls],
                    "tool_errors": sum(1 for c in r.tool_calls if c["error"]),
                    "steps": r.steps,
                    "seconds": round(r.seconds, 2),
                    "stopped_by": "error" if r.error else "",
                    "error": r.error,
                }
            )
            print(
                f"  [{i:>2}/{len(items)}] {it['id']}  {len(r.tool_calls)} calls  {r.seconds:.1f}s"
                + (f"  {r.error[:60]}" if r.error else "")
            )
    return _summary(f"pydantic-ai ({behavior})", rows)


def _summary(name: str, rows: list[dict]) -> dict:
    lat = sorted(r["seconds"] for r in rows)
    n = len(rows) or 1
    return {
        "framework": name,
        "n": len(rows),
        "completed": sum(r["completed"] for r in rows),
        "called_a_tool": sum(1 for r in rows if r["tool_calls"]),
        "tool_calls_total": sum(r["tool_calls"] for r in rows),
        "tool_calls_mean": round(sum(r["tool_calls"] for r in rows) / n, 2),
        "tool_errors": sum(r["tool_errors"] for r in rows),
        "p50_s": round(lat[len(lat) // 2], 2) if lat else 0.0,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    ap.add_argument("--golden", type=Path, default=Path("golden/v1/golden.jsonl"))
    ap.add_argument("--model", default="qwen3.5:9b")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--out", type=Path, default=Path("results/day6/frameworks.json"))
    a = ap.parse_args(argv)

    items = load_sample(a.golden)[: a.n]
    out: dict = {"model": a.model, "n": len(items), "results": []}

    # One framework fully, then the next. Both drive the same Ollama model and
    # Ollama serialises; interleaving them would measure the swap, not the code.
    for label, coro in (
        ("langgraph", _langgraph(items, a.index, a.model)),
        ("pydantic-ai", _pydantic_ai(items, a.index, a.model, "retry")),
    ):
        print(f"== {label}")
        t0 = time.perf_counter()
        out["results"].append(asyncio.run(coro))
        print(f"   {time.perf_counter() - t0:.1f}s\n")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2) + "\n")

    hdr = f"{'framework':<26}{'completed':>11}{'tool calls':>12}{'errors':>8}{'p50':>8}"
    print(hdr + "\n" + "-" * len(hdr))
    for s in out["results"]:
        print(
            f"{s['framework']:<26}{s['completed']:>4}/{s['n']:<6}"
            f"{s['tool_calls_total']:>12}{s['tool_errors']:>8}{s['p50_s']:>8.2f}"
        )
    print(f"\n-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
