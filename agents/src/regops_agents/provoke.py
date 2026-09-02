"""Provoke the failures that have to be provoked, and record what happened.

`FAILURE_MODES.md` is the day's deliverable and the prep plan's bar is "8+
documented failures with the mitigation you applied to each". The easy way to
clear that bar is to write down whatever went wrong while building, which
produces a list of anecdotes. So every entry needs a **trigger that reproduces
it on demand**, and this module is where the triggers live.

Each function returns a dict of evidence. Nothing here asserts -- a provocation
that stops failing is a finding, not a test failure, and the write-up should say
so rather than a CI job going red on a model's good day.

Everything runs against one model, in one process, in one order: Ollama
serialises against a loaded model and this is the third day the rule has bitten.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx
from regops_retrieval.index import base_url

MODEL = "qwen3.5:9b"
TIMEOUT_S = 300.0

# A fact that cannot be in the training data and cannot be inferred, placed at
# the very front of a long prompt. If the model cannot repeat it, the front of
# the prompt is gone -- and in an agent the front of the prompt is the system
# instructions and the user's question.
NEEDLE = "The authorization code for this session is ZX-4417-QQ."


def _chat(prompt: str, *, model: str = MODEL, num_ctx: int | None = None) -> dict:
    opts: dict = {"temperature": 0.0}
    if num_ctx is not None:
        opts["num_ctx"] = num_ctx
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "think": False,
        "stream": False,
        "options": opts,
    }
    t0 = time.perf_counter()
    try:
        r = httpx.post(f"{base_url()}/api/chat", json=payload, timeout=TIMEOUT_S)
        r.raise_for_status()
        b = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        return {"error": str(exc)[:200], "wall_s": time.perf_counter() - t0}
    return {
        "text": (b.get("message", {}) or {}).get("content", ""),
        "prompt_tokens": b.get("prompt_eval_count", 0),
        "wall_s": time.perf_counter() - t0,
        "error": "",
    }


def f3_context_overflow(num_ctxs=(2048, 4096, 16384), filler_tokens: int = 8_000) -> dict:
    """Does an over-long prompt fail loudly, or quietly lose its own instructions?

    The hazard is not the default window -- this build passes 30k tokens through
    and the model reports a 262,144-token context. It is what happens when
    `num_ctx` is set *below* the prompt: the prompt is truncated from the front,
    no error is raised, and the model answers confidently from what is left.
    """
    filler = "The Reporting Bank shall maintain adequate records of each transaction. " * (
        filler_tokens // 12
    )
    prompt = f"{NEEDLE}\n\n{filler}\n\nWhat is the authorization code stated at the start?"
    rows = []
    for n in num_ctxs:
        out = _chat(prompt, num_ctx=n)
        text = out.get("text", "")
        rows.append(
            {
                "num_ctx": n,
                "prompt_tokens_evaluated": out.get("prompt_tokens", 0),
                "needle_survived": "ZX-4417-QQ" in text,
                "raised_an_error": bool(out.get("error")),
                "reply": " ".join(text.split())[:160],
            }
        )
        print(
            f"  num_ctx {n:>6}: evaluated {rows[-1]['prompt_tokens_evaluated']:>6} tokens, "
            f"needle {'kept' if rows[-1]['needle_survived'] else 'GONE'}, "
            f"error {'yes' if rows[-1]['raised_an_error'] else 'no'}"
        )
    return {"filler_target_tokens": filler_tokens, "runs": rows}


async def _agent_run(question: str, index: Path, **kw):
    from regops_agents.agent import ask, build_agent
    from regops_agents.mcp_tools import mcp_tools

    async with mcp_tools(index) as tools:
        return await ask(build_agent(tools), question, **kw)


def f5_tool_error(index: Path) -> dict:
    """A tool raises. Does the model see it, recover, or fabricate around it?

    `regdocs-mcp` returns a `ToolError` naming the recovery path (ADR-005 rule 3)
    -- an unknown `doc_id` is answered with "use search_notices to obtain a valid
    doc_id". Whether that is *used* is a different question from whether it is
    delivered.
    """
    q = (
        "Read clause 6.14 of document zzzzzzzzzzzzzzzz and tell me what it requires. "
        "That document id is correct; use it."
    )
    run = asyncio.run(_agent_run(q, index))
    errored = [c for c in run.tool_calls if c["error"]]
    after = run.tool_calls[len(errored) :] if errored else []
    return {
        "question": q,
        "tool_calls": run.tool_calls,
        "errors_seen": len(errored),
        "recovered_with_search": any(c["tool"] == "search_notices" for c in after),
        "steps": run.steps,
        "stopped_by": run.stopped_by,
        "answer": run.answer[:600],
    }


def f6_pagination(index: Path) -> dict:
    """Every list tool returns `next_cursor`. Is it ever followed?

    One page of `list_obligations` on Notice 637 is 59,307 characters. If the
    agent answers "all of them" from page one, the answer is confidently
    incomplete and nothing in it says so.
    """
    q = (
        "List every obligation in MAS Notice 637. I need the complete list, "
        "not a sample — make sure you have retrieved all of them."
    )
    run = asyncio.run(_agent_run(q, index, max_steps=16))
    return {
        "question": q,
        "tool_calls": run.tool_calls,
        "used_a_cursor": any("cursor" in (c["args"] or {}) for c in run.tool_calls),
        "list_calls": sum(1 for c in run.tool_calls if c["tool"] == "list_obligations"),
        "steps": run.steps,
        "stopped_by": run.stopped_by,
        "answer": run.answer[:600],
    }


def f7_wrong_tool(index: Path) -> dict:
    """A temporal question, and four tools of which one is about versions."""
    q = "What changed between the versions of MAS Notice 626, and when did each take effect?"
    run = asyncio.run(_agent_run(q, index, max_steps=16))
    return {
        "question": q,
        "tools_used": sorted({c["tool"] for c in run.tool_calls}),
        "called_diff_versions": any(c["tool"] == "diff_versions" for c in run.tool_calls),
        "n_searches": sum(1 for c in run.tool_calls if c["tool"] == "search_notices"),
        "repeated_search": len(
            {
                json.dumps(c["args"], sort_keys=True)
                for c in run.tool_calls
                if c["tool"] == "search_notices"
            }
        ),
        "steps": run.steps,
        "stopped_by": run.stopped_by,
        "answer": run.answer[:600],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    ap.add_argument("--out", type=Path, default=Path("results/day6/failures.json"))
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args(argv)

    plan = {
        "f3_context_overflow": lambda: f3_context_overflow(),
        "f5_tool_error": lambda: f5_tool_error(a.index),
        "f6_pagination": lambda: f6_pagination(a.index),
        "f7_wrong_tool": lambda: f7_wrong_tool(a.index),
    }
    out: dict = {"model": MODEL}
    for name, fn in plan.items():
        if a.only and name not in a.only:
            continue
        print(f"== {name}")
        out[name] = fn()
        print()

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2) + "\n")
    print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
