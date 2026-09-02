"""Metrics against values worked out by hand.

A wrong retriever shows up as a bad number. A wrong metric shows up as a *good*
number, consistently, in every cell, and nothing downstream can detect it. So
every case here has its arithmetic written next to it, and the cases chosen are
the degenerate ones -- the ones that produce plausible-looking wrong answers
rather than obvious ones.
"""

from __future__ import annotations

import math

import pytest
from regops_evals.metrics import (
    full_at_k,
    hit_at_k,
    mrr,
    ndcg_at_k,
    percentile,
    recall_at_k,
    score_ranking,
)

A, B, C, D = "a", "b", "c", "d"


def test_nothing_retrieved_is_zero_everywhere():
    ranked, gold = [C, D], {A, B}
    assert hit_at_k(ranked, gold, 5) == 0.0
    assert recall_at_k(ranked, gold, 5) == 0.0
    assert full_at_k(ranked, gold, 5) == 0.0
    assert mrr(ranked, gold) == 0.0
    assert ndcg_at_k(ranked, gold, 10) == 0.0


def test_gold_at_rank_one():
    ranked, gold = [A, C, D], {A}
    assert hit_at_k(ranked, gold, 1) == 1.0
    assert mrr(ranked, gold) == 1.0
    # DCG = 1/log2(2) = 1; IDCG likewise.
    assert ndcg_at_k(ranked, gold, 10) == 1.0


def test_everything_retrieved():
    ranked, gold = [A, B], {A, B}
    assert full_at_k(ranked, gold, 2) == 1.0
    assert recall_at_k(ranked, gold, 2) == 1.0
    assert ndcg_at_k(ranked, gold, 10) == 1.0


def test_hit_is_any_and_full_is_all():
    """The distinction the multi-span types live on: one hop of two is not two."""
    ranked, gold = [A, C, D], {A, B}
    assert hit_at_k(ranked, gold, 5) == 1.0
    assert full_at_k(ranked, gold, 5) == 0.0
    assert recall_at_k(ranked, gold, 5) == 0.5


def test_k_truncates_before_the_set_test():
    ranked, gold = [C, D, A], {A}
    assert hit_at_k(ranked, gold, 2) == 0.0
    assert hit_at_k(ranked, gold, 3) == 1.0
    # MRR reads the whole list; it is not a @k metric.
    assert mrr(ranked, gold) == pytest.approx(1 / 3)


def test_fewer_results_than_k():
    """A short list must not be padded, and must not raise."""
    ranked, gold = [A], {A, B}
    assert hit_at_k(ranked, gold, 20) == 1.0
    assert full_at_k(ranked, gold, 20) == 0.0
    assert recall_at_k(ranked, gold, 20) == 0.5
    assert hit_at_k([], gold, 5) == 0.0
    assert mrr([], gold) == 0.0


def test_mrr_takes_the_first_gold_not_the_best():
    ranked, gold = [C, A, B], {A, B}
    assert mrr(ranked, gold) == pytest.approx(0.5)


def test_ndcg_hand_computed_two_spans():
    """Gold at ranks 2 and 4 of a 4-item list.

    DCG  = 1/log2(3) + 1/log2(5) = 0.63093 + 0.43068 = 1.06161
    IDCG = 1/log2(2) + 1/log2(3) = 1.0     + 0.63093 = 1.63093
    """
    ranked, gold = [C, A, D, B], {A, B}
    expected = (1 / math.log2(3) + 1 / math.log2(5)) / (1 + 1 / math.log2(3))
    assert ndcg_at_k(ranked, gold, 10) == pytest.approx(expected)
    assert expected == pytest.approx(0.65093, abs=1e-5)


def test_ndcg_ideal_is_capped_at_k():
    """Three gold spans but k=2: the ideal is two, not three, or nDCG can never reach 1."""
    ranked, gold = [A, B], {A, B, C}
    assert ndcg_at_k(ranked, gold, 2) == pytest.approx(1.0)


def test_duplicate_uids_are_credited_once():
    """Chunk-mode rankings name a clause more than once.

    Credit it twice and the ablation measures the metric. Remove it before
    truncation and the chunk configuration is handed distinct clauses it never
    retrieved. So: keep the position, credit the clause once.
    """
    ranked, gold = [A, A, B], {A, B}
    assert full_at_k(ranked, gold, 3) == 1.0
    assert full_at_k(ranked, gold, 2) == 0.0  # top-2 is [a, a]: b is not there
    assert recall_at_k(ranked, gold, 2) == 0.5
    # DCG credits `a` at rank 1 and `b` at rank 3, not `a` twice.
    expected = (1 + 1 / math.log2(4)) / (1 + 1 / math.log2(3))
    assert ndcg_at_k(ranked, gold, 10) == pytest.approx(expected)


def test_empty_gold_is_zero_not_one():
    """A negative has no gold span. Every rank metric must decline to score it.

    Returning 1.0 for "the empty set is a subset of anything" would silently
    give the 35 negatives a perfect recall row.
    """
    assert full_at_k([A, B], set(), 5) == 0.0
    assert recall_at_k([A, B], set(), 5) == 0.0
    assert ndcg_at_k([A, B], set(), 5) == 0.0


def test_percentile_is_nearest_rank():
    """A reported p95 must be a latency some query actually had."""
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert percentile(vals, 50) == 3.0
    assert percentile(vals, 100) == 5.0
    assert percentile(vals, 1) == 1.0
    assert percentile([], 95) == 0.0


def test_score_ranking_reports_every_column():
    got = score_ranking([A, B], {A})
    assert set(got) >= {"hit@5", "recall@5", "full@5", "hit@20", "ndcg@10", "mrr"}
    assert got["mrr"] == 1.0
