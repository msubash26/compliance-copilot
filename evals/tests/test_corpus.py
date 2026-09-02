"""Parsing what MAS titles say, and searching what the index holds.

The two extractors here decide which questions can exist at all: `notice_code`
resolves a cross-reference into a `multi_hop` pair, and `entity_class` supplies
the discriminator that makes a `comparative` question answerable. Both were
rewritten during the build after their first versions lost a third of the
AML/CFT family, so the cases below are the real titles that broke them.
"""

from __future__ import annotations

import pytest
from conftest import _v
from regops_evals.corpus import entity_class, notice_code
from regops_evals.generate import vocab_overlap


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Notice 626 Prevention of Money Laundering - Banks", "626"),
        ("Notice 626A Prevention of Money Laundering - Credit Card Licensees", "626A"),
        ("Guidelines to MAS Notice 1014 on Prevention of Money Laundering", "1014"),
        ("Notice FAA-N06 on Prevention of Money Laundering", "FAA-N06"),
        ("Notice SFA 03AA-N01 to the Depository on Prevention", "SFA 03AA-N01"),
        ("PSN01AA Prevention of Money Laundering", "PSN01AA"),
    ],
)
def test_notice_code(title, expected):
    assert notice_code(title) == expected


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Notice 626 Prevention of Money Laundering – Banks", "Banks"),
        # A spaced hyphen separates; a bare one does not -- "Trustee-Managers".
        (
            "Notice PSN10 Prevention of ML - Exempt Payment Service Providers",
            "Exempt Payment Service Providers",
        ),
        (
            "Notice BTA1-N01 to Trustee-Managers on Prevention of Money Laundering",
            "Trustee-Managers",
        ),
        (
            "Notice SFA 13-N01 to Approved Trustees on Prevention of Money Laundering",
            "Approved Trustees",
        ),
        # A trailing parenthetical is part of the name, not a reason to give up.
        (
            "Notice VCC-N01 Prevention of ML – Variable Capital Companies (VCCs)",
            "Variable Capital Companies (VCCs)",
        ),
        # A curly apostrophe is still a letter.
        (
            "Notice FSM-N02 Prevention of ML – Financial Institutions’ Sharing Platform",
            "Financial Institutions’ Sharing Platform",
        ),
    ],
)
def test_entity_class(title, expected):
    assert entity_class(title) == expected


def test_entity_class_is_none_when_the_title_names_no_class():
    """Honest None rather than a forced guess: the cross-border notices bind a
    described set of persons, not a named class."""
    assert entity_class("MAS Notice FSM-N27 Prevention of Money Laundering") is None
    assert (
        entity_class(
            "Notice FAA-N24 to Specified Financial Advisers in relation to "
            "Cross-Border Arrangements under the Regulations 2021"
        )
        is None
    )


def test_eligible_clauses_excludes_front_matter_and_opaque_paths(index):
    paths = {c.section_path for c in index.eligible_clauses(min_chars=10)}
    assert "0" not in paths
    assert not any("#" in p for p in paths)


def test_obligation_filter_keeps_duties_and_drops_definitions(index):
    """The filter that stopped `comparative` items being generated from
    exemption schedules -- long, near-identical across notices, and binding
    nobody."""
    everything = index.eligible_clauses(min_chars=10)
    with_obl = index.eligible_clauses(min_chars=10, obligations_only=True)
    assert {c.section_path for c in everything} - {c.section_path for c in with_obl} == {"2.1"}
    assert all("shall" in c.text for c in with_obl)


def test_bm25_finds_the_clause_it_was_asked_for(index):
    got = [u for u, _ in index.search_bm25("anonymous account fictitious name", 3)]
    assert "d0000001:6.15" in got


def test_near_duplicates_finds_the_sibling_notice(index):
    """The measure the whole difficulty stratum rests on: clause 6.14 of the
    banks notice must find clause 6.14 of the merchant banks notice."""
    got = index.near_duplicates("d0000001", "6.14", threshold=0.10)
    assert [uid for _, uid, _ in got] == ["d0000002:6.14"]


def test_near_duplicates_exclude_the_clause_s_own_document(index):
    """A clause resembling its own neighbour is not a retrieval hazard. A clause
    resembling the same clause in eleven sibling notices is. Without the
    exclusion, 6.15 and 2.1 of the same notice would be counted as crowding."""
    got = index.near_duplicates("d0000001", "6.14", threshold=2.0)
    assert got and all(doc != "d0000001" for doc, _, _ in got)


def test_dense_search_ranks_the_nearest_clause_first(index):
    got = index.search_dense("who owns the customer", 2, vec=_v(1.0))
    assert got[0][0] == "d0000001:6.14"


def test_vocab_overlap_measures_shared_content_words():
    span = "A bank shall identify the beneficial owner of every customer."
    assert vocab_overlap("Who is the beneficial owner identified by a bank?", span) > 0.3
    assert vocab_overlap("What are the capital adequacy ratios for insurers?", span) < 0.1
