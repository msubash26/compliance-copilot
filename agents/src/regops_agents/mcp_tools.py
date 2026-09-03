"""LangChain tools whose schemas come from the running MCP server.

The prep plan names `langchain-mcp-adapters` for this job. It cannot do it here,
and the reason is worth writing down rather than working around silently:

    langchain-mcp-adapters 0.3.1  requires  mcp>=1.24.0      (unbounded)
    langchain-mcp-adapters 0.3.2  requires  mcp>=1.24.0,<2   (the latest release)
    regdocs-mcp                   requires  mcp>=2.1,<3      (spec 2026-07-28)

0.3.1's bound is wrong rather than permissive: it resolves happily against
`mcp` 2.1 and then dies at import on `from mcp.shared.context import
RequestContext`, a name v2 removed. 0.3.2 corrects the pin, and the corrected pin
excludes us. So the adapter ecosystem is a **major version behind the protocol**,
and the only ways to use it are to downgrade the SDK -- abandoning the spec
revision the server was built to, and breaking the server's own pin -- or to
write the bridge. The bridge is 60 lines.

What matters is not that it is small but that it keeps the property the adapter
was wanted for: **the model sees the server's own schemas**. `tools/list` is read
over real JSON-RPC and the `inputSchema` is handed to LangChain verbatim, so a
description edited in `regdocs_mcp.server` reaches the agent on the next run with
nothing here to update. A hand-written copy of four tool signatures would drift
from the server the first time one changed, and Day 6 measures what changing a
description does.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import ExitStack, asynccontextmanager
from pathlib import Path

from langchain_core.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from regops_agents.record import Recorder
from regops_agents.trace import NULL, TOOL, Tracer

# The server repo, as a sibling. It is a path dependency of this workspace
# already (ADR-001), so this is the same checkout `uv sync` installed.
SERVER_DIR = Path(__file__).resolve().parents[4] / "regdocs-mcp"

# Tool results go into a context window, and one of these can be enormous:
# `list_obligations` on Notice 637 is 59,307 characters for a single page. The
# agent's own step budget is not a defence against a single oversized result, so
# the bridge truncates and *says* it truncated -- research 6 measured that an
# over-long prompt is dropped from the front, silently, taking the system prompt
# and the question with it before it touches the tool output.
MAX_RESULT_CHARS = 12_000

# The same cap, for a consumer that is not a context window.
#
# Day 6 put the truncation here because the only consumer was a model, and for a
# model it is right: the result goes straight into a prompt. Day 7's supervisor
# is a second consumer with the opposite requirement -- it *parses* these results
# and compacts them itself, so a result cut mid-JSON is not a shortened answer,
# it is no answer. `search_notices` crosses 12,000 characters at top_k 20 on this
# corpus and `list_obligations` crosses it on its first page, and in both cases
# the graph saw zero results and no error. That is F14, and the fix is that the
# **cap belongs to the caller**: a truncation policy written for one consumer is
# not a property of the tool. Programmatic callers pass this instead.
PARSER_RESULT_CHARS = 400_000


def _render(result, limit: int = MAX_RESULT_CHARS) -> str:
    """One tool result as text, bounded by whatever the caller can hold."""
    parts = [c.text for c in (result.content or []) if getattr(c, "text", None)]
    body = "\n".join(parts) if parts else str(result.structured_content or "")
    if len(body) > limit:
        return (
            body[:limit] + f"\n\n[truncated: {len(body):,} characters returned, "
            f"{limit:,} shown. Narrow the query or page with the cursor.]"
        )
    return body


@asynccontextmanager
async def mcp_tools(
    index: Path,
    *,
    server_dir: Path = SERVER_DIR,
    max_result_chars: int = MAX_RESULT_CHARS,
    recorder: Recorder | None = None,
    tracer: Tracer = NULL,
) -> AsyncIterator[list]:
    """The server's four tools, as LangChain tools, for the life of the session.

    stdio, because it needs no running process -- the same transport the Day 1
    Claude Code registration uses, so what the agent talks to is what a user
    talks to.

    `recorder` and `tracer` are both optional and both wrap the call here rather
    than in either agent, because this is the one layer the single agent and the
    supervisor share. Instrumenting each architecture separately would produce
    two records and an argument about whether they are comparable.
    """
    # `VIRTUAL_ENV` is dropped: the server is a separate uv project, and inheriting
    # this workspace's active venv makes its `uv run` warn on every spawn.
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    params = StdioServerParameters(
        command="uv",
        args=["run", "--directory", str(server_dir), "regdocs-mcp"],
        env={**env, "REGDOCS_INDEX": str(Path(index).resolve())},
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        listed = (await session.list_tools()).tools

        def make(name: str, description: str, schema: dict) -> StructuredTool:
            async def invoke(**kwargs) -> str:
                res = await session.call_tool(name, kwargs)
                if res.is_error:
                    # The SDK delivers a tool's own ToolError here rather than
                    # raising. Handing the text back to the model is deliberate:
                    # these messages carry the recovery path (ADR-005 rule 3),
                    # and F5 measures whether the model uses it.
                    return f"TOOL ERROR from {name}: {_render(res, max_result_chars)}"
                return _render(res, max_result_chars)

            async def call(**kwargs) -> str:
                if recorder is None and not tracer.enabled:
                    return await invoke(**kwargs)
                with ExitStack() as stack:
                    obs = stack.enter_context(tracer.observe(name, as_type=TOOL, input=kwargs))
                    box = stack.enter_context(recorder.call(name, kwargs)) if recorder else [""]
                    box[0] = out = await invoke(**kwargs)
                    obs.update(
                        output=out[:2000],
                        metadata={"result_chars": len(out), "truncated": len(out) > 2000},
                    )
                    return out

            return StructuredTool.from_function(
                coroutine=call,
                name=name,
                description=description,
                args_schema=schema,  # the server's, verbatim
            )

        yield [make(t.name, t.description or "", t.input_schema) for t in listed]
