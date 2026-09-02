"""Read-only access to the Day 3 index, and the corpus facts Day 4 selects on.

This module is deliberately the only place that knows SQL. Selection,
verification and the saturation gate all need the same three things -- resolve a
clause, search for one, and count how crowded its neighbourhood is -- and it
matters that "search" means exactly the same thing in all three, because the
gate's number is only comparable to Day 5's if they ran the same retriever.

The corpus facts encoded here were measured, not assumed. See `docs/` and the
Day 4 plan's research section for the counts each regex was validated against.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import duckdb
import httpx

EMBED_MODEL = "nomic-embed-text:latest"
DIM = 768

# A MAS instrument code as it appears at the head of a title: "626", "626A",
# "FAA-N06", "SFA 04-N02", "PSN01AA". 313 of 463 documents carry one; the 24
# codes held by two documents are always a notice and its guidelines, which
# `doc_type` separates.
CODE_RE = re.compile(
    r"\b(?:MAS\s+)?(?:Notice\s+)?("
    r"(?:[A-Z]{2,7}\s?\d{0,2}[A-Z]{0,2}-N\d{2}[A-Z]?)"  # FAA-N06, SFA 04-N02
    r"|(?:PSN\d{2}[A-Z]{0,2})"  # PSN01AA
    r"|(?:\d{3,4}[A-Z]?)"  # 626, 626A, 1014
    r")\b"
)

# The entity class a notice binds, as MAS writes it: after an en-dash, or after
# "to". This is the discriminator that makes near-duplicate notices separable.
# After the dash MAS names the class, but it does so in prose: curly apostrophes,
# trailing parentheticals ("Variable Capital Companies (VCCs)"), slashes. A strict
# character class loses roughly a third of them, so this splits and then checks.
# The separator is an en-dash, or a hyphen with spaces around it. A bare hyphen
# is not a separator -- "Trustee-Managers" and "Cross-Border" contain one.
ENTITY_TAIL_RE = re.compile(r"(?:[–—]|\s-\s)\s*([^–—]{4,90})\s*$")
ENTITY_TO_RE = re.compile(
    r"\bNotice\s+[A-Z0-9\- ]{3,12}\s+to\s+((?:the\s+)?[A-Z][^,]{3,60}?)\s+on\s+Prevention\b"
)

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

# Selection floor. Below this a clause is a heading fragment or a cross-reference
# stub, not something carrying a citable obligation.
MIN_CLAUSE_CHARS = 200

# A clause that binds someone says so, and MAS is formulaic about it. This is
# what separates a requirement from a definition, a scope list or an exemption
# schedule -- all of which are long, look substantive, and are near-identical
# across the parallel notices, so they survive every other filter. Asking two
# institutions to be compared on an exemption list produces a question whose
# honest answer is "identically, it is the same boilerplate". 5,949 of the 7,993
# eligible clauses carry one of these.
OBLIGATION_RE = re.compile(
    r"\b(shall|must|is required to|are required to|should|may not|shall not)\b", re.I
)


def base_url() -> str:
    raw = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return raw.rstrip("/").removesuffix("/v1")


def embed_one(text: str, *, model: str = EMBED_MODEL) -> list[float]:
    r = httpx.post(f"{base_url()}/api/embed", json={"model": model, "input": [text]}, timeout=120.0)
    r.raise_for_status()
    return r.json()["embeddings"][0]


def notice_code(title: str) -> str | None:
    m = CODE_RE.search(title)
    return re.sub(r"\s+", " ", m.group(1)).strip().upper() if m else None


def entity_class(title: str) -> str | None:
    """The class of institution a notice binds, or None when the title does not say.

    Two shapes, both common: "... – Merchant Banks" and "Notice X to Approved
    Trustees on Prevention of ...". Titles that name no class (the cross-border
    arrangement notices, FSM-N27) return None honestly rather than being forced.
    """
    m = ENTITY_TO_RE.search(title)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    m = ENTITY_TAIL_RE.search(title.strip())
    if not m:
        return None
    tail = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(".")
    # A class is a noun phrase, not a sentence or a citation.
    if not tail[:1].isupper() or len(tail.split()) > 10:
        return None
    return tail


@dataclass(frozen=True)
class Clause:
    doc_id: str
    section_path: str
    heading: str | None
    text: str
    title: str
    doc_type: str
    effective_date: str | None

    @property
    def section_uid(self) -> str:
        return f"{self.doc_id}:{self.section_path}"

    @property
    def code(self) -> str | None:
        return notice_code(self.title)

    @property
    def entity(self) -> str | None:
        return entity_class(self.title)


class Index:
    """A read-only handle on the Day 3 index."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.conn = duckdb.connect(str(path), read_only=True)
        self.conn.execute("INSTALL vss; LOAD vss;")
        self.conn.execute("INSTALL fts; LOAD fts;")

    def close(self) -> None:
        self.conn.close()

    # -- documents ---------------------------------------------------------

    def documents(self) -> list[tuple[str, str, str, str | None]]:
        return self.conn.execute(
            "SELECT doc_id, doc_type, title, CAST(effective_date AS VARCHAR) FROM documents"
        ).fetchall()

    def code_map(self) -> dict[str, dict[str, str]]:
        """`{code: {doc_type: doc_id}}` -- how a citation resolves to a document."""
        out: dict[str, dict[str, str]] = defaultdict(dict)
        for doc_id, doc_type, title, _ in self.documents():
            code = notice_code(title)
            if code:
                out[code][doc_type] = doc_id
        return dict(out)

    def guideline_parents(self) -> dict[str, str]:
        """`{guidelines doc_id: the notice doc_id it annotates}`, by shared code."""
        return {
            v["guidelines"]: v["notices"]
            for v in self.code_map().values()
            if "guidelines" in v and "notices" in v
        }

    # -- clauses -----------------------------------------------------------

    _CLAUSE_COLS = """
        s.doc_id, s.section_path, s.heading, s.text,
        d.title, d.doc_type, CAST(d.effective_date AS VARCHAR)
    """

    def eligible_clauses(
        self, min_chars: int = MIN_CLAUSE_CHARS, *, obligations_only: bool = False
    ) -> list[Clause]:
        """Clauses a question can be written from.

        Excludes front matter (path `0`), the 237 opaque `#N` paths that ADR-014
        could not qualify -- neither is citable -- and anything too short to
        carry an obligation.

        `obligations_only` additionally drops clauses that state no duty. It is
        off by default because two query types legitimately need clauses that
        state none: a `temporal` item is grounded in an amendment endnote, which
        records rather than binds, and a `multi_hop` item often starts from a
        guidelines paragraph explaining a notice.
        """
        rows = self.conn.execute(
            f"""
            SELECT {self._CLAUSE_COLS} FROM sections s JOIN documents d USING (doc_id)
            WHERE s.section_path <> '0' AND s.section_path NOT LIKE '%#%' AND s.char_len >= ?
            ORDER BY s.doc_id, s.ordinal
            """,
            [min_chars],
        ).fetchall()
        out = [Clause(*r) for r in rows]
        return [c for c in out if OBLIGATION_RE.search(c.text)] if obligations_only else out

    def clause(self, doc_id: str, section_path: str) -> Clause | None:
        row = self.conn.execute(
            f"""
            SELECT {self._CLAUSE_COLS} FROM sections s JOIN documents d USING (doc_id)
            WHERE s.doc_id = ? AND s.section_path = ?
            """,
            [doc_id, section_path],
        ).fetchone()
        return Clause(*row) if row else None

    def clauses_by_path(self, section_path: str) -> list[Clause]:
        """The same clause number across every document that has one.

        This is what makes `comparative` items possible: MAS's parallel AML/CFT
        notices share a numbering scheme, so 6.14 means the same topic in all
        of them and differs only in whom it binds.
        """
        rows = self.conn.execute(
            f"""
            SELECT {self._CLAUSE_COLS} FROM sections s JOIN documents d USING (doc_id)
            WHERE s.section_path = ? AND s.char_len >= ?
            """,
            [section_path, MIN_CLAUSE_CHARS],
        ).fetchall()
        return [Clause(*r) for r in rows]

    # -- vectors -----------------------------------------------------------

    def clause_vector(self, doc_id: str, section_path: str) -> list[float] | None:
        """A clause's vector: its first chunk's, on the plain (non-context) arm.

        First chunk by ordinal, not lexical minimum -- the Day 3 locator bug was
        exactly this mistake, and it is worth not repeating.
        """
        row = self.conn.execute(
            """
            SELECT e.vec FROM chunks c JOIN embeddings e USING (chunk_id)
            WHERE c.section_uid = ? AND e.model = ? ORDER BY c.ordinal LIMIT 1
            """,
            [f"{doc_id}:{section_path}", EMBED_MODEL],
        ).fetchone()
        return list(row[0]) if row else None

    def near_duplicates(
        self, doc_id: str, section_path: str, *, threshold: float = 0.10, limit: int = 50
    ) -> list[tuple[str, str, float]]:
        """Clauses in *other* documents within `threshold` cosine distance.

        The crowding measure the Day 4 plan's difficulty stratum is built on.
        Same-document neighbours are excluded: a clause resembling its own
        neighbour is not a retrieval hazard, a clause resembling the same clause
        in eleven sibling notices is.
        """
        vec = self.clause_vector(doc_id, section_path)
        if vec is None:
            return []
        rows = self.conn.execute(
            """
            SELECT c.doc_id, c.section_uid, MIN(array_cosine_distance(e.vec, ?::FLOAT[768])) d
            FROM embeddings e JOIN chunks c USING (chunk_id)
            WHERE e.model = ? AND c.doc_id <> ?
            GROUP BY 1, 2 HAVING d <= ? ORDER BY d LIMIT ?
            """,
            [vec, EMBED_MODEL, doc_id, threshold, limit],
        ).fetchall()
        return [(r[0], r[1], float(r[2])) for r in rows]

    # -- retrieval (one definition, used by the gate and by negatives) ------

    def search_bm25(self, question: str, k: int = 20) -> list[tuple[str, float]]:
        """BM25 over clause text. Returns (section_uid, score)."""
        rows = self.conn.execute(
            """
            SELECT section_uid, score FROM (
                SELECT section_uid, fts_main_sections.match_bm25(section_uid, ?) AS score
                FROM sections
            ) WHERE score IS NOT NULL ORDER BY score DESC LIMIT ?
            """,
            [question, k],
        ).fetchall()
        return [(r[0], float(r[1])) for r in rows]

    def search_dense(self, question: str, k: int = 20, *, vec: list[float] | None = None):
        """Dense over chunk vectors, rolled up to the parent clause (ADR-014)."""
        v = vec if vec is not None else embed_one(question)
        rows = self.conn.execute(
            """
            SELECT c.section_uid, MIN(array_cosine_distance(e.vec, ?::FLOAT[768])) d
            FROM embeddings e JOIN chunks c USING (chunk_id)
            WHERE e.model = ? GROUP BY 1 ORDER BY d LIMIT ?
            """,
            [v, EMBED_MODEL, k],
        ).fetchall()
        return [(r[0], float(r[1])) for r in rows]
