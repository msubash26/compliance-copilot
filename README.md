# Regulatory Compliance Copilot

RAG + multi-agent system over MAS / SGX regulatory corpora, running fully local on an
RTX 3090 (air-gapped path), with a Bedrock parity path for cost/quality comparison.

**Status:** Day 3 — Docling ingestion over 463 documents / 9,043 pages, parent-child chunks
with contextual locators, embeddings and HNSW in DuckDB.

## Layout

| Package | Role |
|---|---|
| `ingest/` | Parsing, hierarchical chunking, contextual retrieval, corpus manifest |
| `retrieval/` | Hybrid dense + BM25, RRF, cross-encoder rerank, metadata filters |
| `agents/` | LangGraph supervisor, Pydantic AI comparison agent |
| `evals/` | Golden set, retrieval benchmark, agent eval suite |
| `serving/` | vLLM / Ollama serving, model routing, semantic cache |
| `api/` | FastAPI service + thin UI |

The MCP server lives in its own repo: [regdocs-mcp](https://github.com/msubash26/regdocs-mcp),
consumed here as an editable path dependency. Docling and its CUDA stack land in **this**
workspace only, so the server stays a `uv sync` from green CI without a multi-GB download
(ADR-001, ADR-013).

## Quickstart

```bash
uv sync
cp .env.example .env          # fill every blank: openssl rand -hex 32
./scripts/stack.sh up         # LangFuse + ClickHouse + MinIO + Redis + 2x Postgres
uv run python scripts/hello_trace.py
```

LangFuse UI at <http://localhost:3000>. See [docker/README.md](docker/README.md) for the port
map — the host already owns 5432 and 6379, so containers are remapped.

## The ingest pipeline

Four re-runnable stages. Parsing is the expensive one, so the others can be redone without it.

```bash
uv run regops-ingest build   --corpus corpus --out index/regdocs.duckdb   # PDFs  -> sections + tables
uv run regops-ingest chunk   --index index/regdocs.duckdb                 # sections -> child chunks
uv run regops-ingest context --index index/regdocs.duckdb                 # clause  -> locator sentence
uv run regops-ingest embed   --index index/regdocs.duckdb                 # chunks  -> vectors + HNSW
```

The result is one DuckDB file holding documents, clauses, chunks, tables, vectors and the BM25
index. Point the MCP server at it and the Day 1 tools serve it unchanged:

```bash
REGDOCS_INDEX=$PWD/index/regdocs.duckdb uv run --directory ../regdocs-mcp regdocs-mcp
```

### Measured over the full corpus

| | Day 1 (PyMuPDF) | Day 3 (Docling) |
|---|---|---|
| sections | 8,055 | **11,171** (+39%) |
| tables | 0 — flattened into text | **2,173** (17,538 rows) |
| `effective_date` resolved | 341/463 (73.6%) | **409/463 (88.3%)** |
| scanned documents readable | 0 of 2 | **2 of 2** (OCR by detection) |
| headings recovered | 0 on all three gate documents | 13/14, 57/70, 140 |

Parsing 9,043 pages takes **1,484s (0.164 s/page)** on the 3090. Per-document cost is driven by
table density, not length: the 1,110-page Notice 637 runs at 0.15 s/page while a 42-page
scanned notice hits 2.6 s/page.

Chunking gives **22,090 chunks**, 1.98 per clause, median 928 characters — most clauses are a
single chunk, because the parent is a real unit rather than an invented window (ADR-014).

### Traceability

`trace` is the pipeline's "show your working": one clause, from source PDF to vector.

```bash
uv run regops-ingest trace <doc_id> 6.14 --index index/regdocs.duckdb
```

It prints the document and its versions, the source file and page range, the clause text, every
child chunk with its context sentence, and each embedding's model, dimension and norm.

## Decisions

[`DECISIONS.md`](DECISIONS.md) — 16 ADRs. The Day 3 ones:

- **ADR-013** Docling replaces the provisional parser behind an unchanged schema; what the
  quality gate measured; OCR routed by detection rather than applied to 9,043 pages
- **ADR-014** Parent-child chunking where the clause is the parent, and how a clause number
  that repeats inside forty appendices stays citable
- **ADR-015** Contextual retrieval: reasoning off (15×), per clause rather than per chunk (2×),
  outline rather than document text
- **ADR-016** Vectors in DuckDB VSS rather than an eighth container

## Development

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format .
```

The ingest suite parses no PDFs: Docling's layout model was settled by reading its output on
three real documents, and what the tests guard is our code — the schema contract, idempotent
re-ingestion, clause-path disambiguation, OCR routing. The contract test is the important one:
it builds an index with this pipeline and drives `regdocs-mcp`'s four tools against it over
real JSON-RPC, so ADR-003's "the schema is the contract" is a test rather than a sentence.
