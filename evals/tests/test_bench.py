"""The sweep harness: aggregation, the sensitivity split, and the gate.

The gate is the important one. C1 is BM25 and nothing else, so its row must
reproduce the number Day 4 published. If it does not, the sweep has quietly
redefined what search means and every row below it is void -- which is a failure
mode that otherwise survives all the way into a results table, because a
plausible number looks exactly like a correct one.
"""

from __future__ import annotations

from regops_evals.bench import BASELINE_TOLERANCE, Row, aggregate, check_baseline


def _row(**kw) -> Row:
    base = dict(
        config="C1_bm25",
        item_id="gs-0001",
        query_type="factual_lookup",
        flagged=False,
        gold=["d1:1.1"],
        ranked=["d1:1.1"],
        latency_s=0.1,
        embed_replay_s=0.0,
        decompose_s=0.0,
        context_chars=1000,
        context_truncated=0,
        context_dropped=0,
        metrics={"hit@5": 1.0, "mrr": 1.0},
    )
    base.update(kw)
    return Row(**base)


def test_negatives_are_retrieved_but_never_averaged_into_recall():
    """35 of 150 items have no gold span. Scoring them would be scoring nothing."""
    rows = [
        _row(metrics={"hit@5": 1.0, "mrr": 1.0}),
        _row(item_id="gs-0002", query_type="negative", gold=[], metrics={}),
    ]
    agg = aggregate(rows)
    assert agg["overall"]["n_ranked"] == 1
    assert agg["overall"]["hit@5"] == 1.0
    # Latency, though, counts every query: a production p95 does not get to
    # exclude the ones whose answer is "not in the corpus".
    assert agg["all_items"]["n"] == 2


def test_the_unflagged_run_excludes_flagged_items():
    rows = [
        _row(metrics={"hit@5": 1.0, "mrr": 1.0}),
        _row(item_id="gs-0002", flagged=True, metrics={"hit@5": 0.0, "mrr": 0.0}),
    ]
    assert aggregate(rows)["overall"]["hit@5"] == 0.5
    assert aggregate(rows, unflagged_only=True)["overall"]["hit@5"] == 1.0
    assert aggregate(rows, unflagged_only=True)["overall"]["n_ranked"] == 1


def test_truncation_is_counted_per_query_not_per_excerpt():
    rows = [
        _row(context_truncated=3),
        _row(item_id="gs-0002", context_dropped=1, context_truncated=0),
        _row(item_id="gs-0003"),
    ]
    assert aggregate(rows)["all_items"]["truncated_queries"] == 2


def test_the_baseline_gate_passes_on_the_published_numbers():
    report = {
        "configs": {
            "C1_bm25": {
                "all_150": {"overall": {"hit@5": 0.6696, "hit@20": 0.8696, "full@5": 0.4174}}
            }
        }
    }
    sat = {"overall": {"bm25_hit@5": 0.67, "bm25_hit@20": 0.87, "bm25_full@5": 0.417}}
    got = check_baseline(report, sat)
    assert got["passed"] is True
    assert len(got["checks"]) == 3


def test_the_baseline_gate_fails_when_search_was_redefined():
    """One item is 0.0087, so the tolerance is half of one item."""
    report = {
        "configs": {
            "C1_bm25": {"all_150": {"overall": {"hit@5": 0.70, "hit@20": 0.87, "full@5": 0.417}}}
        }
    }
    sat = {"overall": {"bm25_hit@5": 0.67, "bm25_hit@20": 0.87, "bm25_full@5": 0.417}}
    got = check_baseline(report, sat)
    assert got["passed"] is False
    assert [c["ok"] for c in got["checks"]] == [False, True, True]
    assert BASELINE_TOLERANCE < 1 / 115  # inside one item's worth of movement


def test_a_missing_c1_is_a_failure_not_a_pass():
    """An empty check list must never read as 'nothing disagreed'."""
    got = check_baseline({"configs": {}}, {"overall": {}})
    assert got["passed"] is False


def test_displacement_separates_wrong_documents_from_demoted_ones():
    """Why a config lost is a different question from how much.

    C7 lost 15 MRR points. That is compatible with two very different stories —
    it retrieved different documents, or it retrieved the same ones and ranked
    them worse — and only one of them is an argument about fusion.
    """
    from regops_evals.bench import displacement

    before = [
        _row(item_id="a", config="C4", ranked=["g", "x", "y"], gold=["g"]),
        _row(item_id="b", config="C4", ranked=["g", "x"], gold=["g"]),
        _row(item_id="c", config="C4", ranked=["x", "g"], gold=["g"]),
        _row(item_id="d", config="C4", ranked=["g"], gold=["g"]),
    ]
    after = [
        _row(item_id="a", config="C7", ranked=["x", "y", "g"], gold=["g"]),  # 1 -> 3
        _row(item_id="b", config="C7", ranked=["g", "x"], gold=["g"]),  # unchanged
        _row(item_id="c", config="C7", ranked=["g", "x"], gold=["g"]),  # 2 -> 1
        _row(item_id="d", config="C7", ranked=["x"], gold=["g"]),  # dropped out
    ]
    got = displacement(before, after)
    assert got["n_both_retrieved"] == 3
    assert (got["demoted"], got["unchanged"], got["promoted"]) == (1, 1, 1)
    assert got["dropped_out_of_top20"] == 1
    assert got["mean_shift"] == 0.33


def test_displacement_ignores_items_with_no_gold_span():
    from regops_evals.bench import displacement

    before = [_row(item_id="n", query_type="negative", gold=[], ranked=["x"], metrics={})]
    after = [_row(item_id="n", query_type="negative", gold=[], ranked=["y"], metrics={})]
    assert displacement(before, after)["n_both_retrieved"] == 0


def _answer(**kw) -> dict:
    base = dict(is_negative=False, abstained=False, error="", flagged=False, item_id="gs-0001")
    base.update(kw)
    return base


def test_abstention_is_two_rates_and_they_are_not_interchangeable():
    """A system that abstains on everything must not score well.

    Reporting one blended "abstention accuracy" is how that happens: refusing
    every question makes the negatives look perfect, and in a compliance tool
    the two failures are not the same failure.
    """
    from regops_evals.generation import abstention_split

    always_abstains = [_answer(is_negative=True, abstained=True) for _ in range(10)] + [
        _answer(abstained=True) for _ in range(10)
    ]
    got = abstention_split(always_abstains)
    assert got["false_answer_rate"] == 0.0  # flawless on the negatives
    assert got["false_abstention_rate"] == 1.0  # and useless on everything else


def test_a_generator_error_is_not_credited_as_an_abstention():
    """A crashed call is an error, not good judgement about the corpus."""
    from regops_evals.generation import abstention_split

    got = abstention_split(
        [_answer(is_negative=True, abstained=False, error="timeout") for _ in range(4)]
    )
    assert got["false_answer_rate"] == 0.0


def test_the_flagged_split_separates_the_instrument_from_the_system():
    from regops_evals.generation import abstention_split

    rows = [_answer(flagged=True, abstained=True) for _ in range(3)]
    rows += [_answer(flagged=True, abstained=False)]
    rows += [_answer(flagged=False, abstained=True)]
    rows += [_answer(flagged=False, abstained=False) for _ in range(9)]
    got = abstention_split(rows)
    assert got["false_abstention_flagged"] == 0.75
    assert got["false_abstention_unflagged"] == 0.1
    assert got["false_abstention_rate"] == 0.2857
    assert (got["flagged_n"], got["unflagged_n"]) == (4, 10)


def test_the_split_is_none_rather_than_zero_when_a_bucket_is_empty():
    """0.0 would read as 'never refused'; the honest answer is 'no items'."""
    from regops_evals.generation import abstention_split

    got = abstention_split([_answer(flagged=False, abstained=True)])
    assert got["false_abstention_flagged"] is None
    assert got["false_abstention_unflagged"] == 1.0


def test_useful_answer_rate_is_not_gamed_by_abstaining():
    """Groundedness rewards silence; this is the column that does not.

    A system that answers 10 of 100 items and grounds all 10 scores a perfect
    groundedness. It has still failed 90 questions the corpus could answer.
    """
    from regops_evals.report import _useful

    cautious = {"groundedness": 1.0, "grounded_n": 10, "grounded_items_n": 100}
    working = {"groundedness": 0.85, "grounded_n": 80, "grounded_items_n": 100}
    assert cautious["groundedness"] > working["groundedness"]
    assert _useful(cautious) == 0.1
    assert _useful(working) == 0.68
    assert _useful(working) > _useful(cautious)


def test_useful_answer_rate_survives_a_missing_denominator():
    from regops_evals.report import _useful

    assert _useful({"groundedness": 0.5, "grounded_n": 2, "grounded_items_n": 0}) == 1.0
