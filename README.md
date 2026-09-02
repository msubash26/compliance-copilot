# Regulatory Compliance Copilot

RAG + multi-agent system over MAS / SGX regulatory corpora, running fully local on an
RTX 3090 (air-gapped path), with a Bedrock parity path for cost/quality comparison.

**Status:** Day 4 — a 150-item golden set over the Day 3 index, machine-verified by a second
model, with a published saturation baseline per query type.

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
uv run regops-ingest compact --index index/regdocs.duckdb --replace       # reclaim space after a re-run
```

Run them **one at a time**. Ollama serialises against one loaded model, so an `embed` call
issued while `context` is running queues past its timeout rather than sharing the GPU.

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

Contextual retrieval: **11,171 locators, 0 failures, 2.0h at 0.64 s/clause**, traced to
LangFuse at 1% sampling. Embedding both arms: **44,180 vectors** at 57–71 chunks/s, HNSW in
14.4s. The finished index is **433 MB** — after `compact`, which matters, because a re-run
inflates the same data to 2.9 GB (ADR-016).

### Traceability

`trace` is the pipeline's "show your working": one clause, from source PDF to vector.

```bash
uv run regops-ingest trace <doc_id> 6.14 --index index/regdocs.duckdb
```

It prints the document and its versions, the source file and page range, the clause text, every
child chunk with its context sentence, and each embedding's model, dimension and norm.

## The golden set

Day 5 measures seven retrieval configurations. Whether that measurement can say anything is a
property of the eval set, not the retriever — and the first thing Day 4 measured is that a
*naively* built set says nothing: questions drawn from random clauses gave BM25 **92% recall@5**
and dense 92%, at ceiling before any variant is applied. Seven configurations, seven identical
rows.

Difficulty is therefore engineered from the corpus's own structure. MAS publishes near-identical
AML/CFT notices for 25 classes of institution, so clause 6.14 of Notice 626 has **13 near
duplicates within cosine 0.10**, differing mainly in *whom they bind*. Selection is stratified by
that crowding; every contested question names its entity class, so the distractors are
defeatable rather than unfair.

```bash
uv run regops-evals select   --index index/regdocs.duckdb --out golden/v1/candidates.json
uv run regops-evals generate --candidates golden/v1/candidates.json --out golden/v1/golden.jsonl
uv run regops-evals verify   --index index/regdocs.duckdb --golden golden/v1/golden.jsonl \
                             --queue golden/v1/review_queue.md --report golden/v1/verification.json
uv run regops-evals gate     --index index/regdocs.duckdb --golden golden/v1/golden.jsonl --k 5
```

150 items — 45 factual, 30 multi-hop, 25 comparative, 15 temporal, **35 negative** — each pinning
`doc_id`, `section_path` and a `span_sha256` of the gold text. Measured over the finished set:

| query type | bm25 hit@5 | dense hit@5 | bm25 full@5 | dense full@5 | n |
|---|---|---|---|---|---|
| `factual_lookup` | 0.733 | 0.733 | 0.733 | 0.733 | 45 |
| `multi_hop` | **0.800** | 0.600 | 0.167 | 0.167 | 30 |
| `comparative` | 0.560 | 0.560 | 0.160 | 0.160 | 25 |
| `temporal` | 0.400 | 0.333 | 0.400 | 0.333 | 15 |
| **overall** | **0.670** | **0.609** | **0.417** | **0.409** | 115 |

Headroom on both arms, and the rows already diverge. `full@5` (every gold span retrieved) sits at
**0.16** on the two multi-span types — that is the room reranking and metadata filtering have to
earn on Day 5.

Verification runs on **`qwen3.8`, a different model from the generator**, because a model
agreeing with itself is not evidence. **0 of 35 negatives** turned out to be answerable, **0 of
115** questions could be answered without the corpus, and **28 of 150** items ship flagged rather
than deleted. Nothing has been reviewed by a human, every item says so, and a test asserts it.
See [`evals/README.md`](evals/README.md) and [`golden/v1/README.md`](golden/v1/README.md).

## Decisions

[`DECISIONS.md`](DECISIONS.md) — 19 ADRs. The Day 4 ones:

- **ADR-017** The set is machine-built and machine-verified, with a stated human boundary; why
  the verifier is a different model; why a model's self-report of knowledge is worth nothing
- **ADR-018** The query-type taxonomy, and why `temporal` means stated-time rather than
  version-diff on this corpus
- **ADR-019** Difficulty is engineered from entity-class near-duplication; the measured
  distances; why a shared clause number does not mean a shared topic

The Day 3 ones:

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

The evals suite calls no model: the schema, span-drift, leakage and stratification claims are
all decidable without a GPU, which is what lets them run in CI. The ingest suite parses no PDFs: Docling's layout model was settled by reading its output on
three real documents, and what the tests guard is our code — the schema contract, idempotent
re-ingestion, clause-path disambiguation, OCR routing. The contract test is the important one:
it builds an index with this pipeline and drives `regdocs-mcp`'s four tools against it over
real JSON-RPC, so ADR-003's "the schema is the contract" is a test rather than a sentence.
