"""`regops-supervisor` -- one request through the graph, and the resume half.

Three modes, because the day's deliverables need three different things shown:

    regops-supervisor "question"                  run it, print the trace
    regops-supervisor "question" --thread t1      run it, stop at the interrupt
    regops-supervisor --resume t1 --approve       resume it in a *new* process

The third is the point. `--resume` shares nothing with the run that started --
no memory, no open handles, not even the same interpreter -- so a resume that
works is evidence the checkpointer did its job rather than evidence that a
variable was still in scope.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from langgraph.types import Command

from regops_agents.budget import Budget, new_spend, summary
from regops_agents.llm import MODEL
from regops_agents.supervisor import ask, running


def _pending(out: dict, thread: str) -> bool:
    """Did this call stop at an interrupt rather than finish?

    A rejection re-runs the sweep and asks again, so a resume can end in another
    interrupt. Reporting that as a finished run would print an empty answer and
    look like the graph had quietly given up.
    """
    if not out.get("__interrupt__"):
        return False
    print(json.dumps(out["__interrupt__"][0].value, indent=2)[:1200])
    print(f"\ninterrupted. resume with:\n  uv run regops-supervisor --resume {thread} --approve")
    return True


def _show(out: dict) -> None:
    for note in out.get("notes", []):
        print(f"  · {note}")
    for f in out.get("findings", []):
        mark = "x" if f["covered"] else " "
        print(f"    [{mark}] {f['title'][:52]:52} {f['section_path']}")
    cost = out.get("cost", {})
    print(
        f"\nroute {out.get('route', '-')} · steps {cost.get('steps', 0)} · "
        f"{out.get('wall_seconds', 0)}s · {cost.get('tokens', 0):,} tokens · "
        f"${cost.get('usd', 0):.6f} · stopped_by={out.get('stopped_by') or '-'}"
    )
    if out.get("violations"):
        print("violations: " + "; ".join(out["violations"]))
    print()
    print(out.get("answer", ""))


async def _run(a) -> int:
    budget = Budget(max_steps=a.max_steps, max_seconds=a.max_seconds, max_tokens=a.max_tokens)
    async with running(
        a.index,
        model=a.model,
        budget=budget,
        plan_and_execute=a.plan_and_execute,
        persist=a.persist or bool(a.resume),
        approve=a.approve_gate,
    ) as (app, config):
        if a.resume:
            cfg = config(a.resume)
            # `aget_state`, not `get_state`. `AsyncPostgresSaver` refuses a
            # synchronous read from the main thread outright, with a message
            # naming the fix -- which is the friendliest version of this failure
            # and is worth contrasting with F9, where the framework said nothing.
            state = await app.aget_state(cfg)
            if not state.next:
                print(f"thread {a.resume!r} has nothing pending — it already finished.")
                return 1
            print(f"resuming {a.resume!r} at {state.next[0]!r}")
            for task in state.tasks:
                for itr in task.interrupts:
                    print(json.dumps(itr.value, indent=2)[:1200])
            decision = "approve" if a.approve else (a.reject or "rejected")
            out = await app.ainvoke(Command(resume=decision), cfg)
            for note in out.get("notes", []):
                print(f"  · {note}")
            if _pending(out, a.resume):
                return 0
            # The cost of the *whole* run, not of the resume. `spend` came back
            # out of the checkpoint carrying what the first process paid, which
            # is the only reading of "what did this run cost" that is true.
            out["cost"] = summary(out.get("spend") or new_spend(), budget)
            out["notes"] = []
            _show(out)
            return 0

        out = await ask(app, config, a.question, thread=a.thread)
        if _pending(out, out["thread_id"]):
            return 0
        _show(out)
        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="regops-supervisor", description=__doc__)
    ap.add_argument("question", nargs="?", default="")
    ap.add_argument("--index", type=Path, default=Path("index/regdocs.duckdb"))
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--thread", default=None, help="name the run, so it can be resumed")
    ap.add_argument("--resume", default=None, metavar="THREAD", help="resume a paused run")
    ap.add_argument("--approve", action="store_true", help="with --resume: approve the report")
    ap.add_argument("--reject", default="", metavar="REASON", help="with --resume: send it back")
    ap.add_argument(
        "--approve-gate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="stop for human approval before a coverage report is finalised",
    )
    ap.add_argument(
        "--persist",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="checkpoint to Postgres rather than to memory; required to resume",
    )
    ap.add_argument("--plan-and-execute", action="store_true", help="the Phase 5 variant")
    ap.add_argument("--max-steps", type=int, default=Budget().max_steps)
    ap.add_argument("--max-seconds", type=float, default=Budget().max_seconds)
    ap.add_argument("--max-tokens", type=int, default=Budget().max_tokens)
    a = ap.parse_args(argv)

    if not a.question and not a.resume:
        ap.error("give a question, or --resume a thread")
    return asyncio.run(_run(a))


if __name__ == "__main__":
    raise SystemExit(main())
