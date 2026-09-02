# Regulatory Compliance Copilot

RAG + multi-agent system over MAS / SGX regulatory corpora, running fully local on an
RTX 3090 (air-gapped path), with a Bedrock parity path for cost/quality comparison.

**Status:** Day 5 — seven retrieval configurations measured over that set, with per-query-type
winners, a determinism fix that had to land first, and a routing rule read off the table.

## Layout

| Package | Role |
|---|---|
| `ingest/` | Parsing, hierarchical chunking, contextual retrieval, corpus manifest |
| `retrieval/` | Hybrid dense + BM25, RRF, cross-encoder rerank, context assembly |
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

Day 5 measured seven retrieval configurations against it. Whether that measurement can say
anything is a property of the eval set, not the retriever — and the first thing Day 4 measured is that a
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
**0.16** on the two multi-span types — that was the room reranking had to earn on Day 5, and the
next section is what it earned.

Verification runs on **`qwen3.8`, a different model from the generator**, because a model
agreeing with itself is not evidence. **0 of 35 negatives** turned out to be answerable, **0 of
115** questions could be answered without the corpus, and **29 of 150** items ship flagged rather
than deleted. Nothing has been reviewed by a human, every item says so, and a test asserts it.
See [`evals/README.md`](evals/README.md) and [`golden/v1/README.md`](golden/v1/README.md).

## The retrieval benchmark

Seven configurations, read as a **4-rung ladder plus 3 ablations** against the top rung — because
a factorial reading of the prep plan's list is 32 rows over 115 grounded items, and an ablation
needs a fixed reference to mean anything (ADR-020).

```bash
uv run regops-evals bench --index index/regdocs.duckdb --configs all \
                          --report results/day5/retrieval.md
uv run regops-evals generate-answers --configs ladder
uv run regops-evals judge --answers results/day5/answers
```

**Before any of it is believed:** C1 is BM25 and nothing else, so its row has to reproduce Day 4's
published baseline. It does, to three places — `hit@5` 0.670, `hit@20` 0.870, `full@5` 0.417 —
and `bench` exits non-zero if it ever stops doing so.

| config | hit@5 | full@5 | nDCG@10 | MRR | p50 | p95 |
|---|---|---|---|---|---|---|
| C1 BM25 | 0.670 | 0.417 | 0.481 | 0.486 | 0.016s | 0.020s |
| C2 dense +ctx | 0.661 | 0.417 | 0.518 | 0.517 | 0.092s | 0.102s |
| C3 hybrid RRF | 0.730 | 0.487 | 0.564 | 0.574 | 0.108s | 0.118s |
| **C4 + cross-encoder** | **0.835** | **0.574** | **0.661** | **0.681** | 0.514s | 0.541s |
| C5 — contextual off | 0.835 | 0.556 | 0.650 | 0.672 | 0.522s | 0.553s |
| C6 — parent-child off | 0.809 | 0.530 | 0.641 | 0.676 | 0.357s | 0.402s |
| C7 + decomposition | 0.661 | 0.478 | 0.533 | 0.532 | 1.643s | 2.195s |

n = 115 grounded items for the ranking columns, 150 for latency — a production p95 does not get to
exclude the questions whose answer is *not in the corpus*.

### What the table says that one number cannot

**Reranking is worth 32 MRR points on `temporal` and 4 on `comparative`.** Same reranker, same
400ms, an eightfold difference in what it buys:

| C3 → C4, MRR | factual_lookup | multi_hop | comparative | temporal |
|---|---|---|---|---|
| | +0.048 (n=45) | **+0.145** (n=30) | +0.037 (n=25) | **+0.318** (n=15) |

`temporal` questions ask *when* something took effect, and the answer lives in an amendment
endnote whose vocabulary is nearly identical to forty other endnotes. That is the disambiguation
a cross-encoder is for. A lookup that already ranks its clause first has nothing left to reorder.

**Contextual retrieval and the cross-encoder do the same job, and only one of them is needed.**
On the dense arm alone, `+ctx` is worth +6.7 MRR overall and +16.3 on `multi_hop` (ADR-015). With
the reranker on, turning it off (C5) costs **+0.9 MRR overall and 0.0 on `temporal`**. Two
mechanisms competing for the same ranking error, and the second one absorbs the first.

**BM25 beats dense on `multi_hop`; dense beats BM25 on `factual_lookup`.** +7.1 MRR to dense on
lookup (0.613 vs 0.542, n=45), −7.3 on hops (0.516 vs 0.589, n=30). Cross-references are
citations — literal strings — and that is lexical territory. Day 4 measured this and Day 5
reproduces it.

**Query decomposition loses on every single query type**, by 13–16 MRR points, at 3.2× the
latency. It was run on all 150 items precisely so that finding could exist: restricting it to the
types where it was expected to help would have assumed the conclusion. The per-item rows say why
— over the 100 items both C4 and C7 retrieve at all, the first gold span is **demoted on 36 and
promoted on 13**, with 9 more falling out of the top 20. Decomposition is not finding the wrong
documents; it is finding the right ones and pushing them down, because RRF weights every sub-query
equally and the original question ends up with one vote in three.

**Parent-child is not a recall axis, as predicted.** C6 is −0.4 MRR — noise — but **2.4× smaller
context** (4,264 vs 10,098 chars) and **0 of 150 queries truncated against 42**. The axis belongs
in the cost column, not the quality one — with one caveat the sensitivity run produced: on the
121 unflagged items the switch stops being flat and starts *hurting* `factual_lookup` and
`comparative`. It is the only recommendation here that depends on which 29 items are flagged, so
it ships as a cost optimisation to measure per deployment rather than as a free win.

### What the generation pass found

Groundedness, citation validity and abstention on the four ladder rungs × 150 items, judged by
`qwen3.8` — not the model that wrote the answers.

| config | groundedness | answered | citations valid | false-answer (35 neg) | false-abstention (115) | useful-answer rate |
|---|---|---|---|---|---|---|
| C1 BM25 | 0.821 | 78 | 0.833 | 0.057 | 0.322 | 0.557 |
| C2 dense +ctx | **0.880** | 75 | 0.867 | 0.057 | 0.348 | 0.574 |
| C3 hybrid RRF | 0.798 | 84 | 0.809 | 0.086 | 0.270 | 0.583 |
| **C4 + cross-encoder** | 0.870 | **92** | **0.891** | **0.029** | **0.191** | **0.696** |

**Groundedness is gameable and the table shows it.** C2 has the highest groundedness on the
fewest answers — refusing the hard questions leaves an easier set to be grounded on. The
*useful-answer rate* (grounded answers as a fraction of all 115 grounded items) cannot be traded
against caution that way, and it is the only column that is monotone down the ladder.

**Abstention is two rates because they are two different failures.** Answering a question the
corpus cannot answer is dangerous; refusing one it can is useless. Better retrieval improves both
at once — C4 fabricates least *and* refuses least.

**Part of the false-abstention column belongs to the golden set, not the retriever.** Every
configuration refuses flagged items at ~3× the rate it refuses unflagged ones (C4: 0.393 vs
0.126). Some are genuinely unanswerable as written — `gs-0005` asks *"when does this notice become
effective"* with no referent for *this notice*.

**And the benchmark found a defect in its own instrument.** C4's single false answer, `gs-0118`,
is not a fabrication: the system correctly reported that Notice 653 prescribes an NSFR Disclosure
Template, and the *item* is wrong to claim MAS mandates no templates. Day 4's verifier had that
clause at rank 3 and still passed the item at confidence 1.0, because it showed the judge only
the first 700 characters of a 12,689-character clause — and the answer begins at character 3,697.
A silent truncation is a judge being lied to about its evidence. The window is now 6,000
characters and whatever is still cut says so (ADR-024). So the affected number is quoted both
ways — C4's false-answer rate is **1/35 = 0.029 as measured, 0/35 excluding `gs-0118`**.

Day 6 re-verified the set through that wider window, and the item flagged *itself*: `gs-0118`
now fails `negative_is_answerable` and ships flagged at confidence 0.4, having previously passed
at 1.0. Nothing was hand-edited — under ADR-017 a flag comes from the checker — and the change is
**one item**: the split moved 122/28 → 121/29 and every ranking number above is byte-identical,
because the sensitivity subsets are over the 115 grounded items and this one is a negative.

### The routing rule this implies

Rerank everything (it is 400ms and never hurts); budget it against the query class rather than
the average; prefer the lexical arm on cross-reference questions; do not decompose; and treat
chunk assembly as a measured cost optimisation rather than a free 2.4× saving.

Full write-up, the 121-item sensitivity run, and per-item rows for every cell:
[`results/day5/retrieval.md`](results/day5/retrieval.md).

### One thing that had to be fixed before any of it counted

Six identical dense queries against this index returned **six different orderings** — one exact
distance tie in the top 20, and DuckDB's parallel aggregation does not break ties in a fixed
order. A uid tie-break fixed that, a test asserted it, and **BM25 was still not reproducible**:
three consecutive full sweeps of a pure-BM25 configuration over a fixed index returned MRR of
0.490, 0.495 and 0.486. BM25 sums term contributions in a parallel reduction, float addition is
not associative, and the same query returns scores differing in their last bit — so an
exact-equality tie-break never fires on the pairs it exists for. Over 40 real questions, **10
reordered their top-20 between runs**.

The fix is to round before ordering (`round(score, 9)`), which turns the jitter into a real tie
the uid can break: 10 of 40 unstable → **0 of 40**, and two independent sweeps now produce
byte-identical rankings on all 150 items.

The first test passed throughout, because a five-clause fixture with orthogonal vectors has no
near-ties for jitter to disturb — **a determinism test over clean synthetic data proves nothing
about determinism.** The second bug was found only by running the benchmark three times and
diffing the headline numbers. `hit@k` is a set test and survived both, which is why Day 4's
baseline was never wrong. See ADR-022.

## Decisions

[`DECISIONS.md`](DECISIONS.md) — 24 ADRs. The Day 5 ones:

- **ADR-020** The seven configurations as a ladder plus ablations, why a factorial reading was
  rejected, and the constants left untuned and admitted (RRF `k=60`, rerank `top_n`)
- **ADR-021** Retrieval metrics on all seven, generation metrics on four; what an empty cell
  means; why abstention is two rates and not one
- **ADR-022** Two determinism bugs, the second hidden by the fix for the first; why a
  determinism test over synthetic data proves nothing, and what both invalidated
- **ADR-023** Why `verify --no-judge` — the day's own pre-flight check — must not be able to
  overwrite the artifact it is checking
- **ADR-024** The negative set was verified through a 700-character window; how the benchmark
  found the one bad negative that produced, and why the fix is deferred rather than rushed

The Day 4 ones:

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
all decidable without a GPU, which is what lets them run in CI. Nor does the retrieval suite —
the cross-encoder's *pipeline* (reorders by score, truncates to `top_n`, deterministic under
ties) is driven by a stub scorer, which is the part that can be wrong in a way a results table
hides; the real 1.33 GB of weights are exercised in one test marked `slow` and skipped in CI. The ingest suite parses no PDFs: Docling's layout model was settled by reading its output on
three real documents, and what the tests guard is our code — the schema contract, idempotent
re-ingestion, clause-path disambiguation, OCR routing. The contract test is the important one:
it builds an index with this pipeline and drives `regdocs-mcp`'s four tools against it over
real JSON-RPC, so ADR-003's "the schema is the contract" is a test rather than a sentence.
