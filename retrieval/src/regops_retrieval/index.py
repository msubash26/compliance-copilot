"""Read-only access to the Day 3 index, and the one definition of "search".

This module was `regops_evals.corpus` until Day 5. It moved because the eval
package must not own the thing it evaluates: Day 6's agent needs these
retrievers and has no business importing an eval harness to get them, and a
benchmark whose retriever is defined inside the benchmark cannot be shown to
have measured the system that ships.

What stayed behind in `regops_evals.corpus` is the Day 4 *selection* vocabulary
-- cross-reference regexes, amendment endnote patterns, the leakage checker.
Those are facts about how questions were written, not about how documents are
found. `corpus.py` imports the primitives back, so every Day 4 call site reads
unchanged and the gate's baseline row is still produced by this code.

**Determinism.** Every ranked query here carries a secondary sort key. Six
identical dense queries against this index returned six different orderings on
Day 5's research pass, diverging at rank 18, because there is an exact distance
tie in the top-20 and DuckDB's parallel aggregation does not break ties in a
fixed order. `hit@k` is a set test and survived that; MRR and nDCG read the
order and did not. See ADR-022.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import duckdb
import httpx

# Decimal places every ranked score is rounded to before it is ordered.
#
# The tie-break on `section_uid` only fires on *exact* equality, and BM25 scores
# are not exactly reproducible: DuckDB sums each term's contribution in a
# parallel reduction, floating-point addition is not associative, and the same
# query returns the same score varying in its last bit
# (7.665345794357177 vs ...176). That is enough to reorder two clauses whose
# true scores are equal, and measured over 40 real questions it reordered the
# top-20 of **10 of them**. Rounding first collapses the jitter into a real tie,
# which the uid tie-break then breaks deterministically.
#
# 9 places is ~6 orders of magnitude above the observed jitter (~1e-15 at these
# magnitudes) and far below any score difference that means anything. See
# ADR-022.
ROUND_DP = 9

EMBED_MODEL = "nomic-embed-text:latest"
CTX_EMBED_MODEL = "nomic-embed-text:latest+ctx"
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

# Selection floor. Below this a clause is a heading fragment or a cross-reference
# stub, not something carrying a citable obligation.
MIN_CLAUSE_CHARS = 200

# A clause that binds someone says so, and MAS is formulaic about it. This is
# what separates a requirement from a definition, a scope list or an exemption
# schedule -- all of which are long, look substantive, and are near-identical
# across the parallel notices, so they survive every other filter. 5,949 of the
# 7,993 eligible clauses carry one of these.
OBLIGATION_RE = re.compile(
    r"\b(shall|must|is required to|are required to|should|may not|shall not)\b", re.I
)


def base_url() -> str:
    raw = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return raw.rstrip("/").removesuffix("/v1")


def embed_one(text: str, *, model: str = EMBED_MODEL) -> list[float]:
    # The `+ctx` arm is a *chunk-side* variant: the same embedder, run over
    # context-prepended chunk text. A query is embedded plainly on both arms,
    # so the model name is stripped before the call.
    r = httpx.post(
        f"{base_url()}/api/embed",
        json={"model": model.removesuffix("+ctx"), "input": [text]},
        timeout=120.0,
    )
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


@dataclass(frozen=True)
class Chunk:
    """A child chunk, and the clause it belongs to (ADR-014)."""

    chunk_id: str
    section_uid: str
    ordinal: int
    text: str
    context_text: str | None


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

    def clause_by_uid(self, section_uid: str) -> Clause | None:
        doc_id, _, path = section_uid.partition(":")
        return self.clause(doc_id, path)

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

    # -- chunks ------------------------------------------------------------

    def chunks(self, chunk_ids: list[str]) -> dict[str, Chunk]:
        """The child chunks behind a set of ids, for the parent-child ablation."""
        if not chunk_ids:
            return {}
        rows = self.conn.execute(
            f"""
            SELECT chunk_id, section_uid, ordinal, text, context_text FROM chunks
            WHERE chunk_id IN ({",".join("?" * len(chunk_ids))})
            """,
            chunk_ids,
        ).fetchall()
        return {r[0]: Chunk(*r) for r in rows}

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
            f"""
            SELECT c.doc_id, c.section_uid, MIN(array_cosine_distance(e.vec, ?::FLOAT[768])) d
            FROM embeddings e JOIN chunks c USING (chunk_id)
            WHERE e.model = ? AND c.doc_id <> ?
            GROUP BY 1, 2 HAVING d <= ? ORDER BY round(d, {ROUND_DP}), c.section_uid LIMIT ?
            """,
            [vec, EMBED_MODEL, doc_id, threshold, limit],
        ).fetchall()
        return [(r[0], r[1], float(r[2])) for r in rows]

    # -- retrieval (one definition, used by the gate, the sweep and the agent) --

    def search_bm25(self, question: str, k: int = 20) -> list[tuple[str, float]]:
        """BM25 over clause text. Returns (section_uid, score), ties broken by uid."""
        rows = self.conn.execute(
            f"""
            SELECT section_uid, score FROM (
                SELECT section_uid, fts_main_sections.match_bm25(section_uid, ?) AS score
                FROM sections
            ) WHERE score IS NOT NULL ORDER BY round(score, {ROUND_DP}) DESC, section_uid LIMIT ?
            """,
            [question, k],
        ).fetchall()
        return [(r[0], float(r[1])) for r in rows]

    def search_dense(
        self,
        question: str,
        k: int = 20,
        *,
        vec: list[float] | None = None,
        model: str = EMBED_MODEL,
    ) -> list[tuple[str, float]]:
        """Dense over chunk vectors, rolled up to the parent clause (ADR-014)."""
        v = vec if vec is not None else embed_one(question, model=model)
        rows = self.conn.execute(
            f"""
            SELECT c.section_uid, MIN(array_cosine_distance(e.vec, ?::FLOAT[768])) d
            FROM embeddings e JOIN chunks c USING (chunk_id)
            WHERE e.model = ? GROUP BY 1 ORDER BY round(d, {ROUND_DP}), c.section_uid LIMIT ?
            """,
            [v, model, k],
        ).fetchall()
        return [(r[0], float(r[1])) for r in rows]

    def search_dense_chunks(
        self,
        question: str,
        k: int = 20,
        *,
        vec: list[float] | None = None,
        model: str = EMBED_MODEL,
    ) -> list[tuple[str, str, float]]:
        """The same search without the roll-up: (chunk_id, section_uid, distance).

        This is the parent-child ablation's retrieval unit. Two clauses can now
        be represented by four chunks in the top 5, which is exactly the effect
        the ablation exists to measure.
        """
        v = vec if vec is not None else embed_one(question, model=model)
        rows = self.conn.execute(
            f"""
            SELECT c.chunk_id, c.section_uid, array_cosine_distance(e.vec, ?::FLOAT[768]) d
            FROM embeddings e JOIN chunks c USING (chunk_id)
            WHERE e.model = ? ORDER BY round(d, {ROUND_DP}), c.chunk_id LIMIT ?
            """,
            [v, model, k],
        ).fetchall()
        return [(r[0], r[1], float(r[2])) for r in rows]

    def search_bm25_chunks(self, question: str, k: int = 20) -> list[tuple[str, str, float]]:
        """BM25 over chunk text, for the parent-child ablation's lexical arm.

        The FTS index built on Day 3 covers `sections`, not `chunks`, so this
        scores clauses and then attributes the score to that clause's chunks by
        ordinal. It is an approximation, and it is the honest one available
        without building a second FTS index: the ablation is about the *unit of
        assembly*, and the lexical arm's clause ordering is unchanged by it.
        """
        out: list[tuple[str, str, float]] = []
        for uid, score in self.search_bm25(question, k):
            rows = self.conn.execute(
                "SELECT chunk_id FROM chunks WHERE section_uid = ? ORDER BY ordinal", [uid]
            ).fetchall()
            out += [(r[0], uid, score) for r in rows]
        return out[:k]
