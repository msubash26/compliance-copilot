"""Embeddings, and the HNSW index that searches them -- both inside DuckDB.

Vectors live in the same file as the clauses (ADR-016). DuckDB 1.5.5 loads the
`vss` extension and builds HNSW indexes, so this adds no eighth container to a
stack that already runs seven, and an index stays one copyable artifact.

Every chunk is embedded twice, under two model labels: once on its own text and
once with its context sentence prepended. Day 5 sweeps contextual retrieval on
against off, and that comparison is only clean if both vectors exist over the
*same* chunks -- otherwise the arms differ in what was chunked as well as in
what was embedded.
"""

from __future__ import annotations

import os

import duckdb
import httpx

DEFAULT_MODEL = "nomic-embed-text:latest"
# The label written to `embeddings.model` for the context-prepended arm.
CTX_SUFFIX = "+ctx"
DIM = 768
BATCH = 64
TIMEOUT_S = 300.0


def base_url() -> str:
    raw = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    return raw.rstrip("/").removesuffix("/v1")


def embed_batch(texts: list[str], *, model: str = DEFAULT_MODEL) -> tuple[list[list[float]], int]:
    """Embed a batch. Returns (vectors, prompt tokens) -- the token count is real,
    taken from Ollama, and is what fills `chunks.token_len`."""
    r = httpx.post(
        f"{base_url()}/api/embed",
        json={"model": model, "input": texts},
        timeout=TIMEOUT_S,
    )
    r.raise_for_status()
    data = r.json()
    return data["embeddings"], int(data.get("prompt_eval_count") or 0)


def ensure_vss(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("INSTALL vss; LOAD vss;")
    # HNSW over a file-backed database is still flagged experimental upstream.
    conn.execute("SET hnsw_enable_experimental_persistence = true;")


def build_hnsw(conn: duckdb.DuckDBPyConnection) -> None:
    """One HNSW index over the vectors, cosine distance."""
    ensure_vss(conn)
    conn.execute("DROP INDEX IF EXISTS embeddings_hnsw")
    conn.execute(
        "CREATE INDEX embeddings_hnsw ON embeddings USING HNSW (vec) WITH (metric = 'cosine')"
    )
