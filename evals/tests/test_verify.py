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


def test_no_judge_preserves_a_judged_run_and_does_not_reset_flags(index_path, tmp_path):
    """`--no-judge` re-runs the mechanical checks. It must not erase the rest.

    This is a regression, and it was found by running Day 5's own Phase 0
    pre-flight: `verify --index ... --no-judge` rebuilt the whole `verification`
    block from scratch, so a check intended to confirm that 150 gold spans still
    resolve silently reset 28 flagged items to `unverified` and wrote the file
    back. Nothing downstream could have detected that — the benchmark would
    simply have reported a cleaner instrument than it has.
    """
    from regops_evals.schema import read_jsonl, write_jsonl
    from regops_evals.verify import run_verify

    golden = tmp_path / "golden.jsonl"
    item = make_item(
        verification={
            "span_exists": True,
            "answerable_from_span": False,
            "no_leakage": True,
            "verifier": "qwen3.8:latest",
            "status": "flagged",
            "human_reviewed": False,
            "confidence": 0.35,
            "failures": ["judge_says_not_answerable_from_span"],
        }
    )
    write_jsonl(golden, [item])

    assert run_verify(golden, index_path, judge=False) == 0

    after = read_jsonl(golden)[0].verification
    assert after.status == "flagged"
    assert "judge_says_not_answerable_from_span" in after.failures
    assert after.verifier == "qwen3.8:latest"
    assert after.answerable_from_span is False
    # The mechanical fields are still refreshed -- that is what the run is for.
    assert after.span_exists is True
    assert after.no_leakage is True


def test_no_judge_can_still_raise_a_new_mechanical_flag(index_path, tmp_path):
    """Preserving prior findings must not mean ignoring new ones."""
    from regops_evals.schema import read_jsonl, write_jsonl
    from regops_evals.verify import run_verify

    golden = tmp_path / "golden.jsonl"
    write_jsonl(
        golden,
        [
            make_item(
                question="What does MAS Notice 626 require of a bank on beneficial ownership?",
                verification={"status": "machine_verified", "confidence": 0.9},
            )
        ],
    )
    assert run_verify(golden, index_path, judge=False) == 0
    after = read_jsonl(golden)[0].verification
    assert after.status == "flagged"
    assert any("leak" in f for f in after.failures)


def test_a_truncated_negative_excerpt_says_that_it_is_truncated(index, monkeypatch):
    """The negative set's one known defect, as a test.

    `gs-0118` asks whether MAS prescribes disclosure templates. The right clause
    was retrieved at rank 3 — and cut to 700 characters, while the answer begins
    at character 3,697. The judge was asked "does the corpus answer this?", shown
    a window that stopped short of the answer, and said no with confidence 1.0.
    A silent truncation is a judge being lied to about its evidence, so what is
    cut now says so. See ADR-024.
    """
    from regops_evals import verify as V
    from regops_evals.verify import NEGATIVE_EXCERPT_CHARS, negative_excerpts

    # No test in this suite calls a model, and CI has no GPU. `negative_excerpts`
    # embeds the question before searching, so the embedder is stubbed rather
    # than reached for -- what is under test is the excerpt window, not Ollama.
    monkeypatch.setattr(V, "embed_one", lambda text, **kw: [0.0] * 768)

    long_clause = "d0000001:6.14"
    doc_id, _, path = long_clause.partition(":")
    ix = index
    original = ix.clause(doc_id, path).text
    assert len(original) < NEGATIVE_EXCERPT_CHARS  # the fixture clause is short

    class Stub:
        """An index whose one clause is longer than the excerpt window."""

        def __init__(self, inner):
            self.inner = inner

        def clause(self, d, p):
            cl = self.inner.clause(d, p)
            if cl is None:
                return None
            return type(cl)(
                cl.doc_id,
                cl.section_path,
                cl.heading,
                "filler " * 3000 + "THE ANSWER IS HERE",
                cl.title,
                cl.doc_type,
                cl.effective_date,
            )

        def search_bm25(self, q, k):
            return [(long_clause, 1.0)]

        def search_dense(self, q, k, vec=None):
            return []

    item = make_item(query_type="negative", gold_spans=[], absence_reason="unregulated_topic")
    ex = negative_excerpts([item], Stub(ix))[item.id]
    assert "…truncated from" in ex
    assert "THE ANSWER IS HERE" not in ex  # still cut — but no longer silently
    assert len(ex) < 3000 * len("filler ")
