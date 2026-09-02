"""The context budget, and why truncation has to be a measurement.

A MAS clause can run to 127,564 characters -- one clause is longer than most
context windows. Without a cap, the parent-mode configurations would overflow
the generator on the tail of the distribution and score zero for groundedness,
and the write-up would read that as a retrieval result. So the cap is enforced,
and what it cost is *recorded per query* rather than swallowed.
"""

from __future__ import annotations

from regops_retrieval.context import PER_EXCERPT_SHARE, assemble_context
from regops_retrieval.retrievers import Scored

# Fixtures live in a uniquely named module rather than a third `conftest.py`;
# see fixtures_retrieval for why.
pytest_plugins = ["fixtures_retrieval"]


def _hits(*uids: str) -> list[Scored]:
    return [Scored(u, u.split("#")[0], 1.0, i + 1) for i, u in enumerate(uids)]


def test_a_long_clause_is_truncated_and_the_truncation_is_recorded(index):
    """`d0000002:12.1` is 220,000 characters in the fixture."""
    asm = assemble_context(index, _hits("d0000002:12.1"), mode="parent", budget=5_000)
    assert asm.chars <= 5_000
    assert asm.truncated_excerpts == 1
    assert asm.truncated is True
    assert "[…truncated]" in asm.text


def test_no_single_excerpt_may_eat_the_whole_budget(index):
    """Otherwise one 127K clause at rank 1 starves the other four retrieved."""
    asm = assemble_context(
        index,
        _hits("d0000002:12.1", "d0000001:6.14", "d0000001:6.15"),
        mode="parent",
        budget=10_000,
    )
    assert len(asm.cited) == 3
    first = asm.text.split("\n\n")[0]
    assert len(first) <= 10_000 * PER_EXCERPT_SHARE + 200


def test_a_short_context_is_not_truncated_and_says_so(index):
    asm = assemble_context(index, _hits("d0000001:6.14", "d0000001:6.15"), mode="parent")
    assert asm.truncated_excerpts == 0
    assert asm.dropped_excerpts == 0
    assert asm.truncated is False
    assert asm.cited == ["d0000001:6.14", "d0000001:6.15"]


def test_excerpts_are_numbered_so_a_citation_can_be_checked(index):
    asm = assemble_context(index, _hits("d0000001:6.14", "d0000001:6.15"), mode="parent")
    assert asm.text.startswith("[1] ")
    assert "\n\n[2] " in asm.text
    # The uid is in the header, so a judge can bind a citation to a clause.
    assert "(d0000001:6.14)" in asm.text


def test_dropped_excerpts_are_counted_not_silently_lost(index):
    """A retrieved clause the generator never saw is a confound, not a detail."""
    asm = assemble_context(
        index,
        _hits("d0000002:12.1", "d0000001:6.14", "d0000001:6.15"),
        mode="parent",
        budget=800,
    )
    assert asm.dropped_excerpts >= 1
    assert len(asm.cited) < 3


def test_child_mode_assembles_chunks_and_is_far_smaller(index):
    parent = assemble_context(index, _hits("d0000002:12.1"), mode="parent", budget=10**7)
    child = assemble_context(index, _hits("d0000002:12.1#0"), mode="child", budget=10**7)
    assert child.chars < parent.chars
    assert child.cited == ["d0000002:12.1"]  # scored as its parent clause


def test_top_k_is_respected(index):
    asm = assemble_context(
        index, _hits("d0000001:6.14", "d0000001:6.15", "d0000002:9.1"), mode="parent", top_k=2
    )
    assert len(asm.cited) == 2
