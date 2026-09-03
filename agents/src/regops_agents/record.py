"""Every tool call the agent made, with its arguments and what it cost.

Day 7 measured the supervisor's retriever as *"15 hits, 11,579 chars of context"*
and that is one line for one search and five reads. Two of Day 8's deliverables
need the calls themselves: tool-call precision and recall are questions about
*which documents were read*, and a LangFuse span tree is a picture of the same
list. One recorder serves both.

It lives on the **bridge** rather than in the graph, which is the only place both
architectures pass through. Day 6's ReAct agent already harvests its calls out of
the LangChain message list (`agent._harvest`); the supervisor has no message list
to harvest. Recording at `mcp_tools` gives the two arms an identical record from
an identical place, so "the supervisor read the gold document and the single
agent did not" is a comparison of agents rather than of two bookkeeping schemes.

**The shape matches Day 6's `Run.tool_calls`** -- `tool`, `args`, `result_chars`,
`error` -- plus `seconds`, which Day 6 had no use for and a span tree does.

Risk noted in the Day 8 plan and worth restating: instrumenting the hot path can
change what is being measured. It appends a dict per call and serialises once at
the end, and `results/day8/determinism.json` re-runs the determinism check with
the recorder attached. If a single answer moved, that is a bug, not a cost.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class Recorder:
    """One list of calls, cleared between tasks by whoever owns the loop."""

    calls: list[dict] = field(default_factory=list)
    # Set by the eval harness so a call can be attributed without a second
    # structure keyed by position. `None` outside a task.
    task_id: str | None = None

    def reset(self, task_id: str | None = None) -> None:
        self.calls = []
        self.task_id = task_id

    @contextmanager
    def call(self, tool: str, args: dict):
        """Time one tool call and append it, whatever happens inside.

        Yields a one-element list the caller writes the result text into, so a
        raising tool still records the attempt: a call that blew up is exactly
        the call a trajectory metric needs to see.
        """
        rec = {
            "tool": tool,
            "args": dict(args),
            "result_chars": 0,
            "error": False,
            "seconds": 0.0,
            "task_id": self.task_id,
        }
        self.calls.append(rec)
        t0 = time.perf_counter()
        box: list[str] = [""]
        try:
            yield box
        except Exception as exc:  # noqa: BLE001 -- recorded, then re-raised
            rec["error"] = True
            rec["result_chars"] = len(f"{type(exc).__name__}: {exc}")
            raise
        finally:
            rec["seconds"] = round(time.perf_counter() - t0, 4)
            if not rec["error"]:
                text = box[0] or ""
                rec["result_chars"] = len(text)
                rec["error"] = text.startswith("TOOL ERROR")

    # -- what the metrics read ------------------------------------------------

    def documents_read(self) -> list[str]:
        """Every `doc_id` fetched in full, in call order, deduplicated.

        Reads only. A `doc_id` that merely appeared in a search *result* was not
        read by the agent, it was offered to it, and scoring an agent for what
        BM25 put in front of it measures the retriever. This is the distinction
        tool-call recall exists to make.
        """
        out: list[str] = []
        for c in self.calls:
            if c["tool"] in READ_TOOLS and not c["error"]:
                doc = str(c["args"].get("doc_id", ""))
                if doc and doc not in out:
                    out.append(doc)
        return out

    def snapshot(self) -> list[dict]:
        return [dict(c) for c in self.calls]


# Tools that fetch a named document's own content. `search_notices` is excluded
# on purpose -- see `documents_read`.
READ_TOOLS = frozenset({"get_document_section", "list_obligations", "diff_versions"})
