"""Writing the index: the Day 1 contract tables, plus additive ones beside them.

`documents`, `sections` and `document_versions` are `regdocs_mcp.index`'s to
define -- this module imports `SCHEMA_SQL` rather than restating it, so the two
repos cannot drift (ADR-003). `chunks`, `tables` and `embeddings` are new and
purely additive: the four MCP tools do not read them, which is what lets the
retrieval pipeline grow without the tool surface moving.

Re-ingestion is idempotent by key. That is not a tidiness point -- ADR-004 ships
`diff_versions` with an honest empty state precisely because version history is
*created* by a re-fetch that finds changed bytes under an unchanged URL, and
this is the code that has to notice.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
from regdocs_mcp.index import SCHEMA_SQL, connect

from regops_ingest.parse import ParsedDoc

EXTRA_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id     VARCHAR PRIMARY KEY,   -- section_uid || '#' || ordinal
    doc_id       VARCHAR NOT NULL,
    section_uid  VARCHAR NOT NULL,      -- the parent clause (ADR-014)
    ordinal      INTEGER NOT NULL,
    text         VARCHAR NOT NULL,
    context_text VARCHAR,               -- LLM-written locator; NULL until contextualised
    char_len     INTEGER NOT NULL,
    token_len    INTEGER
);

CREATE TABLE IF NOT EXISTS tables (
    table_id    VARCHAR PRIMARY KEY,    -- doc_id || ':t' || ordinal
    doc_id      VARCHAR NOT NULL,
    section_uid VARCHAR,
    page        INTEGER,
    caption     VARCHAR,
    n_rows      INTEGER,
    n_cols      INTEGER,
    rows_json   VARCHAR NOT NULL        -- structured rows, not flattened text
);

CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id VARCHAR NOT NULL,
    model    VARCHAR NOT NULL,          -- 'nomic-embed-text' / 'nomic-embed-text+ctx'
    dim      INTEGER NOT NULL,
    vec      FLOAT[768] NOT NULL,
    PRIMARY KEY (chunk_id, model)
);

CREATE INDEX IF NOT EXISTS chunks_section ON chunks (section_uid);
CREATE INDEX IF NOT EXISTS tables_doc ON tables (doc_id);
"""


def open_index(path: Path) -> duckdb.DuckDBPyConnection:
    """Open (creating if needed) an index carrying both halves of the schema."""
    conn = connect(path, read_only=False)
    conn.execute(SCHEMA_SQL)
    conn.execute(EXTRA_SCHEMA_SQL)
    return conn


def _next_version_label(
    conn: duckdb.DuckDBPyConnection, doc_id: str, base: str, sha: str | None
) -> str | None:
    """The label for this document's current bytes, or None if already recorded.

    Returns None when the exact sha256 is already on record -- re-ingesting an
    unchanged corpus must not mint a version. A changed sha256 under a known
    doc_id is what ADR-004 calls the birth of history.
    """
    rows = conn.execute(
        "SELECT version_label, sha256 FROM document_versions WHERE doc_id = ?", [doc_id]
    ).fetchall()
    if any(r[1] == sha for r in rows):
        return None
    labels = {r[0] for r in rows}
    if base not in labels:
        return base
    n = 2
    while f"{base}-{n}" in labels:
        n += 1
    return f"{base}-{n}"


def write_doc(conn: duckdb.DuckDBPyConnection, meta: dict, parsed: ParsedDoc) -> tuple[int, bool]:
    """Upsert one parsed document. Returns (n_sections, minted_a_new_version)."""
    doc_id = meta["doc_id"]
    conn.execute(
        "INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            doc_id,
            meta["issuer"],
            meta["doc_type"],
            meta["title"],
            meta.get("url"),
            meta.get("source_page"),
            meta.get("sha256"),
            meta.get("fetched_at"),
            parsed.effective_date,
            len(parsed.sections),
        ],
    )

    # Sections are replaced wholesale: a better parser may find *fewer* clauses,
    # and leaving the old ones behind would serve text the index no longer stands
    # behind. The tables below hang off section_uid, so they go the same way.
    conn.execute("DELETE FROM sections WHERE doc_id = ?", [doc_id])
    conn.execute("DELETE FROM tables WHERE doc_id = ?", [doc_id])
    for ordinal, s in enumerate(parsed.sections):
        conn.execute(
            "INSERT OR REPLACE INTO sections VALUES (?,?,?,?,?,?,?,?,?)",
            [
                f"{doc_id}:{s.section_path}",
                doc_id,
                s.section_path,
                s.heading,
                ordinal,
                s.text,
                len(s.text),
                s.page_from,
                s.page_to,
            ],
        )
    for i, t in enumerate(parsed.tables):
        conn.execute(
            "INSERT OR REPLACE INTO tables VALUES (?,?,?,?,?,?,?,?)",
            [
                f"{doc_id}:t{i}",
                doc_id,
                f"{doc_id}:{t.section_path}",
                t.page,
                t.caption,
                len(t.rows),
                max((len(r) for r in t.rows), default=0),
                json.dumps(t.rows, ensure_ascii=False),
            ],
        )

    base = parsed.effective_date or (meta.get("fetched_at") or "")[:10] or "current"
    label = _next_version_label(conn, doc_id, base, meta.get("sha256"))
    if label is not None:
        conn.execute(
            "INSERT OR REPLACE INTO document_versions VALUES (?,?,?,?,?)",
            [doc_id, label, meta.get("sha256"), meta.get("fetched_at"), meta["filename"]],
        )
    return len(parsed.sections), label is not None


def build_fts(conn: duckdb.DuckDBPyConnection) -> None:
    """(Re)build the BM25 index the `search_notices` tool reads."""
    conn.execute("PRAGMA drop_fts_index('sections')" if _has_fts(conn) else "SELECT 1")
    conn.execute("PRAGMA create_fts_index('sections', 'section_uid', 'text', 'heading')")


def _has_fts(conn: duckdb.DuckDBPyConnection) -> bool:
    rows = conn.execute(
        "SELECT 1 FROM duckdb_schemas() WHERE schema_name = 'fts_main_sections'"
    ).fetchall()
    return bool(rows)
