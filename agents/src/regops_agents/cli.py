"""`regops-agents` -- run one question through the agent and show its working."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from regops_agents.agent import MAX_SECONDS, MAX_STEPS, MODEL, ask, build_agent
from regops_agents.mcp_tools import mcp_tools
from regops_agents.tools import LocalSearch


async def _ask(a) -> int:
    local = LocalSearch(a.index) if a.local else None
    try:
        async with mcp_tools(a.index) as tools:
            if local is not None:
                tools = [*tools, local.as_tool()]
            print(f"tools: {[t.name for t in tools]}\n")
            agent = build_agent(tools, model=a.model, num_ctx=a.num_ctx)
            run = await ask(agent, a.question, max_steps=a.max_steps, max_seconds=a.max_seconds)
    finally:
        if local is not None:
            local.close()

    for i, c in enumerate(run.tool_calls, 1):
        flag = "  ERROR" if c["error"] else ""
        print(f"  {i}. {c['tool']}({json.dumps(c['args'])[:120]}) -> {c['result_chars']:,}ch{flag}")
    print(f"\nsteps {run.steps} · {run.seconds:.1f}s · stopped_by={run.stopped_by or '-'}")
    if run.error:
        print(f"error: {run.error}")
    print()
    print(run.answer)
    return 1 if run.stopped_by == "error" else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="regops-agents", description=__doc__)
    ap.add_argument("question")
    ap.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    ap.add_argument("--model", default=MODEL)
    ap.add_argument(
        "--local",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="also offer search_local (C4 hybrid + reranker); loads 1.33 GB of weights",
    )
    ap.add_argument("--max-steps", type=int, default=MAX_STEPS)
    ap.add_argument("--max-seconds", type=float, default=MAX_SECONDS)
    ap.add_argument("--num-ctx", type=int, default=None, help="provoke F3; leave unset normally")
    a = ap.parse_args(argv)
    return asyncio.run(_ask(a))


if __name__ == "__main__":
    raise SystemExit(main())
