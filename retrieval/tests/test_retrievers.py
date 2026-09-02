"""The arms, the combinators, and the two failures that would have been silent.

RRF is four lines and every one of them is easy to get subtly wrong, so its
fused order is worked out by hand here rather than compared against itself. The
reranker's pipeline is driven by a stub, because what can be wrong in a way a
results table hides is the *plumbing* -- does it actually reorder, does it
truncate, does it keep the pool a total order -- not the cross-encoder's opinion.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from regops_retrieval.index import CTX_EMBED_MODEL, EMBED_MODEL
from regops_retrieval.retrievers import Bm25, Decomposed, Dense, Rerank, Rrf, Scored

# Fixtures live in a uniquely named module rather than a third `conftest.py`;
# see fixtures_retrieval for why.
pytest_plugins = ["fixtures_retrieval"]


class Fixed:
    """A retriever that returns a written-down ranking."""

    def __init__(self, uids: list[str], name: str = "fixed") -> None:
        self.uids = uids
        self.name = name

    def search(self, question: str, k: int) -> list[Scored]:
        return [Scored(u, u, 1.0 / (i + 1), i + 1) for i, u in enumerate(self.uids[:k])]


class StubScorer:
    """Scores by a lookup on the passage text. No model, no GPU."""

    def __init__(self, table: dict[str, float]) -> None:
        self.table = table
        self.calls = 0

    def score(self, question: str, passages: list[str]) -> list[float]:
        self.calls += 1
        return [self.table.get(p, 0.0) for p in passages]


# -- the arms --------------------------------------------------------------


def test_bm25_finds_the_clause_that_uses_the_words(index):
    hits = index.search_bm25("anonymous fictitious account", 5)
    assert hits and hits[0][0] == "d0000001:6.15"


def test_dense_rolls_chunks_up_to_the_parent_clause(index, vectors):
    """Two chunks per clause, one slot per clause. ADR-014's contract."""
    hits = Dense(index, vectors).search("beneficial owner", 5)
    uids = [h.section_uid for h in hits]
    assert len(uids) == len(set(uids))
    assert uids[0] == "d0000001:6.14"


def test_chunk_mode_lets_one_clause_take_two_slots(index, vectors):
    """The parent-child ablation's whole mechanism, asserted rather than assumed."""
    hits = Dense(index, vectors, unit="chunk").search("beneficial owner", 4)
    assert [h.uid for h in hits][:2] == ["d0000001:6.14#0", "d0000001:6.14#1"]
    assert hits[0].section_uid == hits[1].section_uid == "d0000001:6.14"


def test_the_contextual_arm_is_a_different_embedding_table(index, vectors):
    plain = Dense(index, vectors, model=EMBED_MODEL).search("beneficial owner", 3)
    ctx = Dense(index, vectors, model=CTX_EMBED_MODEL).search("beneficial owner", 3)
    assert [h.uid for h in plain] and [h.uid for h in ctx]
    assert Dense(index, vectors, model=CTX_EMBED_MODEL).model.endswith("+ctx")


def test_dense_scores_are_similarity_not_distance(index, vectors):
    """Fusion and reporting must never have to remember which way is better."""
    hits = Dense(index, vectors).search("beneficial owner", 3)
    assert hits[0].score >= hits[-1].score


# -- determinism -----------------------------------------------------------


def test_the_same_query_twice_is_byte_identical(index, vectors):
    """Six identical dense queries once returned six orderings (ADR-022).

    `hit@k` is a set test and survived that. MRR and nDCG read the order and did
    not, so a benchmark without this property cannot support a two-point claim.
    """
    arm = Rrf((Bm25(index), Dense(index, vectors)))
    first = [(h.uid, h.rank) for h in arm.search("beneficial owner", 20)]
    for _ in range(5):
        assert [(h.uid, h.rank) for h in arm.search("beneficial owner", 20)] == first


def test_ties_break_on_the_uid_not_on_thread_scheduling(index, vectors):
    """d0000001:6.14 and d0000002:6.14 are near-identical by construction."""
    runs = {
        tuple(h.uid for h in Dense(index, vectors).search("beneficial owner", 5)) for _ in range(6)
    }
    assert len(runs) == 1


def test_an_exact_score_tie_is_broken_by_uid_and_not_by_luck(index):
    """Two clauses with near-identical text score near-identically under BM25.

    The fixture's two `6.14` clauses differ only in "A bank" versus "A merchant
    bank", so a query using neither word scores them within a hair of each
    other. Whatever the engine does with that, the uid must decide.
    """
    runs = {
        tuple(u for u, _ in index.search_bm25("identify the beneficial owner", 5)) for _ in range(8)
    }
    assert len(runs) == 1
    both = [u for u in next(iter(runs)) if u.endswith(":6.14")]
    assert both == sorted(both)


@pytest.mark.slow
@pytest.mark.skipif(
    not Path("index/regdocs.duckdb").exists(),
    reason="needs the real 433 MB index; a fixture cannot reproduce float jitter",
)
def test_the_real_index_ranks_the_same_way_every_time():
    """The test that would have caught the second determinism bug.

    The first fix -- `ORDER BY score DESC, section_uid` -- was verified against
    the fixture above and passed, because a five-clause fixture with hand-written
    orthogonal vectors has no near-ties for floating-point jitter to disturb. On
    the real index it was still wrong: BM25 sums term contributions in a parallel
    reduction, float addition is not associative, and the same query returned
    scores differing in their last bit. An exact-equality tie-break never fires
    on two scores that differ by 1 ULP, so **10 of 40 real questions** reordered
    their top-20 between runs.

    A determinism test over clean synthetic data cannot find that. This one runs
    real questions against the real index, which is the only place the defect
    lives. See ADR-022.
    """
    import json

    from regops_retrieval.index import Index

    questions = [
        json.loads(line)["question"]
        for line in Path("golden/v1/golden.jsonl").read_text().splitlines()[:20]
        if line.strip()
    ]
    ix = Index(Path("index/regdocs.duckdb"))
    try:
        for q in questions:
            orders = {tuple(u for u, _ in ix.search_bm25(q, 20)) for _ in range(4)}
            assert len(orders) == 1, f"BM25 ranking is not reproducible for: {q!r}"
    finally:
        ix.close()


# -- RRF -------------------------------------------------------------------


def test_rrf_fused_order_is_the_hand_computed_one():
    """k=60. Scores, by hand:

        a: 1/61 + 1/62 = 0.016393 + 0.016129 = 0.032522   -> 1st
        b: 1/62 + 1/63 = 0.016129 + 0.015873 = 0.032002   -> 2nd
        c: 1/63 + 0    =                       0.015873   -> 3rd
        d: 0    + 1/61 =                       0.016393   -> and so d beats c

    Which is the point of the test: `d` is *first* in one arm and absent from
    the other, and it still outranks `c`, which is third in one and absent from
    the other. Getting that backwards is the classic RRF bug.
    """
    fused = Rrf((Fixed(["a", "b", "c"]), Fixed(["d", "a", "b"]))).search("q", 4)
    assert [h.uid for h in fused] == ["a", "b", "d", "c"]
    assert fused[0].score == pytest.approx(1 / 61 + 1 / 62)
    assert fused[2].score == pytest.approx(1 / 61)


def test_rrf_gives_a_missing_item_nothing_not_a_floor():
    """Crediting absences would reward whichever arm returned the shortest list."""
    fused = Rrf((Fixed(["a"]), Fixed(["a", "b", "c", "d", "e"]))).search("q", 5)
    assert fused[0].uid == "a"
    assert fused[1].score == pytest.approx(1 / 62)  # b: rank 2 in one arm only


def test_rrf_ranks_are_dense_and_one_based():
    fused = Rrf((Fixed(["a", "b"]), Fixed(["b", "a"]))).search("q", 2)
    assert [h.rank for h in fused] == [1, 2]


# -- rerank ----------------------------------------------------------------


def test_rerank_reorders_by_score(index, vectors):
    base = Fixed(["a", "b", "c"])
    scorer = StubScorer({"A": 0.1, "B": 0.9, "C": 0.5})
    out = Rerank(base, scorer, lambda h: h.uid.upper(), top_n=3).search("q", 3)
    assert [h.uid for h in out] == ["b", "c", "a"]
    assert scorer.calls == 1  # one batched call, not one per passage


def test_rerank_truncates_to_top_n_and_keeps_the_tail_below_it(index, vectors):
    """The window is scored; everything under it keeps base order, underneath."""
    base = Fixed(["a", "b", "c", "d"])
    scorer = StubScorer({"A": 0.0, "B": 1.0})
    out = Rerank(base, scorer, lambda h: h.uid.upper(), top_n=2).search("q", 4)
    assert [h.uid for h in out] == ["b", "a", "c", "d"]
    assert out[2].score < out[1].score


def test_rerank_on_an_empty_pool_does_not_raise():
    out = Rerank(Fixed([]), StubScorer({}), lambda h: h.uid, top_n=5).search("q", 5)
    assert out == []


def test_rerank_is_deterministic_when_the_scorer_ties():
    base = Fixed(["b", "a", "c"])
    scorer = StubScorer({"B": 1.0, "A": 1.0, "C": 1.0})
    runs = {
        tuple(h.uid for h in Rerank(base, scorer, lambda h: h.uid.upper()).search("q", 3))
        for _ in range(5)
    }
    assert runs == {("a", "b", "c")}  # equal scores fall back to the uid


# -- decomposition ---------------------------------------------------------


def test_decomposition_always_keeps_the_original_question():
    """A decomposer that drops the question is a strictly worse retriever.

    What C7 measures is the cost of decomposing questions that did not need it,
    not the cost of throwing the question away.
    """
    seen: list[str] = []

    class Recording(Fixed):
        def search(self, question: str, k: int):
            seen.append(question)
            return super().search(question, k)

    Decomposed(Recording(["a"]), lambda q: ["sub one", "sub two"]).search("original?", 5)
    assert seen[0] == "original?"
    assert set(seen) == {"original?", "sub one", "sub two"}


def test_decomposition_fuses_rather_than_concatenates():
    """A clause found by two sub-questions must outrank one found by either."""

    class PerQuery:
        name = "per"

        def search(self, question: str, k: int):
            table = {"q": ["a", "x"], "s1": ["a", "y"], "s2": ["b", "a"]}
            return [Scored(u, u, 1.0, i + 1) for i, u in enumerate(table[question])]

    out = Decomposed(PerQuery(), lambda q: ["s1", "s2"]).search("q", 3)
    assert out[0].uid == "a"
