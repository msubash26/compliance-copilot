# regops-retrieval

Four retrieval arms, two combinators, a cross-encoder and a context budget — over the Day 3
index, with one definition of "search" that the eval harness, the Day 4 gate and Day 6's agent
all share.

Until Day 5 these lived inside `regops_evals.corpus`. They moved because an eval package must
not own the thing it evaluates, and because Day 6's agent needs a retriever without importing a
benchmark (ADR-020). `regops_evals.corpus` imports them back under their old names, and a test
asserts `corpus.Index is regops_retrieval.index.Index` — so Day 4's published baseline and Day
5's C1 row are comparable by construction rather than by coincidence.

## The pieces

| | |
|---|---|
| `index.py` | Read-only DuckDB handle: clauses, chunks, vectors, BM25, and the metadata Day 4 selects on |
| `retrievers.py` | `Scored`, the `Retriever` protocol, `Bm25`, `Dense`, `Rrf`, `Rerank`, `Decomposed`, `QuestionVectors` |
| `rerank.py` | `BAAI/bge-reranker-v2-m3` on `transformers` + `torch` directly — no `sentence-transformers`, no `FlagEmbedding` |
| `context.py` | `assemble_context(hits, mode="parent"\|"child")` under a hard character budget, with truncation recorded |
| `decompose.py` | One LLM call per question, disk-cached by question hash |
| `configs.py` | The seven Day 5 configurations, as declared objects |

Everything composes because everything returns `list[Scored]`:

```python
from regops_retrieval import Bm25, Dense, Index, QuestionVectors, Rrf

ix, vecs = Index(Path("index/regdocs.duckdb")), QuestionVectors()
hybrid = Rrf((Bm25(ix), Dense(ix, vecs, model="nomic-embed-text:latest+ctx")))
hits = hybrid.search("what must a bank do when it cannot verify a customer?", 20)
```

`Scored` carries two ids, and the distinction is the parent-child ablation's whole mechanism:
`uid` is what was retrieved (a clause, or a chunk), `section_uid` is what gets scored. Metrics
always read `section_uid` — gold spans are clauses — and context assembly always reads `uid`.

## Two things that cost a day to learn

**A ranked list must be reproducible, and it took two fixes.** Six identical dense queries once
returned six orderings — an exact distance tie in the top 20, which DuckDB's parallel aggregation
does not break in a fixed order. A uid tie-break fixed that. BM25 was *still* unstable: it sums
term contributions in a parallel reduction, float addition is not associative, and the same query
returns scores differing in their last bit, so an exact-equality tie-break never fires on the
pairs it exists for — 10 of 40 real questions reordered their top-20 between runs. Every ranked
query therefore orders on a **rounded** score (`ROUND_DP = 9`) with the uid as tie-break, which
turns jitter into a real tie. Two independent sweeps now produce byte-identical rankings on all
150 golden items. See ADR-022.

**Context has to be budgeted, and the budget has to be measured.** Assembled as clauses, a top-5
is 5,848 characters at the median — and 46,417 at p90, 82,184 at the maximum, because a MAS
clause can run to 127,564 characters. Assembled as chunks the same top-5 is 3,156 / 4,516 /
5,916. Without a cap the parent-mode configurations would silently overflow the generator on the
tail and score zero for groundedness, and a write-up would read that as a retrieval result. So
`assemble_context` enforces a 24,000-character budget with a 40% per-excerpt share, and records
`truncated_excerpts` and `dropped_excerpts` **per query** — over the real sweep that is 42–62 of
150 queries on the parent path and **0 of 150** on the child path.

## The reranker

568M parameters, **1.33 GB in fp16**, 7.2s to load from the HF cache, and 138ms p50 to score 20
real clauses on the 3090. It runs on the `transformers` 5.8.1 + `torch` 2.13.0+cu130 already
installed for Docling: `AutoModelForSequenceClassification` with a pair input is what a
cross-encoder *is*, and a library that wraps that is a dependency bought for an import statement.

Tests never load it. The pipeline contract — reorders by score, truncates to `top_n`, keeps the
tail below the reranked window, deterministic under ties — is driven by a stub scorer, which is
the part that can be wrong in a way a results table hides. The real weights are exercised in one
test marked `slow` and skipped in CI.

## What it measured

See [`results/day5/retrieval.md`](../results/day5/retrieval.md). The short version: on this
corpus the cross-encoder is worth **+10.6 MRR points overall and +31 on `temporal`** against
**+3.7 on `comparative`** — an eightfold spread across query types, which is the whole routing
argument. Contextual embeddings are worth several MRR points on the dense arm alone but
**+0.9 once the reranker is on**: two mechanisms competing for the same ranking error. Query
decomposition **loses on every query type**, at 3.2× the latency, and the per-item rows say why —
over the 100 items both configurations retrieve, the first gold span is demoted on 36 and
promoted on 13, because RRF weights every sub-query equally and the original question ends up
with one vote in three.

## Development

```bash
uv run pytest retrieval -q          # 32 tests, no GPU, no model weights
uv run pytest retrieval -q -m slow  # the cross-encoder, and determinism on the real index
```
