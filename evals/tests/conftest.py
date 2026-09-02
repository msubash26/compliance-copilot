"""Fixtures for the evals suite.

Nothing here calls a model. The claims worth testing are claims about our code
-- that the schema rejects a malformed item, that a moved gold span is detected
as moved rather than silently rescored, that the leakage regex fires on a real
leak and not on the word "Notice" -- and all of them are decidable without a
GPU, which is also what lets them run in CI where there is none.

The one test that does need a model is marked `llm` and skipped by default.
"""

from __future__ import annotations

import duckdb
import pytest
from regdocs_mcp.index import SCHEMA_SQL
from regops_evals.corpus import DIM, EMBED_MODEL
from regops_evals.schema import GoldenItem, Provenance, span_hash
from regops_ingest.load import EXTRA_SCHEMA_SQL

PROV = Provenance(
    generator="qwen3.5:9b",
    corpus_manifest_sha="deadbeef",
    index_built_at="2026-09-02T00:00:00",
    parser="regops-ingest@abc1234",
)

# Three duties and one definition. The definition matters: it is the shape that
# survives every other filter -- long, plausible, near-identical across notices --
# and binds nobody, which is what the obligation filter exists to drop.
CLAUSES = [
    (
        "d0000001",
        "6.14",
        "A bank shall identify the beneficial owner of every customer and "
        "take reasonable measures to verify that identity.",
    ),
    (
        "d0000001",
        "6.15",
        "A bank shall not open an anonymous account or an account in a fictitious name.",
    ),
    (
        "d0000001",
        "2.1",
        "In this Notice, unless the context otherwise requires, "
        "'beneficial owner' means the natural person who ultimately owns "
        "or controls the customer.",
    ),
    (
        "d0000002",
        "6.14",
        "A merchant bank shall identify the beneficial owner of every "
        "customer and take reasonable measures to verify that identity.",
    ),
]


# Stand-in vectors, hand-written so the geometry is the thing under test rather
# than an embedding model's opinion: the two 6.14 clauses are close to each
# other and far from everything else, which is exactly the entity-class
# near-duplication the real corpus exhibits.
# Padded to the real 768 so the tests exercise the production SQL, casts and all,
# rather than a narrowed copy of it.
def _v(*head: float) -> list[float]:
    return list(head) + [0.0] * (DIM - len(head))


VECTORS = {
    "d0000001:6.14": _v(1.0, 0.0, 0.0),
    "d0000002:6.14": _v(0.99, 0.14, 0.0),
    "d0000001:6.15": _v(0.0, 1.0, 0.0),
    "d0000001:2.1": _v(0.0, 0.0, 1.0),
}


@pytest.fixture
def index_path(tmp_path):
    """A tiny index with the same schema the real one has."""
    p = tmp_path / "fixture.duckdb"
    conn = duckdb.connect(str(p))
    conn.execute(SCHEMA_SQL)
    conn.execute(EXTRA_SCHEMA_SQL)
    for doc_id, title, dt in (
        ("d0000001", "Notice 626 Prevention of Money Laundering - Banks", "notices"),
        ("d0000002", "Notice 1014 Prevention of Money Laundering - Merchant Banks", "notices"),
    ):
        conn.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                doc_id,
                "MAS",
                dt,
                title,
                f"https://x/{doc_id}.pdf",
                None,
                "sha",
                None,
                "2024-03-28",
                2,
            ],
        )
    for i, (doc_id, path, text) in enumerate(CLAUSES):
        conn.execute(
            "INSERT INTO sections VALUES (?,?,?,?,?,?,?,?,?)",
            [f"{doc_id}:{path}", doc_id, path, None, i, text, len(text), 1, 1],
        )
    # One chunk per clause, with a vector, so near-duplicate counting and dense
    # search are exercised rather than trivially returning nothing.
    conn.execute("INSTALL vss; LOAD vss;")
    for doc_id, path, text in CLAUSES:
        uid = f"{doc_id}:{path}"
        conn.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?)",
            [f"{uid}#0", doc_id, uid, 0, text, None, len(text), None],
        )
        conn.execute(
            "INSERT INTO embeddings VALUES (?,?,?,?)",
            [f"{uid}#0", EMBED_MODEL, DIM, VECTORS[uid]],
        )
    conn.execute("PRAGMA create_fts_index('sections', 'section_uid', 'text', 'heading')")
    conn.close()
    return p


@pytest.fixture
def index(index_path):
    from regops_evals.corpus import Index

    ix = Index(index_path)
    yield ix
    ix.close()


def make_item(**kw) -> GoldenItem:
    """A valid item, with overrides. Keeps each test to the field it is about."""
    doc_id, path, text = CLAUSES[0]
    base = dict(
        id="gs-0001",
        question="When must a bank identify the beneficial owner of a customer?",
        answer="Whenever it establishes business relations with that customer.",
        query_type="factual_lookup",
        gold_spans=[
            {
                "doc_id": doc_id,
                "section_path": path,
                "span_sha256": span_hash(text),
                "why": "states the identification duty",
            }
        ],
        entity_class="Banks",
        difficulty={"near_duplicates_at_0_10": 1, "vocab_overlap": 0.2},
        provenance=PROV,
    )
    base.update(kw)
    return GoldenItem.model_validate(base)
