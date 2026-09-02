"""The declared configurations, and the reranker's one real-weights test.

The table's rows and this list are the same list. That is checkable, and it is
checked, because "the results table describes code that exists" is exactly the
claim a portfolio benchmark most needs to be able to make.
"""

from __future__ import annotations

import os

import pytest
from regops_retrieval.configs import ABLATIONS, BY_NAME, CONFIGS, DIAGNOSTICS, LADDER, build
from regops_retrieval.retrievers import Bm25, Decomposed, Dense, Rerank, Rrf

# Fixtures live in a uniquely named module rather than a third `conftest.py`;
# see fixtures_retrieval for why.
pytest_plugins = ["fixtures_retrieval"]


class StubScorer:
    def score(self, question: str, passages: list[str]) -> list[float]:
        # Reverse the base order, so a test can tell reranking happened at all.
        return [float(i) for i in range(len(passages))]


def test_there_are_seven_configurations_four_of_them_a_ladder():
    assert len(CONFIGS) == 7
    assert len(LADDER) == 4 and len(ABLATIONS) == 3
    assert [c.rung for c in LADDER] == [True] * 4
    assert [c.rung for c in ABLATIONS] == [False] * 3


def test_a_diagnostic_is_reachable_by_name_but_is_not_a_row():
    """A diagnostic supports a claim made elsewhere; it does not add a table row."""
    assert "D1_dense_plain" in BY_NAME
    assert all(d not in CONFIGS for d in DIAGNOSTICS)


def test_the_ladder_holds_contextual_and_parent_child_fixed():
    """An ablation needs a fixed reference or it means nothing."""
    assert all(c.contextual and c.parent_child and not c.decompose for c in LADDER)


def test_each_ablation_moves_exactly_one_switch_against_c4():
    c4 = BY_NAME["C4_hybrid_rerank"]
    for cfg in ABLATIONS:
        moved = [
            f
            for f in ("arms", "contextual", "parent_child", "rerank", "decompose")
            if getattr(cfg, f) != getattr(c4, f)
        ]
        assert moved == [
            {
                "C5_no_context": "contextual",
                "C6_child_units": "parent_child",
                "C7_decompose": "decompose",
            }[cfg.name]
        ], f"{cfg.name} moved {moved}"


def test_switches_drive_the_derived_settings():
    c6 = BY_NAME["C6_child_units"]
    assert c6.unit == "chunk" and c6.context_mode == "child"
    assert BY_NAME["C5_no_context"].embed_model == "nomic-embed-text:latest"
    assert BY_NAME["C4_hybrid_rerank"].embed_model.endswith("+ctx")


def test_build_produces_the_shape_each_row_claims(index, vectors, tmp_path):
    assert isinstance(build(BY_NAME["C1_bm25"], index, vectors), Bm25)
    assert isinstance(build(BY_NAME["C2_dense"], index, vectors), Dense)
    assert isinstance(build(BY_NAME["C3_hybrid_rrf"], index, vectors), Rrf)
    r4 = build(BY_NAME["C4_hybrid_rerank"], index, vectors, scorer=StubScorer())
    assert isinstance(r4, Rerank) and isinstance(r4.base, Rrf)
    r7 = build(BY_NAME["C7_decompose"], index, vectors, scorer=StubScorer(), decompose_dir=tmp_path)
    assert isinstance(r7, Decomposed) and isinstance(r7.base, Rerank)


def test_a_reranking_config_refuses_to_build_without_a_scorer(index, vectors):
    with pytest.raises(ValueError, match="scorer"):
        build(BY_NAME["C4_hybrid_rerank"], index, vectors)


def test_the_whole_c4_pipeline_runs_on_a_stub_scorer(index, vectors):
    """End to end with no model: retrieve, fuse, rerank, truncate."""
    hits = build(BY_NAME["C4_hybrid_rerank"], index, vectors, scorer=StubScorer()).search(
        "beneficial owner", 3
    )
    assert len(hits) == 3
    assert [h.rank for h in hits] == [1, 2, 3]
    assert len({h.uid for h in hits}) == 3


@pytest.mark.slow
@pytest.mark.skipif(
    os.getenv("CI") is not None or os.getenv("REGOPS_NO_RERANKER") is not None,
    reason="1.33 GB of weights and a GPU; the pipeline is covered by the stub tests",
)
def test_the_real_cross_encoder_prefers_the_relevant_clause(index, vectors):
    from regops_retrieval import rerank as rr

    scorer = rr.load()
    q = "when must a bank verify who ultimately owns a customer"
    passages = [
        "A bank shall retain records of every transaction for five years.",
        "A bank shall identify the beneficial owner of every customer and take reasonable "
        "measures to verify that identity before establishing business relations.",
    ]
    scores = scorer.score(q, passages)
    assert scores[1] > scores[0]
