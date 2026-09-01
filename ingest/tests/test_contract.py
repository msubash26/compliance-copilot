"""ADR-003's claim, as a test.

Day 1 asserted that the index schema is the contract and the parser is
replaceable: `regops-ingest` would swap Docling in behind the same three tables
and the four MCP tools would not move. That is a sentence in a decision record
until something runs the tools against an index this pipeline built.

So: build an index with `regops_ingest.load`, point `REGDOCS_INDEX` at it, and
drive the real MCP server over the real JSON-RPC surface. If a tool needs one
edit to serve this, ADR-003 was wrong -- and that is the finding worth having.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

import pytest
from mcp import ClientSession
from mcp.client._memory import InMemoryTransport
from regops_ingest import load

# The copilot workspace runs pytest-asyncio in auto mode (see pyproject), so async
# tests need no marker here. regdocs-mcp's own suite uses anyio; mixing the two
# drivers in one process hangs rather than fails, which is worth knowing once.
EXPECTED_TOOLS = ["search_notices", "get_document_section", "list_obligations", "diff_versions"]


@pytest.fixture
def built_index(index_path, meta, parsed_with_table):
    conn = load.open_index(index_path)
    load.write_doc(conn, meta, parsed_with_table)
    load.build_fts(conn)
    conn.close()
    return index_path


@asynccontextmanager
async def _session():
    """The real regdocs-mcp server, over the real JSON-RPC surface.

    Deliberately a context manager entered inside each test rather than an async
    generator fixture: the SDK's transport is built on anyio task groups, and
    pytest-asyncio tears a fixture down in a different task than it set it up in,
    which surfaces as "attempted to exit cancel scope in a different task".
    """
    import regdocs_mcp.server as srv

    srv._conn = None  # drop any connection cached against another index
    async with (
        InMemoryTransport(srv.mcp, raise_exceptions=False) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        yield session


@pytest.fixture
def client(built_index, monkeypatch):
    """Points the server at the index this pipeline just wrote."""
    monkeypatch.setenv("REGDOCS_INDEX", str(built_index))
    return _session


class TestTheToolSurfaceDidNotMove:
    async def test_the_same_four_tools_are_exposed(self, client):
        async with client() as session:
            names = [t.name for t in (await session.list_tools()).tools]
        assert sorted(names) == sorted(EXPECTED_TOOLS)

    async def test_search_finds_a_clause_written_by_this_pipeline(self, client):
        async with client() as session:
            res = await session.call_tool("search_notices", {"query": "customer due diligence"})
        out = res.structured_content
        assert out["total"] > 0
        assert any(h["section_path"] == "6.1" for h in out["hits"])

    async def test_a_clause_is_retrievable_by_its_own_number(self, client):
        async with client() as session:
            res = await session.call_tool(
                "get_document_section", {"doc_id": "aaa11111", "section_path": "6.1"}
            )
        assert "customer due diligence" in res.structured_content["text"].lower()

    async def test_obligations_are_extracted_from_this_index(self, client):
        async with client() as session:
            res = await session.call_tool("list_obligations", {"doc_id": "aaa11111"})
        kinds = {o["modality"] for o in res.structured_content["obligations"]}
        # "shall perform" is a requirement; "shall not open" is a prohibition.
        assert {"requirement", "prohibition"} <= kinds

    async def test_diff_versions_still_reports_its_honest_empty_state(self, client):
        """ADR-004: one version per document until a re-fetch changes the bytes."""
        async with client() as session:
            res = await session.call_tool(
                "diff_versions", {"doc_id": "aaa11111", "v1": "a", "v2": "b"}
            )
        assert res.is_error


class TestTheAdditiveTablesAreInvisibleToTheTools:
    def test_tables_are_stored_as_rows_not_flattened_text(self, built_index, table_rows):
        conn = load.open_index(built_index)
        row = conn.execute(
            "SELECT n_rows, n_cols, rows_json FROM tables WHERE doc_id = 'aaa11111'"
        ).fetchone()
        conn.close()
        assert (row[0], row[1]) == (3, 2)
        assert json.loads(row[2]) == table_rows

    def test_the_contract_tables_carry_no_new_columns(self, built_index):
        """A new column would be a schema change the server did not agree to."""
        conn = load.open_index(built_index)
        cols = {
            t: [r[0] for r in conn.execute(f"DESCRIBE {t}").fetchall()]
            for t in ("documents", "sections", "document_versions")
        }
        conn.close()
        assert cols["sections"] == [
            "section_uid",
            "doc_id",
            "section_path",
            "heading",
            "ordinal",
            "text",
            "char_len",
            "page_from",
            "page_to",
        ]
        assert "effective_date" in cols["documents"]
