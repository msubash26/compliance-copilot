"""Validation, layer by layer — and the failure that motivated layer 2.

Research 2 measured 18 of 20 answers schema-valid and 12 of 20 with citations
that resolve. The gap is the whole point of this module, so the actual bad
output from that run is the fixture below rather than something invented for the
test.
"""

from __future__ import annotations

import pytest
from regops_agents.structured import Answer, Citation, check_references, check_shape

pytest_plugins = ["fixtures_agents"]


class StubIndex:
    """Only `clause_by_uid` is exercised, so only it is stubbed."""

    def __init__(self, uids: set[str]) -> None:
        self.uids = uids
        self.lookups: list[str] = []

    def clause_by_uid(self, uid: str):
        self.lookups.append(uid)
        return object() if uid in self.uids else None


@pytest.fixture
def ix():
    return StubIndex({"d0000001:6.14", "d0000001:6.15"})


# -- layer 1: shape --------------------------------------------------------


def test_well_formed_json_validates():
    ans, problems = check_shape(
        '{"answer": "A bank shall identify the beneficial owner.",'
        ' "citations": [{"doc_id": "d0000001", "section_path": "6.14"}],'
        ' "sufficient": true}'
    )
    assert problems == []
    assert ans is not None
    assert ans.citations[0].doc_id == "d0000001"


def test_malformed_json_is_a_violation_not_an_exception():
    ans, problems = check_shape("this is not json at all")
    assert ans is None
    assert problems and problems[0].startswith("schema:")


def test_a_missing_required_field_is_reported_with_its_location():
    ans, problems = check_shape('{"answer": "x", "citations": []}')
    assert ans is None
    assert any("sufficient" in p for p in problems)


# -- layer 2: reference ----------------------------------------------------


def test_the_research_2_failure_is_caught(ix):
    """The exact output that passed Pydantic and cited nothing real.

    The model filled both fields with the excerpt's *label* — `[1]` for the
    document and the whole header line for the clause — instead of the
    identifiers inside it. Every field is a present, non-empty string, so shape
    validation has no complaint. Only a lookup finds it.
    """
    ans = Answer(
        answer="Clause 6.14 requires identification of the beneficial owner.",
        citations=[Citation(doc_id="[1]", section_path="clause 6.14 (d0000001:6.14)")],
        sufficient=True,
    )
    problems = check_references(ix, ans)
    assert len(problems) == 1
    assert "not in the index" in problems[0]
    assert "[1]" in problems[0], "the violation names the bad value, so a repair can act on it"


def test_a_resolvable_citation_passes(ix):
    ans = Answer(
        answer="x",
        citations=[Citation(doc_id="d0000001", section_path="6.14")],
        sufficient=True,
    )
    assert check_references(ix, ans) == []


def test_every_citation_is_checked_not_just_the_first(ix):
    ans = Answer(
        answer="x",
        citations=[
            Citation(doc_id="d0000001", section_path="6.14"),
            Citation(doc_id="d0000001", section_path="99.99"),
        ],
        sufficient=True,
    )
    problems = check_references(ix, ans)
    assert len(problems) == 1
    assert "99.99" in problems[0]
    assert len(ix.lookups) == 2


def test_claiming_sufficiency_with_no_citation_at_all_fails(ix):
    """An unfalsifiable claim is the failure this whole pipeline exists to avoid."""
    ans = Answer(answer="Banks must do it.", citations=[], sufficient=True)
    problems = check_references(ix, ans)
    assert len(problems) == 1
    assert "cites nothing" in problems[0]


def test_an_abstention_is_not_required_to_cite(ix):
    """35 of the 150 golden items have no answer in the corpus. Refusing is correct."""
    ans = Answer(answer="The corpus does not address this.", citations=[], sufficient=False)
    assert check_references(ix, ans) == []
    assert ix.lookups == [], "an abstention costs no lookups"


def test_the_uid_is_built_the_way_the_index_addresses_a_clause(ix):
    ans = Answer(
        answer="x", citations=[Citation(doc_id="abc", section_path="6.14")], sufficient=True
    )
    check_references(ix, ans)
    assert ix.lookups == ["abc:6.14"]
