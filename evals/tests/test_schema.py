"""What the schema must refuse.

A golden set has no downstream consumer that can notice a malformed item, so
the file is validated on write and on read. These are the invariants that,
if broken, would make Day 5's per-query-type table quietly wrong rather than
visibly broken.
"""

from __future__ import annotations

import pytest
from conftest import PROV, make_item
from pydantic import ValidationError
from regops_evals.schema import STRATIFICATION, GoldenItem, read_jsonl, write_jsonl


def test_stratification_totals_150():
    assert sum(STRATIFICATION.values()) == 150


def test_negative_may_not_carry_a_gold_span():
    with pytest.raises(ValidationError, match="that is what makes it negative"):
        make_item(query_type="negative", absence_reason="other_jurisdiction")


def test_negative_must_say_why_it_is_unanswerable():
    with pytest.raises(ValidationError, match="must say why"):
        make_item(query_type="negative", gold_spans=[])


def test_grounded_item_needs_a_span():
    with pytest.raises(ValidationError, match="needs at least one gold span"):
        make_item(gold_spans=[])


def test_multi_hop_needs_two_spans():
    """One span is not a hop. This is the check that keeps `multi_hop` meaning
    something in the per-query-type table."""
    with pytest.raises(ValidationError, match="needs 2\\+ gold spans"):
        make_item(query_type="multi_hop")


def test_absence_reason_is_negatives_only():
    with pytest.raises(ValidationError, match="belongs to negatives only"):
        make_item(absence_reason="invented_specific")


def test_question_must_be_a_question():
    with pytest.raises(ValidationError, match="must end with"):
        make_item(question="Describe the beneficial ownership requirement.")


def test_unknown_field_is_rejected():
    """`extra: forbid` is deliberate: a typo'd field name would otherwise be
    silently dropped, and the item would look complete while missing a check."""
    with pytest.raises(ValidationError):
        make_item(verifcation={"status": "machine_verified"})


def test_roundtrip_preserves_every_field(tmp_path):
    items = [make_item(), make_item(id="gs-0002")]
    p = tmp_path / "g.jsonl"
    write_jsonl(p, items)
    back = read_jsonl(p)
    assert [i.model_dump() for i in back] == [i.model_dump() for i in items]


def test_duplicate_ids_are_rejected(tmp_path):
    p = tmp_path / "g.jsonl"
    write_jsonl(p, [make_item(), make_item()])
    with pytest.raises(ValueError, match="duplicate id"):
        read_jsonl(p)


def test_a_bad_line_names_itself(tmp_path):
    p = tmp_path / "g.jsonl"
    p.write_text('{"id": "gs-0001"}\n')
    with pytest.raises(ValueError, match=r"g\.jsonl:1"):
        read_jsonl(p)


def test_ids_are_zero_padded():
    with pytest.raises(ValidationError):
        GoldenItem.model_validate({**make_item().model_dump(), "id": "gs-1"})


def test_provenance_is_required():
    d = make_item().model_dump()
    del d["provenance"]
    with pytest.raises(ValidationError):
        GoldenItem.model_validate(d)
    assert PROV.generator  # the fixture provenance is what real items carry
