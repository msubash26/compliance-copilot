"""The metrics, on rows built by hand, including the ones that look right and are not.

`metrics.py` makes the argument this file inherits: a wrong retriever shows up as
a bad number, and a wrong *metric* shows up as a good number, in every cell,
consistently, with nothing downstream able to detect it. So every outcome here is
computed from a row whose expected value was worked out by hand, and the
degenerate cases -- zero tool calls, an agent that read nothing, a negative task,
a run that hit a ceiling -- are tested rather than assumed.

No model, no index, no server.
"""

from __future__ import annotations

from regops_evals.agenteval import GATED_ARM, REFUSAL, Row, looks_like_refusal, score


def row(**kw) -> Row:
    base = dict(
        arm="supervisor",
        task_id="t-001",
        golden_id="gs-0001",
        query_type="factual_lookup",
        question="q?",
        gold_answer="a",
        gold_doc_ids=["aaa"],
        gold_uids=["aaa:1.1"],
        must_cite=True,
        must_abstain=False,
        min_tool_calls=2,
    )
    return Row(**(base | kw))


# -- the four mechanical outcomes -------------------------------------------


class TestOutcomes:
    def test_a_clean_run_passes_all_four(self):
        r = row(docs_read=["aaa"], cited_uids=["aaa:1.1"], n_tool_calls=2, answer="It is 5%.")
        assert (r.retrieved_gold, r.cited_resolvable, r.abstained_correctly, r.within_budget) == (
            True,
            True,
            True,
            True,
        )
        assert r.success

    def test_reading_only_one_of_two_gold_documents_is_not_retrieved_gold(self):
        """A multi-hop answer built on half the hops is half an answer."""
        r = row(gold_doc_ids=["aaa", "bbb"], docs_read=["aaa"], min_tool_calls=3)
        assert not r.retrieved_gold
        assert r.tool_recall == 0.5

    def test_reading_the_gold_document_among_others_still_counts(self):
        r = row(docs_read=["zzz", "aaa", "yyy"])
        assert r.retrieved_gold
        assert r.tool_recall == 1.0
        assert r.tool_precision == round(1 / 3, 4)

    def test_a_grounded_task_that_cites_nothing_resolvable_fails_that_outcome(self):
        r = row(docs_read=["aaa"], cited_uids=[], unresolvable=2)
        assert not r.cited_resolvable and not r.success

    def test_a_negative_task_needs_no_citation_and_no_gold_document(self):
        r = row(
            query_type="negative",
            gold_doc_ids=[],
            gold_uids=[],
            must_cite=False,
            must_abstain=True,
            min_tool_calls=1,
            n_tool_calls=1,
            answer="The corpus does not address this.",
            abstained=True,
        )
        assert r.retrieved_gold and r.cited_resolvable and r.abstained_correctly and r.success
        assert r.tool_recall is None and r.tool_precision is None

    def test_answering_a_negative_is_a_failure_even_with_a_real_citation(self):
        """The dangerous direction. A confident answer to an unanswerable question."""
        r = row(
            query_type="negative",
            gold_doc_ids=[],
            must_cite=False,
            must_abstain=True,
            min_tool_calls=1,
            n_tool_calls=2,
            cited_uids=["aaa:1.1"],
            answer="Yes, clause 1.1 requires it.",
            abstained=False,
        )
        assert not r.abstained_correctly and not r.success

    def test_a_ceiling_fails_within_budget_however_good_the_answer_is(self):
        r = row(
            docs_read=["aaa"], cited_uids=["aaa:1.1"], n_tool_calls=9, stopped_by="step_ceiling"
        )
        assert not r.within_budget and not r.success


# -- trajectory --------------------------------------------------------------


class TestTrajectory:
    def test_the_floor_is_the_best_score_and_it_is_capped(self):
        assert row(min_tool_calls=2, n_tool_calls=2).efficiency == 1.0
        assert row(min_tool_calls=2, n_tool_calls=1).efficiency == 1.0  # capped, never > 1

    def test_twice_the_floor_is_a_half(self):
        assert row(min_tool_calls=2, n_tool_calls=4).efficiency == 0.5

    def test_no_tool_calls_is_zero_efficiency_not_infinite(self):
        """An agent that called nothing is maximally inefficient, not maximally efficient."""
        assert row(n_tool_calls=0).efficiency == 0.0

    def test_the_raw_pair_survives_alongside_the_ratio(self):
        """0.5 from 2-instead-of-1 and 0.5 from 12-instead-of-6 are different animals."""
        a, b = row(min_tool_calls=1, n_tool_calls=2), row(min_tool_calls=6, n_tool_calls=12)
        assert a.efficiency == b.efficiency
        assert (a.min_tool_calls, a.n_tool_calls) != (b.min_tool_calls, b.n_tool_calls)


# -- abstention --------------------------------------------------------------


class TestAbstention:
    def test_the_markers_fire_on_a_real_refusal(self):
        assert looks_like_refusal(
            "The provided material does not contain the specific values requested."
        )
        assert looks_like_refusal("I could not find a clause addressing this.")

    def test_they_do_not_fire_on_an_ordinary_grounded_answer(self):
        assert not looks_like_refusal(
            "A bank shall retain the records for a period of at least five years."
        )
        assert not looks_like_refusal("The notice does not apply to exempt persons under 2.1.")

    def test_every_marker_is_lower_case(self):
        """The match lower-cases the answer, so an upper-case marker never fires."""
        assert all(m == m.lower() for m in REFUSAL)


# -- aggregation -------------------------------------------------------------


def _mixed() -> list[Row]:
    return [
        row(
            task_id="t-001", docs_read=["aaa"], cited_uids=["aaa:1.1"], n_tool_calls=2, seconds=1.0
        ),
        row(
            task_id="t-002",
            docs_read=[],
            cited_uids=[],
            n_tool_calls=1,
            seconds=2.0,
            abstained=True,
        ),
        row(
            task_id="t-003",
            query_type="negative",
            gold_doc_ids=[],
            gold_uids=[],
            must_cite=False,
            must_abstain=True,
            min_tool_calls=1,
            n_tool_calls=1,
            seconds=3.0,
            abstained=True,
        ),
        row(
            task_id="t-004",
            query_type="negative",
            gold_doc_ids=[],
            gold_uids=[],
            must_cite=False,
            must_abstain=True,
            min_tool_calls=1,
            n_tool_calls=2,
            cited_uids=["aaa:1.1"],
            seconds=4.0,
        ),
    ]


class TestScore:
    def test_the_composite_requires_all_four_outcomes(self):
        s = score(_mixed())
        assert s["success"]["composite"] == {"passed": 2, "n": 4}
        assert s["success"]["retrieved_gold"]["passed"] == 3
        assert s["success"]["abstained_correctly"]["passed"] == 2

    def test_abstention_is_two_rates_and_never_one(self):
        """ADR-021: refusing what you could answer and answering what you cannot
        are different failures, and averaging them produces a number for neither."""
        a = score(_mixed())["abstention"]
        assert a["false_abstention"] == {"n": 2, "count": 1, "rate": 0.5}
        assert a["false_answer"] == {"n": 2, "count": 1, "rate": 0.5}

    def test_counts_are_reported_beside_every_rate(self):
        """Day 6 Phase 1's lesson: over thirty tasks a rate turns one item into 3.3 points."""
        s = score(_mixed())
        for block in (s["success"]["composite"], s["abstention"]["false_answer"]):
            assert "n" in block

    def test_latency_carries_its_n(self):
        lat = score(_mixed())["latency"]
        assert lat["n"] == 4 and lat["max_s"] == 4.0 and lat["p50_s"] == 3.0

    def test_an_empty_arm_does_not_divide_by_zero(self):
        s = score([])
        assert s["n"] == 0 and s["success"]["rate"] is None and s["latency"]["p50_s"] == 0.0

    def test_the_gated_arm_is_the_supervisor(self):
        """Decision 2: measure three, gate one."""
        assert GATED_ARM == "supervisor"

    def test_the_serialised_row_carries_the_derived_outcomes_and_drops_the_call_log(self):
        d = row(docs_read=["aaa"], cited_uids=["aaa:1.1"], n_tool_calls=2).to_json()
        assert d["success"] is True and d["efficiency"] == 1.0
        assert "tool_calls" not in d
