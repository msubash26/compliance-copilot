"""Parent-child chunking, where the parent is the clause.

Most corpora have to invent a parent window -- a fixed number of neighbouring
chunks, or a sliding page. MAS numbering hands us a real one: the clause is a
unit the document itself declares, a compliance officer cites it by number, and
`get_document_section(doc_id, section_path)` already returns exactly that. So
the retrieval design and the Day 1 tool surface agree by construction rather
than by coincidence (ADR-014).

Children exist only because embedding models have a context limit and long
advisory prose dilutes a vector. Notices have a median section of 439
characters and guidelines 825, so most clauses are a single chunk and the
parent-child relation is 1:1 -- the split is the exception, not the rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# nomic-embed-text runs a 2048-token context. ~4 chars/token puts a hard ceiling
# near 8000 characters; 1200 keeps a chunk well inside it and keeps a single
# retrieved clause small enough to be worth citing.
MAX_CHUNK_CHARS = 1200
# Enough to carry a sentence across a split, so an obligation spanning the seam
# is still retrievable from either side.
OVERLAP_CHARS = 150
MIN_TAIL_CHARS = 120

_PARA_RE = re.compile(r"\n\s*\n")
# A sentence end, or the end of a lettered limb -- "(a) ...;" is a natural seam
# in legal drafting and a better split point than a bare full stop.
_SENT_RE = re.compile(r"(?<=[.;:])\s+(?=[A-Z(])|\n")


@dataclass
class Chunk:
    ordinal: int
    text: str

    @property
    def char_len(self) -> int:
        return len(self.text)


def _pieces(text: str) -> list[str]:
    """Split into the smallest units we are willing to keep whole."""
    out: list[str] = []
    for para in _PARA_RE.split(text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= MAX_CHUNK_CHARS:
            out.append(para)
            continue
        for sent in _SENT_RE.split(para):
            sent = sent.strip()
            if not sent:
                continue
            # A single sentence longer than the budget is split on words rather
            # than mid-token; legal prose does produce these.
            while len(sent) > MAX_CHUNK_CHARS:
                cut = sent.rfind(" ", 0, MAX_CHUNK_CHARS)
                cut = cut if cut > MAX_CHUNK_CHARS // 2 else MAX_CHUNK_CHARS
                out.append(sent[:cut].strip())
                sent = sent[cut:].strip()
            if sent:
                out.append(sent)
    return out


def split_section(text: str) -> list[Chunk]:
    """One clause -> its child chunks. Short clauses stay whole, which is most of them."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= MAX_CHUNK_CHARS:
        return [Chunk(0, text)]

    chunks: list[str] = []
    buf = ""
    for piece in _pieces(text):
        candidate = f"{buf}\n{piece}" if buf else piece
        if len(candidate) <= MAX_CHUNK_CHARS:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
            tail = buf[-OVERLAP_CHARS:]
            # Start the overlap at a word boundary so the seam is readable.
            cut = tail.find(" ")
            buf = (tail[cut + 1 :] if cut != -1 else tail) + "\n" + piece
        else:
            buf = piece
        while len(buf) > MAX_CHUNK_CHARS:
            chunks.append(buf[:MAX_CHUNK_CHARS])
            buf = buf[MAX_CHUNK_CHARS - OVERLAP_CHARS :]
    if buf.strip():
        # A scrap of a tail belongs on the previous chunk, not on its own.
        if chunks and len(buf) < MIN_TAIL_CHARS:
            chunks[-1] = f"{chunks[-1]}\n{buf}"
        else:
            chunks.append(buf)
    return [Chunk(i, c.strip()) for i, c in enumerate(chunks) if c.strip()]
