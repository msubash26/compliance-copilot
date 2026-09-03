"""Thirty end-to-end tasks, derived from the golden set rather than rewritten from it.

An agent eval needs expectations a machine can check, and the tempting way to get
them is to write thirty questions with thirty hand-written answers. That produces
a second ground truth to maintain, and the two drift: `golden/v1` is re-verified
on every re-parse (`span_sha256`, ADR-016) and a hand-written task file is not.

So every task here **carries the `golden_id` it came from** and nothing else about
it is invented. The question is the golden question verbatim; `gold_doc_ids` come
from `gold_spans`; `must_abstain` is `query_type == "negative"`. A change to
`golden/v1` therefore shows up here as a **failing test** rather than as silent
drift, which is the property the derivation exists to buy.

**`min_tool_calls` is supplied by the data, not guessed.** The minimum trajectory
for a grounded task is one search plus one read per distinct gold document, and
the distinct-document count is a measured property of the taxonomy (ADR-018):

    factual_lookup  45 items   1 gold document each
    temporal        15 items   1
    multi_hop       30 items   2
    comparative     25 items   2 or 3
    negative        35 items   0 -- one search, then abstain

That makes trajectory efficiency a ratio against a principled floor rather than
against a number someone liked. It is a *floor*, not a target: an agent that
searches twice because the first query missed is doing legitimate work, and the
metric reports the raw pair beside the ratio so that a 0.5 from two calls instead
of one is distinguishable from a 0.5 from twelve instead of six.

**Selection is deterministic and prefers unflagged items.** Lowest golden id
first, `machine_verified` only -- 28 of the 150 items carry a failed verification
check, and an eval that gates a build should not be gated by an item the set
itself flags as doubtful. The negatives are stratified across all five
`absence_reason` values instead, one each, because a negative set that is five
variations of one trick measures one trick (ADR-018).

**There is no version task.** `diff_versions` is unreachable from the supervisor
by design (ADR-028 forbids model-supplied identifiers) and `regdocs-mcp` ADR-004
records that this corpus holds no genuine multi-version document. A task nothing
can pass measures the task set, not the agent.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from regops_evals.schema import GoldenItem, read_jsonl

# Proportional to the golden strata (45/30/25/15/35 of 150), rounded to 30 and
# declared here before anything is selected, so the mix is a decision.
TASK_STRATIFICATION: dict[str, int] = {
    "factual_lookup": 12,
    "multi_hop": 6,
    "comparative": 4,
    "temporal": 3,
    "negative": 5,
}

# The five reasons a negative is genuinely unanswerable (ADR-018). Five slots,
# five reasons, one each.
ABSENCE_ORDER = (
    "other_jurisdiction",
    "out_of_scope_instrument",
    "withdrawn_requirement",
    "invented_specific",
    "unregulated_topic",
)

# Day 7's three coverage tasks, held separately because their expectations are
# hand-written rather than derived -- there is no golden item for "which documents
# address X". They are reported and never gated, and this file says which is which
# by keeping them out of `tasks.jsonl` entirely.
COVERAGE_TASKS = [
    {
        "task_id": "cv-001",
        "question": (
            "Which documents in the corpus state an obligation about politically "
            "exposed persons, and which are silent on it?"
        ),
    },
    {
        "task_id": "cv-002",
        "question": (
            "Which documents in the corpus place an obligation to keep records, "
            "and which are silent on it?"
        ),
    },
    {
        "task_id": "cv-003",
        "question": (
            "Which documents in the corpus require the filing of suspicious "
            "transaction reports, and which are silent on it?"
        ),
    },
]


class Task(BaseModel):
    """One end-to-end task and the four mechanical things it expects.

    Four outcomes, because "task success" has to be something a machine decides
    or the eval is a vibe, and because each of the four fails for a different
    reason worth telling apart:

    - `gold_doc_ids` -- did the agent *read* the document that answers it
      (tool-call recall). An agent can retrieve the right clause and then write
      an answer that ignores it; this is the only outcome that sees the first
      half of that.
    - `must_cite` -- did it cite something that **resolves against the index**
      (Day 6's layer 2). Non-empty for every grounded task.
    - `must_abstain` -- did it decline on a question the corpus does not answer.
      This is the dangerous direction: a confident fabrication scores worse than
      a refusal, and 5 of these 30 tasks are here to make that visible.
    - `min_tool_calls` -- the floor from the derivation above.
    """

    model_config = {"extra": "forbid"}

    task_id: str = Field(pattern=r"^t-\d{3}$")
    golden_id: str = Field(pattern=r"^gs-\d{4}$")
    question: str
    query_type: str
    gold_doc_ids: list[str]
    gold_uids: list[str]
    must_cite: bool
    must_abstain: bool
    min_tool_calls: int = Field(ge=1)
    gold_answer: str
    absence_reason: str | None = None


def min_tool_calls(item: GoldenItem) -> int:
    """One search, plus one read per distinct gold document. See the docstring."""
    return 1 + len({sp.doc_id for sp in item.gold_spans})


def _eligible(items: list[GoldenItem], qtype: str) -> list[GoldenItem]:
    return sorted(
        (i for i in items if i.query_type == qtype and i.verification.status == "machine_verified"),
        key=lambda i: i.id,
    )


def select(items: list[GoldenItem]) -> list[GoldenItem]:
    """The thirty, deterministically. No RNG, so a re-run is the same run."""
    chosen: list[GoldenItem] = []
    for qtype, n in TASK_STRATIFICATION.items():
        pool = _eligible(items, qtype)
        if qtype == "negative":
            # One per absence reason, lowest id within each. A stratum of five
            # drawn by id alone would almost certainly be five of one reason.
            for reason in ABSENCE_ORDER[:n]:
                for it in pool:
                    if it.absence_reason == reason:
                        chosen.append(it)
                        break
        else:
            chosen.extend(pool[:n])
    return sorted(chosen, key=lambda i: i.id)


def build(golden: Path) -> list[Task]:
    items = read_jsonl(golden)
    out: list[Task] = []
    for n, it in enumerate(select(items), 1):
        docs = sorted({sp.doc_id for sp in it.gold_spans})
        out.append(
            Task(
                task_id=f"t-{n:03d}",
                golden_id=it.id,
                question=it.question,
                query_type=it.query_type,
                gold_doc_ids=docs,
                gold_uids=sorted(sp.section_uid for sp in it.gold_spans),
                must_cite=bool(docs),
                must_abstain=not docs,
                min_tool_calls=min_tool_calls(it),
                gold_answer=it.answer,
                absence_reason=it.absence_reason,
            )
        )
    return out


def read_tasks(path: Path) -> list[Task]:
    return [
        Task.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()
    ]


def write_tasks(path: Path, tasks: list[Task]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(t.model_dump(mode="json"), ensure_ascii=False) for t in tasks]
    path.write_text("\n".join(lines) + "\n")
