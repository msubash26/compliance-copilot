"""The tool-call recorder, including what it deliberately does not count.

The one interesting assertion in here is `documents_read`. Tool-call recall asks
*did the agent read the document that answers the question*, and a `doc_id` that
appeared in a search result was offered to the agent rather than used by it.
Counting search hits would make recall a measurement of BM25, which is Day 5's
question and already answered.
"""

from __future__ import annotations

import pytest
from regops_agents.record import Recorder


def test_a_call_is_recorded_with_its_size_and_time():
    rec = Recorder()
    with rec.call("search_notices", {"query": "x", "top_k": 8}) as box:
        box[0] = "a" * 120
    (call,) = rec.calls
    assert call["tool"] == "search_notices"
    assert call["args"] == {"query": "x", "top_k": 8}
    assert call["result_chars"] == 120
    assert call["error"] is False
    assert call["seconds"] >= 0.0


def test_a_tool_error_is_recorded_as_an_error_not_as_a_result():
    """The bridge hands a `ToolError` back as text (ADR-005 rule 3); it is still a failure."""
    rec = Recorder()
    with rec.call("get_document_section", {"doc_id": "a", "section_path": "9"}) as box:
        box[0] = "TOOL ERROR from get_document_section: no section '9'"
    assert rec.calls[0]["error"] is True


def test_a_raising_tool_still_records_the_attempt():
    """A call that blew up is exactly the call a trajectory metric needs to see."""
    rec = Recorder()
    with pytest.raises(RuntimeError), rec.call("search_notices", {"query": "x"}):
        raise RuntimeError("transport died")
    assert len(rec.calls) == 1
    assert rec.calls[0]["error"] is True


def test_reset_clears_the_calls_and_stamps_the_task():
    rec = Recorder()
    with rec.call("search_notices", {"query": "x"}) as box:
        box[0] = "ok"
    rec.reset("t-004")
    assert rec.calls == [] and rec.task_id == "t-004"
    with rec.call("search_notices", {"query": "y"}) as box:
        box[0] = "ok"
    assert rec.calls[0]["task_id"] == "t-004"


def test_documents_read_counts_reads_and_not_searches():
    rec = Recorder()
    with rec.call("search_notices", {"query": "pep", "top_k": 8}) as box:
        box[0] = '{"hits": [{"doc_id": "aaa"}, {"doc_id": "bbb"}]}'
    with rec.call("get_document_section", {"doc_id": "aaa", "section_path": "8.2"}) as box:
        box[0] = "the clause"
    assert rec.documents_read() == ["aaa"]


def test_documents_read_deduplicates_and_keeps_call_order():
    rec = Recorder()
    for doc in ("bbb", "aaa", "bbb"):
        with rec.call("get_document_section", {"doc_id": doc, "section_path": "1"}) as box:
            box[0] = "x"
    assert rec.documents_read() == ["bbb", "aaa"]


def test_a_failed_read_is_not_a_document_read():
    """Crediting recall for a read that errored would score the agent for asking."""
    rec = Recorder()
    with rec.call("get_document_section", {"doc_id": "aaa", "section_path": "9"}) as box:
        box[0] = "TOOL ERROR from get_document_section: no section '9'"
    assert rec.documents_read() == []


def test_list_obligations_counts_as_reading_the_document():
    """A coverage branch reads a document by listing its obligations, not its sections."""
    rec = Recorder()
    with rec.call("list_obligations", {"doc_id": "ccc"}) as box:
        box[0] = '{"obligations": []}'
    assert rec.documents_read() == ["ccc"]


def test_the_snapshot_does_not_alias_the_live_list():
    rec = Recorder()
    with rec.call("search_notices", {"query": "x"}) as box:
        box[0] = "ok"
    snap = rec.snapshot()
    rec.reset()
    assert len(snap) == 1 and rec.calls == []
