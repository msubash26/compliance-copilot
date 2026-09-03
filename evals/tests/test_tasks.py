"""The task set's contract: derived from the golden set, and still derived.

Every assertion here is really the same one -- *`golden/tasks/v1/tasks.jsonl` is a
function of `golden/v1/golden.jsonl`, and if the input moved the output is stale*.
That is the whole reason the tasks carry a `golden_id` instead of a copy of the
question, and these tests are what turn the reason into a mechanism.

No model, no index-free assumptions beyond the committed files.
"""

from __future__ import annotations

import collections
from pathlib import Path

import pytest
from regops_evals.schema import read_jsonl
from regops_evals.tasks import (
    ABSENCE_ORDER,
    COVERAGE_TASKS,
    TASK_STRATIFICATION,
    build,
    min_tool_calls,
    read_tasks,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "golden/v1/golden.jsonl"
TASKS = ROOT / "golden/tasks/v1/tasks.jsonl"


@pytest.fixture(scope="module")
def tasks():
    return read_tasks(TASKS)


@pytest.fixture(scope="module")
def golden():
    return {i.id: i for i in read_jsonl(GOLDEN)}


def test_the_strata_sum_to_thirty(tasks):
    counts = collections.Counter(t.query_type for t in tasks)
    assert counts == TASK_STRATIFICATION
    assert len(tasks) == 30


def test_ids_are_unique_and_dense(tasks):
    assert [t.task_id for t in tasks] == [f"t-{n:03d}" for n in range(1, len(tasks) + 1)]


def test_every_task_still_resolves_against_the_golden_set(tasks, golden):
    """The derivation, checked in reverse. This is the staleness detector."""
    for t in tasks:
        it = golden.get(t.golden_id)
        assert it is not None, f"{t.task_id} cites {t.golden_id}, which is gone"
        assert t.question == it.question, f"{t.task_id}: the golden question changed"
        assert t.query_type == it.query_type
        assert t.gold_doc_ids == sorted({sp.doc_id for sp in it.gold_spans})
        assert t.gold_uids == sorted(sp.section_uid for sp in it.gold_spans)


def test_the_committed_file_is_what_the_builder_produces():
    """Regenerating must be a no-op. A hand-edit to the artifact fails here."""
    assert [t.model_dump() for t in build(GOLDEN)] == [t.model_dump() for t in read_tasks(TASKS)]


def test_min_tool_calls_is_one_search_plus_one_read_per_gold_document(tasks, golden):
    for t in tasks:
        assert t.min_tool_calls == 1 + len(t.gold_doc_ids)
        assert t.min_tool_calls == min_tool_calls(golden[t.golden_id])


def test_the_expectations_are_consistent_with_the_query_type(tasks):
    for t in tasks:
        if t.query_type == "negative":
            assert t.must_abstain and not t.must_cite
            assert t.gold_doc_ids == [] and t.min_tool_calls == 1
            assert t.absence_reason in ABSENCE_ORDER
        else:
            assert t.must_cite and not t.must_abstain
            assert t.gold_doc_ids, f"{t.task_id} is grounded and cites no document"
            assert t.absence_reason is None


def test_the_negatives_cover_all_five_absence_reasons(tasks):
    """Five negatives, five reasons. A stratum of one trick measures one trick."""
    reasons = {t.absence_reason for t in tasks if t.query_type == "negative"}
    assert reasons == set(ABSENCE_ORDER)


def test_no_flagged_golden_item_is_used(tasks, golden):
    for t in tasks:
        assert golden[t.golden_id].verification.status == "machine_verified"


def test_multi_document_types_actually_span_documents(tasks):
    """ADR-018's claim about the taxonomy, asserted rather than assumed."""
    for t in tasks:
        if t.query_type in ("multi_hop", "comparative"):
            assert len(t.gold_doc_ids) >= 2, f"{t.task_id} is {t.query_type} over one document"
        elif t.query_type in ("factual_lookup", "temporal"):
            assert len(t.gold_doc_ids) == 1


def test_no_task_asks_a_version_question():
    """ADR-028 makes `diff_versions` unreachable; a task nothing can pass measures nothing."""
    banned = ("diff_versions", "what changed between", "version 1 and version 2")
    for t in read_tasks(TASKS):
        low = t.question.lower()
        assert not any(b in low for b in banned), t.task_id


def test_the_coverage_tasks_are_held_separately(tasks):
    """Hand-written expectations do not belong in a derived file."""
    ids = {t.task_id for t in tasks}
    assert not ids & {c["task_id"] for c in COVERAGE_TASKS}
    assert len(COVERAGE_TASKS) == 3


@pytest.mark.slow
def test_every_gold_document_is_still_in_the_index(tasks):
    """Needs the built index, which CI does not have. Local, and it is the real check."""
    from regops_retrieval.index import Index

    ix = Index(ROOT / "index/regdocs.duckdb")
    try:
        for t in tasks:
            for uid in t.gold_uids:
                assert ix.clause_by_uid(uid) is not None, f"{t.task_id}: {uid} is not in the index"
    finally:
        ix.close()
