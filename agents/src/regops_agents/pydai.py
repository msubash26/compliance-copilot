"""The same task in Pydantic AI, to make the framework comparison an experience.

Same model, same two-sentence system prompt, same `Answer` output type, same MCP
server over stdio, same golden sample. Four measured columns and one that is
reported but explicitly not treated as a quality signal:

    tool-call accuracy   did it call a tool, with arguments that keep the answer
    steps to answer      how much work per question
    wall-clock p50       what a run costs
    behaviour on error   what happens when a tool raises  <- the one that is not taste
    lines of code        reported, and not a quality signal

The fourth is the one worth building this for. Latency and step counts are
properties of the model far more than of the framework; what a framework does
when a tool raises is a design decision it made for you, and the two here made
different ones.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset, StdioTransport
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from regops_agents.agent import MODEL, SYSTEM
from regops_agents.mcp_tools import SERVER_DIR
from regops_agents.structured import Answer

# Pydantic AI reaches Ollama through its **OpenAI-compatible** endpoint. That is
# not a detail: ADR-009 and ADR-015 record that `/v1` ignores `think: false`,
# and on `qwen3.5:9b` reasoning is a 15x difference (7.98s vs 0.53s). LangChain's
# `ChatOllama` posts to the native `/api/chat` and can turn it off. So a
# wall-clock comparison between the two frameworks is partly a comparison of
# which endpoint each one chose to speak, and the write-up says so rather than
# reporting the seconds as though they were the framework's doing.
OLLAMA_V1 = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/v1"


@dataclass
class PydRun:
    question: str
    answer: Answer | None = None
    tool_calls: list[dict] = field(default_factory=list)
    steps: int = 0
    seconds: float = 0.0
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.answer is not None and not self.error


def build(
    model: str = MODEL,
    *,
    index: Path,
    retries: int = 1,
    tool_error_behavior: str = "retry",
) -> tuple[Agent, MCPToolset]:
    """The same agent, declared the way this framework declares one.

    `output_type=Answer` is the structural difference from the LangGraph build:
    the schema is a property of the *agent*, not of a separate generation call,
    and Pydantic AI validates and retries it internally. That is genuinely less
    code — and it is also why the repair behaviour is the framework's rather than
    ours, which F11 measured as worth 0 of 11.
    """
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    toolset = MCPToolset(
        StdioTransport(
            command="uv",
            args=["run", "--directory", str(SERVER_DIR), "regdocs-mcp"],
            env={**env, "REGDOCS_INDEX": str(Path(index).resolve())},
        ),
        # The framework's answer to "what happens when a tool raises", and it is
        # a *setting* -- which is itself the finding. `retry` (the default) hands
        # the error back to the model to recover from, the way LangGraph does
        # unconditionally. `error` propagates it out of `agent.run()` and kills
        # the run: the model never sees it. Both are measured; see ADR-027.
        tool_error_behavior=tool_error_behavior,
    )
    agent = Agent(
        OpenAIChatModel(model, provider=OllamaProvider(base_url=OLLAMA_V1)),
        output_type=Answer,
        instructions=SYSTEM,
        toolsets=[toolset],
        retries=retries,
    )
    return agent, toolset


async def ask(agent: Agent, question: str, *, timeout_s: float = 300.0) -> PydRun:
    run = PydRun(question=question)
    t0 = time.perf_counter()
    try:
        result = await asyncio.wait_for(agent.run(question), timeout=timeout_s)
        run.answer = result.output
        for msg in result.all_messages():
            for part in getattr(msg, "parts", []):
                if type(part).__name__ == "ToolCallPart":
                    run.tool_calls.append(
                        {"tool": part.tool_name, "args": part.args_as_dict(), "error": False}
                    )
                elif type(part).__name__ == "RetryPromptPart" and run.tool_calls:
                    run.tool_calls[-1]["error"] = True
        run.steps = len(result.all_messages())
    except TimeoutError:
        run.error = f"timeout after {timeout_s}s"
    except Exception as exc:  # noqa: BLE001 -- a framework failure is a result here
        run.error = f"{type(exc).__name__}: {exc}"[:300]
    run.seconds = time.perf_counter() - t0
    return run


async def _main(a) -> int:
    from regops_agents.toolcall_probe import load_sample

    items = load_sample(a.golden)[: a.n]
    agent, toolset = build(
        a.model, index=a.index, tool_error_behavior=a.tool_errors, retries=a.retries
    )
    rows: list[PydRun] = []
    async with agent:
        for i, it in enumerate(items, 1):
            r = await ask(agent, it["question"])
            rows.append(r)
            tools = ",".join(c["tool"] for c in r.tool_calls) or "-"
            cites = len(r.answer.citations) if r.answer else 0
            print(
                f"  [{i:>2}/{len(items)}] {it['id']}  {'ok ' if r.ok else 'ERR'}  "
                f"{tools[:44]:<44} cites {cites}  {r.seconds:.1f}s"
                + (f"  {r.error[:60]}" if r.error else "")
            )

    lat = sorted(r.seconds for r in rows)
    summary = {
        "framework": "pydantic-ai",
        "model": a.model,
        "tool_error_behavior": a.tool_errors,
        "retries": a.retries,
        "endpoint": "openai-compatible (/v1) — reasoning cannot be disabled, see ADR-009",
        "n": len(rows),
        "completed": sum(r.ok for r in rows),
        "called_a_tool": sum(1 for r in rows if r.tool_calls),
        "tool_calls_total": sum(len(r.tool_calls) for r in rows),
        "tool_errors": sum(1 for r in rows for c in r.tool_calls if c["error"]),
        "cited_nothing": sum(
            1 for r in rows if r.answer and r.answer.sufficient and not r.answer.citations
        ),
        "p50_s": round(lat[len(lat) // 2], 2) if lat else 0.0,
        "errors": [r.error for r in rows if r.error][:5],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        json.dumps(
            {
                "summary": summary,
                "rows": [
                    {**asdict(r), "answer": r.answer.model_dump() if r.answer else None}
                    for r in rows
                ],
            },
            indent=2,
            default=str,
        )
        + "\n"
    )
    print(f"\n{json.dumps(summary, indent=2)}\n-> {a.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    ap.add_argument("--golden", type=Path, default=Path("golden/v1/golden.jsonl"))
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--tool-errors", choices=("retry", "error", "failed"), default="retry")
    ap.add_argument("--retries", type=int, default=1, help="pydantic-ai's own default is 1")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)
    a.out = a.out or Path(f"results/day6/pydantic_ai_{a.tool_errors}_r{a.retries}.json")
    return asyncio.run(_main(a))


if __name__ == "__main__":
    raise SystemExit(main())
