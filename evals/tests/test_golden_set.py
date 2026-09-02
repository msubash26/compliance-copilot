"""Tests against the artifact that actually ships.

The suite above tests the machinery. This tests `golden/v1/golden.jsonl` itself,
because the machinery being correct is not the same claim as the file being
right -- the file is what Day 5 measures against, and it is the thing that rots.

Two of these need the real index and are skipped without it, so CI still runs
everything that does not. The stratification test is the important one: a set
whose per-query-type counts drift from the declared targets makes Day 5's table
a comparison between differently-sized cells while still looking fine.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from regops_evals.schema import STRATIFICATION, read_jsonl

GOLDEN = Path("golden/v1/golden.jsonl")
INDEX = Path("index/regdocs.duckdb")

pytestmark = pytest.mark.skipif(not GOLDEN.exists(), reason="golden set not built")


@pytest.fixture(scope="module")
def items():
    return read_jsonl(GOLDEN)


def test_every_line_validates(items):
    """`read_jsonl` raises on the first bad line, so reaching here is the test."""
    assert len(items) == sum(STRATIFICATION.values())


def test_ids_are_unique_and_contiguous(items):
    assert [i.id for i in items] == [f"gs-{n:04d}" for n in range(1, len(items) + 1)]


def test_stratification_matches_the_declared_targets(items):
    counts = {qt: sum(1 for i in items if i.query_type == qt) for qt in STRATIFICATION}
    assert counts == STRATIFICATION


def test_negatives_carry_a_reason_and_no_span(items):
    negs = [i for i in items if i.query_type == "negative"]
    assert negs and all(i.absence_reason and not i.gold_spans for i in negs)


def test_negatives_span_all_five_absence_reasons(items):
    """A negative set that is 35 variations of one trick measures one thing."""
    reasons = {i.absence_reason for i in items if i.query_type == "negative"}
    assert len(reasons) == 5


def test_every_grounded_item_has_a_span(items):
    assert all(i.gold_spans for i in items if i.query_type != "negative")


def test_multi_span_types_really_have_multiple_spans(items):
    multi = [i for i in items if i.query_type in ("multi_hop", "comparative")]
    assert multi and all(len(i.gold_spans) >= 2 for i in multi)


def test_no_item_claims_human_review_it_has_not_had(items):
    """The artifact's central honesty claim, as a test. If a human review pass
    happens, this test is what has to be updated deliberately."""
    assert not any(i.verification.human_reviewed for i in items)


def test_every_item_is_provenance_stamped(items):
    assert all(i.provenance.generator and i.provenance.parser for i in items)


def test_the_verifier_is_not_the_generator(items):
    """A model agreeing with itself is not evidence. This is the check that
    keeps "verified" meaning something."""
    verified = [i for i in items if i.verification.verifier]
    assert verified
    assert all(i.verification.verifier != i.provenance.generator for i in verified)


def test_factual_items_span_all_three_difficulty_bands(items):
    """A uniform sample of this corpus is mostly isolated clauses, which is how
    a golden set ends up saturated. The even split is the point."""
    nd = [
        i.difficulty.near_duplicates_at_0_10
        for i in items
        if i.query_type == "factual_lookup" and i.difficulty
    ]
    assert min(nd) == 0 and max(nd) >= 5
    assert sum(1 for n in nd if n >= 5) >= 10


@pytest.mark.skipif(not INDEX.exists(), reason="real index not present")
def test_every_gold_span_still_binds_to_the_index(items):
    """The anti-rot check. Day 3 moved this corpus from 8,055 clauses to 11,171;
    a set pinning `section_path` is pinned to a parser, and this is what turns
    that into a failing test rather than a slow decay in the numbers."""
    from regops_evals.corpus import Index
    from regops_evals.verify import check_spans

    ix = Index(INDEX)
    try:
        bad = [(i.id, check_spans(i, ix)[0]) for i in items]
        assert [b for b in bad if b[1] != "resolved"] == []
    finally:
        ix.close()


@pytest.mark.skipif(not INDEX.exists(), reason="real index not present")
def test_no_question_leaks_its_own_source(items):
    from regops_evals.verify import check_leakage

    leaks = {i.id: check_leakage(i) for i in items}
    assert {k: v for k, v in leaks.items() if v} == {}
