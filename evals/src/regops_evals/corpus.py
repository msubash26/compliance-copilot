"""The Day 4 corpus vocabulary, over the Day 5 retrieval primitives.

Until Day 5 this module owned both: the read-only index handle *and* the
regexes Day 4 used to pick clauses out of it. The first of those moved to
`regops_retrieval` (ADR-020) -- an eval package should not own the retriever it
evaluates, and Day 6's agent needs the same `Index` without importing a
harness. The primitives are imported back under their old names so every Day 4
call site reads unchanged, and so the gate's baseline row is still produced by
the code the sweep runs.

What is left here is what genuinely belongs to *building questions*: how a
cross-reference is spelled, how an amendment endnote is written, and what
counts as a question leaking its own source. Those are facts about the Day 4
artifact, not about search.

The corpus facts encoded here were measured, not assumed. See `docs/` and the
Day 4 plan's research section for the counts each regex was validated against.
"""

from __future__ import annotations

import re

from regops_retrieval.index import (
    CODE_RE,
    CTX_EMBED_MODEL,
    DIM,
    EMBED_MODEL,
    ENTITY_TAIL_RE,
    ENTITY_TO_RE,
    MIN_CLAUSE_CHARS,
    OBLIGATION_RE,
    Chunk,
    Clause,
    Index,
    base_url,
    embed_one,
    entity_class,
    notice_code,
)

__all__ = [
    "AMENDMENT_RE",
    "CODE_RE",
    "CTX_EMBED_MODEL",
    "DELETED_RE",
    "DIM",
    "EMBED_MODEL",
    "ENTITY_TAIL_RE",
    "ENTITY_TO_RE",
    "LEAK_PATTERNS",
    "MIN_CLAUSE_CHARS",
    "OBLIGATION_RE",
    "XREF_NOTICE_PARA",
    "XREF_PARA_OF",
    "XREF_THE_NOTICE",
    "Chunk",
    "Clause",
    "Index",
    "base_url",
    "embed_one",
    "entity_class",
    "notice_code",
]

# A cross-reference from one clause to a numbered paragraph of another notice.
XREF_PARA_OF = re.compile(
    r"paragraphs?\s+(\d{1,2}(?:\.\d{1,3}){0,3})[^.]{0,40}?"
    r"of\s+(?:MAS\s+)?Notice\s+([A-Z0-9\- ]{3,12}?)\b",
    re.I,
)
XREF_NOTICE_PARA = re.compile(
    r"(?:MAS\s+)?Notice\s+([A-Z0-9\- ]{3,12}?)[,\s]+paragraphs?\s+(\d{1,2}(?:\.\d{1,3}){0,3})\b",
    re.I,
)
# Inside a guidelines document, "the Notice" means the notice it annotates.
XREF_THE_NOTICE = re.compile(
    r"paragraphs?\s+(\d{1,2}(?:\.\d{1,3}){0,3})\s+of\s+the\s+Notice\b", re.I
)

AMENDMENT_RE = re.compile(
    r"([A-Z0-9][A-Za-z0-9 /\-]{1,40}\(Amendment(?:\s+No\.\s*\d+)?\)\s*\d{4})"
    r"[^.]{0,200}?with effect from\s+(\d{1,2}\s+\w+\s+\d{4})",
    re.I,
)
DELETED_RE = re.compile(r"\[Deleted by ([^\]]{3,80})\]")

# A question must not name its own source. Negatives are exempt: naming a real
# instrument is what makes an unanswerable question plausible.
LEAK_PATTERNS = [
    ("notice_number", re.compile(r"\b(?:MAS\s+)?Notice\s+(?:No\.\s*)?[A-Z0-9][A-Z0-9\-]{1,11}\b")),
    (
        "instrument_code",
        re.compile(r"\b(?:[A-Z]{2,7}\s?\d{0,2}[A-Z]{0,2}-N\d{2}[A-Z]?|PSN\d{2}[A-Z]{0,2})\b"),
    ),
    (
        "paragraph_number",
        re.compile(r"\b(?:paragraph|para|clause|section)s?\s+\d{1,2}(?:\.\d{1,3})*\b", re.I),
    ),
]
