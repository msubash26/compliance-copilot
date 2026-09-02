"""Fixtures for the retrieval suite. Nothing here loads a model.

Not named `conftest.py`: pytest's default import mode resolves test modules by
basename, and `ingest/tests/` and `evals/tests/` already own both spellings of
that name. Each test file imports the fixtures it needs instead, which is one
line of noise in exchange for a suite that collects.

The cross-encoder is 1.33 GB of weights and CI has no GPU, so the reranking
*pipeline* is tested against a stub scorer -- which is the part that can be
wrong in a way a results table would hide -- and the real model is exercised in
one test marked `slow`.
"""

from __future__ import annotations

import duckdb
import pytest
from regdocs_mcp.index import SCHEMA_SQL
from regops_ingest.load import EXTRA_SCHEMA_SQL
from regops_retrieval.index import CTX_EMBED_MODEL, DIM, EMBED_MODEL, Index

# Two documents, four clauses. The two `6.14`s are the entity-class
# near-duplication the real corpus exhibits: same topic, different institution.
CLAUSES = [
    (
        "d0000001",
        "6.14",
        "A bank shall identify the beneficial owner of every customer and take "
        "reasonable measures to verify that identity before establishing business relations.",
    ),
    (
        "d0000001",
        "6.15",
        "A bank shall not open an anonymous account or an account in a fictitious name.",
    ),
    (
        "d0000002",
        "6.14",
        "A merchant bank shall identify the beneficial owner of every customer and take "
        "reasonable measures to verify that identity before establishing business relations.",
    ),
    (
        "d0000002",
        "9.1",
        "A merchant bank shall retain records of every transaction for five years "
        "after the completion of the transaction.",
    ),
]

# A clause long enough that the context budget has to act on it.
LONG_CLAUSE = ("d0000002", "12.1", "obligation " * 20_000)


def _v(*head: float) -> list[float]:
    return list(head) + [0.0] * (DIM - len(head))


VECTORS = {
    "d0000001:6.14": _v(1.0, 0.0, 0.0),
    "d0000002:6.14": _v(0.99, 0.14, 0.0),
    "d0000001:6.15": _v(0.0, 1.0, 0.0),
    "d0000002:9.1": _v(0.0, 0.0, 1.0),
    "d0000002:12.1": _v(0.0, 0.7, 0.7),
}


@pytest.fixture
def index_path(tmp_path):
    p = tmp_path / "fixture.duckdb"
    conn = duckdb.connect(str(p))
    conn.execute(SCHEMA_SQL)
    conn.execute(EXTRA_SCHEMA_SQL)
    for doc_id, title in (
        ("d0000001", "Notice 626 Prevention of Money Laundering - Banks"),
        ("d0000002", "Notice 1014 Prevention of Money Laundering - Merchant Banks"),
    ):
        conn.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                doc_id,
                "MAS",
                "notices",
                title,
                f"https://x/{doc_id}.pdf",
                None,
                "sha",
                None,
                "2024-03-28",
                2,
            ],
        )
    rows = [*CLAUSES, LONG_CLAUSE]
    for i, (doc_id, path, text) in enumerate(rows):
        conn.execute(
            "INSERT INTO sections VALUES (?,?,?,?,?,?,?,?,?)",
            [f"{doc_id}:{path}", doc_id, path, None, i, text, len(text), 1, 1],
        )
    conn.execute("INSTALL vss; LOAD vss;")
    # Two chunks per clause, so the parent-child ablation has something to
    # ablate: a clause can occupy two slots of a chunk-mode ranking.
    for doc_id, path, text in rows:
        uid = f"{doc_id}:{path}"
        halves = [text[: len(text) // 2], text[len(text) // 2 :]]
        for j, part in enumerate(halves):
            cid = f"{uid}#{j}"
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?)",
                [cid, doc_id, uid, j, part, f"context for {uid}", len(part), None],
            )
            for model in (EMBED_MODEL, CTX_EMBED_MODEL):
                conn.execute(
                    "INSERT INTO embeddings VALUES (?,?,?,?)", [cid, model, DIM, VECTORS[uid]]
                )
    conn.execute("PRAGMA create_fts_index('sections', 'section_uid', 'text', 'heading')")
    conn.close()
    return p


@pytest.fixture
def index(index_path):
    ix = Index(index_path)
    yield ix
    ix.close()


class StubVectors:
    """A `QuestionVectors` that answers from a table instead of from Ollama."""

    def __init__(self, table: dict[str, list[float]]) -> None:
        self.table = table
        self.touched: list[tuple[str, bool]] = []

    def __len__(self) -> int:
        return len(self.table)

    def get(self, question: str) -> list[float]:
        self.touched.append((question, True))
        return self.table.get(question, _v(1.0, 0.0, 0.0))

    def cost(self, question: str) -> float:
        return 0.0

    def reset(self) -> None:
        self.touched = []

    def replay_cost(self) -> float:
        return 0.0

    def warm(self, questions) -> None:
        for q in questions:
            self.get(q)


@pytest.fixture
def vectors():
    return StubVectors({"beneficial owner": _v(1.0, 0.0, 0.0)})
