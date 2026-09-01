# Day 3 — Ingestion that survives real documents

**Repo:** `compliance-copilot` (member `regops-ingest`) · **Date:** 2026-09-03
**Budget:** ~4.5h build + 1h write-up

> Days 1–2 lived in `regdocs-mcp`; Day 3's work is the ingest pipeline, so the plan lives
> here. The only change on the server side is deleting nothing and proving nothing moved.

---

## Context

Day 1 shipped four MCP tools over a **provisional** index: PyMuPDF page text split on MAS's
numbered-clause convention, 463 documents → 8,055 sections. Day 2 added Streamable HTTP and
audience-validated auth. Both days are pushed with green CI (`regdocs-mcp` at 90 tests).

ADR-003 committed to this exact swap: *the index schema is the contract, the parser is
replaceable.* Day 3 is where that claim gets tested for real. `regdocs_mcp.build`'s own
docstring says Day 3 replaces it. Nothing in `regdocs_mcp.server` imports the parser, so if
the contract holds, the four tools should not move at all — and that is a test, not a hope.

### Carried forward from Days 1–2

- **Notices 817 and 818 are scanned images** with zero extractable text. They need OCR.
- **`effective_date` resolved for 341/463 (74%)** by front-matter regex. Docling's structure
  should do better, and the ones it cannot are genuinely undated.
- **`diff_versions` ships with an honest empty state (ADR-004).** History is born on the
  first re-fetch that finds a changed `sha256`. Day 3 owns idempotent re-ingestion, so Day 3
  owns making that mechanism real — without faking an amendment, which ADR-004 explicitly
  refused to do.

### Research completed before planning (ADR-002's rule, applied here)

Every number below was measured on this box today, not estimated.

**The corpus is bigger than the document count suggests.**

```
463 documents · 9,043 pages · median 7 pages/doc
notices 6,197 pages · guidelines 2,846 pages

  1-10 pages: 272 docs      101-300 pages:   6 docs
 11-50 pages: 157 docs           >300 pages:   1 doc
 51-100 pages:  27 docs
```

The outlier is **Notice 637 (Risk Based Capital Adequacy for Banks) at 1,110 pages** — Basel
capital rules, the single most table-dense document in the corpus. Six more sit between 131
and 260 pages, all capital/valuation notices. These seven documents are 2,326 pages, **26% of
the corpus in 1.5% of the files**, and they are precisely the ones a page-text splitter
mangles and Docling exists for.

**Exactly two documents need OCR** — a text-extraction sweep found 2 files under 200
characters, confirming the Day 1 finding is complete and not a sample.

**Contextual retrieval is affordable, but only just, and only one way.** Timed against
`qwen3.5:9b` on the local Ollama:

| | per chunk | × 8,055 chunks |
|---|---|---|
| `think=True` (default) | **7.98 s** | **17.9 hours** |
| `think=False` | **0.53 s** | **71 minutes** |

That is a 15× difference and it decides whether the day's headline technique is possible at
all. It is ADR-009 collecting: qwen3.5 is a reasoning model, thinking tokens bill to the
completion budget, and here they also ate the 120-token cap — the `think=True` call returned
a truncated answer *and* took eight seconds. Contextual retrieval wants a one-sentence
locator, which is the least reasoning-shaped task imaginable.

**Embeddings are not the bottleneck.** `nomic-embed-text` (already pulled, 768-dim) ran
**12.8 chunks/s** batched — about **10 minutes** for the whole corpus.

**No new container is needed.** DuckDB 1.5.5 loads the `vss` extension and offers HNSW, so
vectors live beside the sections in the same file. Day 0 left this open ("Qdrant or DuckDB
volume"); the stack is already seven containers and this adds none.

**Docling is current but heavy.** `docling` 2.124.0 (requires-python `>=3.10,<4`) resolves to
**121 packages including torch 2.13.0 and 15 `nvidia-*` CUDA wheels** — several GB. It lands
in the `compliance-copilot` workspace only. `regdocs-mcp` keeps its own venv and must never
acquire it; its CI has to stay a `uv sync` away from green without downloading a CUDA stack.
That constraint is what ADR-001's two-repo split bought, and Day 3 is the first day it pays.

---

## The four problems Day 3 has to solve

**1. Replacing the parser without moving the tool surface.**
*Resolution:* `regops-ingest` writes the same three tables `regdocs_mcp.index` defines. The
proof is a contract test that runs `regdocs-mcp`'s tool suite against a Docling-built index
and expects the same answers. If the tools need one edit, ADR-003 was wrong and that is the
finding worth reporting.

**2. Docling's throughput over 9,043 pages is unknown, and 26% of them sit in seven files.**
*Resolution:* a measured gate on 20 stratified documents before the full run, exactly like
Day 1's splitter gate. Notice 637 gets timed on its own, because an average that includes it
is a lie in both directions.

**3. Contextual retrieval needs document context that will not fit.**
The technique prepends an LLM-written sentence situating each chunk *in its document*. You
cannot put a 1,110-page notice in a 9B model's context, and the 0.53 s/chunk measurement
above used a short prompt — it is only representative if the real prompt stays short.
*Resolution:* the prompt carries a **structural outline** (title, doc type, effective date,
the clause-heading spine, the parent section's heading) rather than document text. That is
both what makes the measurement hold and, for legal text, the better signal: a clause's
position in the numbering *is* its context.

**4. Version history cannot be manufactured.**
*Resolution:* implement idempotent re-ingestion properly and prove it with a controlled
re-ingest (same URL, changed bytes) in a test. Do not stage a fake amendment in the real
index. ADR-004 turned down better-looking data than this for the same reason.

---

## Phase 0 — Housekeeping · 15 min

- [x] `gh auth status` — drifts back to `99Tungsten99`; switch to `msubash26` if needed
- [x] `./scripts/stack.sh ps` — 7 services; LangFuse is needed today for the first time since Day 0
- [x] `ollama ps` / warm `qwen3.5:9b`, confirm the 3090 is idle before timing anything
- [x] Re-read ADR-003 (the contract), ADR-004 (why no fake versions), ADR-012 (doc_id rules)

## Phase 1 — Install Docling and gate it on quality · 45 min

- [x] `uv add --package regops-ingest "docling>=2.124,<3"`. **Into the member, not the root**,
      and never into `regdocs-mcp`. Then `uv run --directory ../regdocs-mcp pytest -q` to
      confirm the server's venv is untouched and still green at 90.
- [x] Confirm Docling actually uses the GPU (watch `nvidia-smi` during a parse). CPU-only
      would change every number in Phase 2.
- [x] Parse **three** deliberately chosen documents and read the output by hand:
      a short notice (~7 pages), a prose guideline (~30 pages), and a table-dense capital
      notice (~130 pages).
- [x] **Gate — Docling has to earn its install.** Against the Day 1 splitter on the same three
      documents, it must show at least one of: tables preserved as structured rows rather than
      flattened text, a heading hierarchy the regex could not recover, or materially better
      clause boundaries. If it shows none, the honest outcome is a **hybrid**: PyMuPDF for
      text, Docling for tables only — and that gets written down rather than hidden.

## Phase 2 — Throughput gate, then start the long run · 30 min

- [x] Time Docling over **20 stratified documents** (sampled across the page buckets above),
      record seconds/page, extrapolate to 9,043 pages.
- [x] Time **Notice 637 alone**. If it exceeds ~30 minutes or exhausts VRAM, it gets its own
      handling (page-range batching) rather than blocking the corpus.
- [x] Route OCR **by detection, not globally**: extract text first, and only send the
      documents under a character threshold through Docling's OCR path. Two documents earn it;
      applying it to 9,043 pages would not survive the budget.
- [x] **Start the full parse in the background here**, and do Phases 3–5 while it runs. If the
      extrapolation says the run exceeds ~3 hours, it runs overnight and Phase 4 develops
      against the 20-document sample — say so in the plan rather than discovering it at 22:00.

## Phase 3 — The pipeline · 90 min

`regops_ingest.parse` → `regops_ingest.chunk` → `regops_ingest.load`, writing the schema
`regdocs_mcp.index` owns plus new tables beside it.

- [x] **Same three tables, unchanged.** `documents`, `sections`, `document_versions`.
      `sections.section_path` stays the document's own clause number — it is what a compliance
      officer cites and what the MCP tools return.
- [x] **New tables, additive only:**

```sql
chunks(chunk_id PK, doc_id, section_uid, ordinal, text,
       context_text,          -- the LLM-written locator, NULL until Phase 4
       char_len, token_len)
tables(table_id PK, doc_id, section_uid, page, caption, rows_json)
embeddings(chunk_id PK, model, dim, vec FLOAT[768])
```

- [x] **Parent-child chunking, and the parent is the clause.** `sections` is the parent,
      `chunks` the embedded child. Most corpora need an arbitrary parent window; MAS numbering
      hands us a real one. `get_document_section(doc_id, section_path)` already returns exactly
      that parent, so the retrieval design and the Day 1 tool surface agree by construction
      rather than by coincidence.
- [x] Deterministic IDs throughout: `doc_id` from the canonical URL (ADR-012, unchanged),
      `section_uid = doc_id:section_path`, `chunk_id = section_uid#ordinal`. Re-ingestion
      overwrites by key.
- [x] **Richer metadata**: notice number parsed from the title (`MAS Notice 626`), issuer,
      doc_type, clause path, and `effective_date` from Docling's front matter — **measure the
      new coverage against Day 1's 74%** and report the delta either way.
- [x] **Idempotent upsert.** Re-ingesting an unchanged corpus is a no-op; a changed `sha256`
      for a known `doc_id` inserts a `document_versions` row. That is the mechanism ADR-004
      said history depends on.

## Phase 4 — Contextual retrieval and embeddings · 60 min

- [x] Context prompt carries the **structural outline**, not document text (problem 3 above).
      **Re-time it on real prompts before committing to the full run** — the 0.53 s/chunk
      figure was measured at ~140 prompt tokens and only holds if the outline stays small.
- [x] `think=False` on every call, explicitly, with a comment pointing at ADR-009 and the
      15× measurement. This is the single line that makes the technique affordable.
- [x] Bounded concurrency against Ollama (start at 4, measure — the 3090 has 24 GB and the
      model is 6.6 GB, so there is headroom, but tokens/s per stream will fall).
- [ ] **Trace to LangFuse, sampled.** 8,055 traced generations would drown the project; sample
      ~1% plus every failure, and record total wall-clock and token counts as one summary
      trace. First real LLM workload since Day 0's hello-world.
- [ ] Embed **both** variants — raw chunk and context-prepended chunk — into `embeddings`
      under distinct `model` labels. Day 5 sweeps `contextual on/off`; that A/B is only clean
      if both vectors exist over the *same* chunks.
- [ ] HNSW index via DuckDB `vss`. Record build time and file size.

## Phase 5 — Traceability and tests · 40 min

- [x] **`regops-ingest trace <doc_id> <section_path>`** — prints the source PDF and page, the
      section text, its chunks, the context sentence, the embedding's model/dim/norm, and the
      metadata row. This *is* the prep plan's "done when", so it ships as a command rather
      than a screenshot.
- [x] **The contract test (ADR-003's claim, as a test).** Build a small index with the Docling
      pipeline, point `REGDOCS_INDEX` at it, and run `regdocs-mcp`'s tool assertions against
      it. Same tools, same shapes, no server edits. **This is the test not to cut.**
- [x] Idempotency test: ingest twice → identical row counts and IDs; ingest with mutated bytes
      → exactly one new `document_versions` row, and `diff_versions` stops returning its empty
      state.
- [x] OCR test: the two scanned notices yield non-empty sections.
- [x] A table test on a capital notice: rows survive as rows.

## Phase 6 — Write-up · 50 min

- [x] **ADR-013** — Docling replaces the provisional parser behind an unchanged schema; what
      the gate measured; OCR routed by detection rather than applied globally.
- [x] **ADR-014** — Parent-child chunking where the clause is the parent, and why this corpus
      hands us that for free.
- [x] **ADR-015** — Contextual retrieval costs 0.53 s/chunk with reasoning off and 7.98 s with
      it on; the outline-not-full-text prompt that keeps it there.
- [x] **ADR-016** — Vectors in DuckDB VSS rather than a Qdrant container: one file, no eighth
      service, and the honest limit (single-node, no replication — revisit if Day 12 goes cloud).
- [x] README (copilot): the ingest pipeline, the throughput table, the coverage deltas.
- [ ] Update `initial-setup.md` — Day 3 status, new numbers, any new gotchas.
- [ ] Note in `regdocs-mcp` that `build.py` is retained deliberately (see decision 3 below).
- [ ] Commit, push both repos, confirm CI green on both.

---

## Deliverables

A Docling pipeline over 463 documents / 9,043 pages writing the Day 1 schema unchanged ·
parent-child chunks with contextual locators · embeddings + HNSW in DuckDB · a `trace`
command proving PDF → clause → chunk → embedding → row · a contract test proving the MCP tool
surface did not move · 4 ADRs · green CI on both repos.

## Decisions I would want a steer on before Phase 4

1. **Embedding model.** `nomic-embed-text` is pulled, measured, 768-dim, and fast.
   BGE-M3 (1024-dim) is stronger on legal text but adds `sentence-transformers` and ~2 GB.
   *Recommendation: ship nomic as Day 3's baseline and make the model a config knob.* Day 5's
   sweep is where a model comparison earns its keep; hard-coding either choice today just
   moves the decision somewhere harder to change.
2. **Contextual-retrieval scope.** All 8,055 chunks (~71 min measured) vs the golden-set
   subset only. *Recommendation: all of it.* It is affordable now that reasoning is off, and a
   partially-contextualised corpus makes Day 5's A/B unclean in a way that is hard to caveat.
3. **Keep `regdocs_mcp.build` after Docling lands?** *Recommendation: yes, still marked
   provisional.* It is the reason `regdocs-mcp` stays cloneable and CI-green without a
   multi-GB CUDA download. Deleting it would make the standalone repo depend on the copilot's
   heavy pipeline to produce an index — exactly the coupling ADR-001 and ADR-003 exist to
   prevent.

## Risks

1. **Docling throughput on 9,043 pages.** The Phase 2 gate exists to find this before Phase 3
   builds on an assumption. Mitigation is scheduling, not scope: the full run goes to the
   background early and development continues against the 20-document sample.
2. **Notice 637 (1,110 pages) alone.** Timed separately; page-range batching if it misbehaves.
   Worst case it is ingested overnight and the other 462 proceed.
3. **The heavy install destabilises the copilot venv.** 121 packages, torch, 15 CUDA wheels.
   Fallback is `docling-slim` + PyMuPDF for text with Docling used only for tables — which is
   also Phase 1's gate-failure path, so it is one fallback, not two.
4. **The context prompt grows past the measurement.** Re-timed in Phase 4 before the full run
   commits. If it lands above ~2 s/chunk, contextual retrieval drops to the golden-set subset
   and says so.

**Descope order if behind:** contextual retrieval → golden-set subset · tables → text only ·
OCR → leave the two scanned notices out and name them. **Never cut** the contract test or the
`trace` command: one carries ADR-003's claim and the other is the day's "done when". Day 4's
golden set depends on this index existing, so nothing here may slip into Day 4's budget.

---

## Outcome

All six phases complete. 33 ingest tests green, `regdocs-mcp` still green at 90, ruff clean.
The index is 463 documents / 9,043 pages → 11,171 clauses → 22,090 chunks → 44,180 vectors
in a single 651 MB DuckDB file.

### What the plan got right

The measure-first phases paid for themselves twice. The Phase 1 gate settled whether Docling
earned a 121-package install before any pipeline code existed, and the Phase 2 throughput gate
turned a feared overnight run into a 25-minute one — which is why Phases 3–5 could develop
against a finished index rather than a sample.

### Where the plan was wrong, and what replaced it

- **The 1,110-page notice was never the risk.** The plan gave Notice 637 its own risk entry and
  its own timing budget. Measured: **166.8s, 0.15 s/page** — one of the *cheapest* documents
  per page in the corpus. Per-page cost tracks table density, not length; the actual worst case
  was a 42-page scanned notice at **2.6 s/page**, 17× worse. Page count was the wrong proxy and
  the gate is what said so.
- **The chunk count was 2.7× the estimate.** Phase 4 was budgeted against Day 1's 8,055
  sections. Parent-child chunking over a better parse produces **22,090 chunks**, so the plan's
  "71 minutes" was really 3.9 hours before anything went wrong.
- **Concurrency is not a lever.** The plan said "start at 4, measure". Measured on a free GPU:
  1 → 12 concurrent moves 0.65 → 0.62 s/item, **5% for a 12× increase**. Ollama serialises
  against one loaded model. The saving came from changing the *unit* instead — one locator per
  clause rather than per chunk (ADR-015), which is 2× and loses nothing, because the sentence
  situating chunk 2 of clause 6.14 is the sentence situating clause 6.14.
- **Pipeline stages cannot overlap.** The plan assumed the long parse could run in the
  background while later phases proceeded. True for Docling, false for Ollama: an embed call
  issued during the `context` run queued past its 300s timeout, because a second model cannot
  load while a continuous stream keeps the first one busy. `build`, `chunk`, `context`, `embed`
  run one at a time.
- **`think: false` forces the native API.** Day 0 had already recorded that Ollama's
  OpenAI-compatible endpoint ignores it. Since that flag is a 15× difference, contextual
  retrieval gives up `langfuse.openai`'s free instrumentation and traces by hand — sampled at
  1%, with every failure traced regardless.
- **The plan's three open decisions resolved as recommended**, all three on measured grounds:
  `nomic-embed-text` as the baseline with the model as a config knob; contextual retrieval over
  the full corpus (affordable once the unit changed); and `regdocs_mcp.build` retained, still
  marked provisional, because it is what keeps the server repo cloneable without CUDA.

### Findings worth carrying forward

- **`section_path` needed a disambiguation rule the plan did not anticipate.** MAS Notice 129
  restarts clause numbering inside roughly forty forms — 188 of its 221 paths collided. A
  positional suffix (`1#38`) would have destroyed the citation, so a repeat is qualified by its
  enclosing header (`Notes to Form A1/1`) while the first occurrence keeps the bare number.
  Corpus-wide this leaves 237 opaque paths of 11,171 (**2.1%**).
- **The trace command earned itself immediately.** Running it on one real clause exposed that
  locators were being generated from `min(text)` — lexicographic, not ordinal — so 23% of
  multi-chunk clauses were described from an arbitrary middle chunk, and clause 6.14 came back
  named "6.14A". Fixed and re-run. A summary statistic would not have shown this; reading one
  record end to end did.
- **Letter-suffixed clauses are a known, measured gap.** MAS amendments insert `6.14A`, and
  Docling does not treat those as enumerations, so they stay inline inside the parent clause:
  **190 of 11,171 sections (1.7%)** contain such a marker. No text is lost and it is still
  retrievable under the parent, but it is not separately citable. Recovering it means an inline
  regex over text items — the approach Docling replaced — so it waits until Day 4's golden set
  says whether it matters.
- **`effective_date` improved with the extractor held constant.** 73.6% → **88.3%**, using the
  same function imported from `regdocs_mcp.build`. That makes the delta attributable to input
  quality rather than a better regex, which is the only reason the number means anything.
- **Contextual retrieval cost, in full:** 11,171 clauses, 0 failures, 7,177s (2.0h) at 0.64
  s/clause, 3.60M prompt and 0.45M completion tokens. Embedding both arms is comparatively
  free: 44,180 vectors at 57–71 chunks/s, HNSW in 14.4s.
- **DuckDB does not reclaim space, and re-runs are the normal case.** A second `embed` pass
  inflated the index from 651 MB to **2,926 MB holding identical data**. `COPY FROM DATABASE`
  into a fresh file returns it to **433 MB in 57s**, carrying HNSW and BM25 intact. Shipped as
  `regops-ingest compact` rather than left as folklore.
- **LangFuse 4.24 writes to `events_core`/`events_full`,** not the legacy `traces`/`observations`
  tables, and the public `/api/public/traces` endpoint 404s on this deployment. Both legacy
  tables read 0 rows while tracing works perfectly — which is exactly how a working trace comes
  to look broken. Verified instead by counting in ClickHouse: 25 `locator` generations and 1
  `contextual-retrieval` summary span from a fully-sampled batch.

### End-to-end proof

The four Day 1 tools, unmodified, driven over JSON-RPC against the real Docling-built index:
`search_notices("identify the beneficial owner")` returns **1,432 hits** led by three genuine
beneficial-ownership clauses (`6.14`, `6.13`, `6.16`) across three different notices;
`get_document_section` returns the clause; `list_obligations` extracts all three modalities.
Vector search over both arms puts Notice 626 clause 6.14 top-1 for a natural-language question
in 0.2–0.5s. That is ADR-003's claim, discharged on real data.
