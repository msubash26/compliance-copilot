"""The checks that keep the set honest, tested on their failure modes.

Every one of these guards something that actually went wrong while building the
set, or something that would go wrong silently if it were not checked:

- span drift, because Day 3 moved this corpus from 8,055 clauses to 11,171;
- leakage, because a question that names its own clause makes BM25 unbeatable;
- entity naming, because MAS publishes near-identical notices per entity class
  and a question that omits the class has no single right answer;
- the closed-book self-report, because a model claiming to know something is
  not evidence that it does.
"""

from __future__ import annotations

from conftest import CLAUSES, make_item
from regops_evals.schema import span_hash
from regops_evals.verify import (
    check_answer_grounding,
    check_entity_named,
    check_leakage,
    check_spans,
)


def test_span_that_still_matches_resolves(index):
    assert check_spans(make_item(), index)[0] == "resolved"


def test_span_whose_text_changed_reports_moved(index):
    """The outcome that matters. A path that still exists but holds different
    text is a re-parse, and it is invisible to any check that only asks whether
    the path is there."""
    it = make_item()
    it.gold_spans[0].span_sha256 = span_hash("something the parser used to produce")
    assert check_spans(it, index)[0] == "moved"


def test_span_pointing_at_nothing_reports_missing(index):
    it = make_item()
    it.gold_spans[0].section_path = "99.99"
    assert check_spans(it, index)[0] == "missing"


def test_hash_ignores_whitespace_but_not_words():
    """Re-parsing changes line wrapping without changing the clause, so the hash
    is over normalised whitespace. It must still notice a different clause."""
    _, _, text = CLAUSES[0]
    assert span_hash(text) == span_hash("  ".join(text.split()))
    assert span_hash(text) != span_hash(text.replace("beneficial owner", "customer"))


def test_leakage_catches_a_named_notice():
    assert "notice_number" in check_leakage(
        make_item(question="What does MAS Notice 626 require of a bank?")
    )


def test_leakage_catches_a_clause_number():
    assert "paragraph_number" in check_leakage(
        make_item(question="What does paragraph 6.14 require of a bank?")
    )


def test_leakage_catches_an_instrument_code():
    assert "instrument_code" in check_leakage(
        make_item(question="What must a financial adviser do under FAA-N06 for new customers?")
    )


def test_the_bare_word_notice_is_not_a_leak():
    """The regex has to distinguish "the Notice" from "Notice 626". Without
    this, a third of legitimate questions would be flagged."""
    assert (
        check_leakage(make_item(question="What must a bank do where the Notice sets no threshold?"))
        == []
    )


def test_negatives_are_exempt_from_leakage():
    """Naming a real instrument is what makes an unanswerable question plausible
    -- a negative that avoided all instrument names would be obviously odd."""
    assert (
        check_leakage(
            make_item(
                query_type="negative",
                gold_spans=[],
                absence_reason="withdrawn_requirement",
                question="What does MAS Notice 626 require of a bank today?",
            )
        )
        == []
    )


def test_entity_check_accepts_the_singular():
    """MAS titles a class in the plural ("Banks"); a compliance officer asks in
    the singular ("a bank"). Treating that as a missing entity was a real false
    positive on the first verification pass."""
    assert check_entity_named(make_item(question="When must a bank identify a beneficial owner?"))


def test_entity_check_fires_when_the_class_is_absent():
    assert not check_entity_named(
        make_item(question="When must a firm identify a beneficial owner of a customer?")
    )


def test_uncontested_item_needs_no_entity():
    """The rule exists to make near-duplicate distractors defeatable. Where there
    are no near duplicates, requiring the entity word would be noise."""
    assert check_entity_named(
        make_item(
            question="When must a firm identify a beneficial owner of a customer?",
            difficulty={"near_duplicates_at_0_10": 0, "vocab_overlap": 0.2},
        )
    )


def test_answer_grounding_is_high_when_the_answer_is_in_the_span(index):
    it = make_item(answer="A bank shall identify the beneficial owner of every customer.")
    assert check_answer_grounding(it, index) > 0.8


def test_answer_grounding_is_low_for_an_invented_answer(index):
    it = make_item(answer="Quarterly liquidity coverage submissions require actuarial signoff.")
    assert check_answer_grounding(it, index) < 0.25
