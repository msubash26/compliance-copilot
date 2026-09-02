"""Turning a ranked list into the text a generator sees, under a hard budget.

The budget is not defensive tidiness. Measured over the golden set's queries,
a top-5 assembled as *clauses* is 5,848 characters at the median, 46,417 at p90
and 82,184 at the maximum, because a MAS clause can run to 127,564 characters --
one clause is longer than most people's entire context window. Assembled as
*chunks* the same top-5 is 3,156 / 4,516 / 5,916.

Without a cap the parent-mode configs would silently overflow the generator on
the tail of the distribution and score zero for groundedness, and the write-up
would read that as a retrieval result. So the budget is enforced here, and
truncation is *recorded per query* rather than hidden: "12 of 150 queries lost
text to the budget" is a measurement, and it belongs in the table next to the
groundedness number it explains.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from regops_retrieval.index import Index
from regops_retrieval.retrievers import Scored

# ~6k tokens of excerpts, leaving room for the prompt and the answer inside
# qwen3.5:9b's window. A round number, chosen not tuned (ADR-020).
CONTEXT_BUDGET = 24_000

# No single excerpt may take more than this share of the budget. Without it one
# 127K-character clause at rank 1 consumes the whole allowance and the other
# four retrieved clauses never reach the generator -- which would make the
# parent arm look like a retrieval failure when it is an assembly failure.
PER_EXCERPT_SHARE = 0.4


@dataclass
class Assembled:
    """The excerpts, and the honest accounting of what did not fit."""

    text: str
    cited: list[str] = field(default_factory=list)  # section_uids, in rank order
    chars: int = 0
    truncated_excerpts: int = 0
    dropped_excerpts: int = 0

    @property
    def truncated(self) -> bool:
        return bool(self.truncated_excerpts or self.dropped_excerpts)


def assemble_context(
    ix: Index,
    hits: list[Scored],
    *,
    mode: str = "parent",
    top_k: int = 5,
    budget: int = CONTEXT_BUDGET,
) -> Assembled:
    """Assemble the top `top_k` hits as clauses (`parent`) or chunks (`child`).

    Excerpts are numbered so the generator can cite `[1]` and the judge can
    check the citation against a known clause.
    """
    picked = hits[:top_k]
    per_excerpt = int(budget * PER_EXCERPT_SHARE)

    bodies: list[tuple[str, str, str]] = []  # (section_uid, label, text)
    if mode == "child":
        chunks = ix.chunks([h.uid for h in picked])
        for h in picked:
            ch = chunks.get(h.uid)
            if ch is None:
                continue
            cl = ix.clause_by_uid(h.section_uid)
            label = f"{cl.title} · clause {cl.section_path}" if cl else h.section_uid
            bodies.append((h.section_uid, label, ch.text))
    else:
        for h in picked:
            cl = ix.clause_by_uid(h.section_uid)
            if cl is None:
                continue
            bodies.append((h.section_uid, f"{cl.title} · clause {cl.section_path}", cl.text))

    out: list[str] = []
    cited: list[str] = []
    used = 0
    truncated = 0
    dropped = 0
    for n, (uid, label, text) in enumerate(bodies, 1):
        body = " ".join(text.split())
        head = f"[{n}] {label} ({uid})\n"
        room = min(per_excerpt, budget - used - len(head))
        if room <= 200:
            # Not enough left for an excerpt worth reading. Drop the rest, and
            # count them: a dropped excerpt is a retrieved clause the generator
            # never saw, which is exactly the confound this accounting exists
            # to keep out of the groundedness column.
            dropped += len(bodies) - n + 1
            break
        if len(body) > room:
            body = body[:room].rsplit(" ", 1)[0] + " […truncated]"
            truncated += 1
        block = head + body
        out.append(block)
        cited.append(uid)
        used += len(block) + 2

    text = "\n\n".join(out)
    return Assembled(
        text=text,
        cited=cited,
        chars=len(text),
        truncated_excerpts=truncated,
        dropped_excerpts=dropped,
    )
