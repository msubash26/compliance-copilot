# Decisions (ADRs)

One entry per significant choice, dated. Newest last.

---

## ADR-001 — Two repos, not one monorepo
**Date:** 2026-08-30 · **Status:** Accepted

**Context.** The plan calls for a uv-workspace monorepo, but the deliverables require
`regdocs-mcp` to be an independently publishable, cloneable repo.

**Decision.** Two sibling repos under `~/regops`: `regdocs-mcp` (standalone, public) and
`compliance-copilot` (uv workspace). The copilot consumes the server as an editable path
dependency (`../regdocs-mcp`).

**Alternatives rejected.** Single monorepo + `git subtree split` to publish the server —
splitting history later is error-prone and the published repo's history reads oddly.
Git submodule — adds clone/update friction for a repo that is edited daily in week 1.

**Consequence.** The copilot's CI must check out *both* repos side by side to reproduce the
path dependency (see `.github/workflows/ci.yml`). Accepted as the cost of a clean clone story.

---

## ADR-002 — Workspace member packages are name-prefixed
**Date:** 2026-08-30 · **Status:** Accepted

**Decision.** Directories keep the plain names from the plan (`ingest/`, `retrieval/`,
`agents/`, `evals/`, `serving/`, `api/`), but distribution names are `regops-*` and modules
are `regops_*`.

**Rationale.** `ingest`, `api`, `agents` and `evals` are all live names on PyPI. Unprefixed
modules would shadow or be shadowed by a real dependency, and the failure mode is a confusing
import error weeks later.

---

## ADR-003 — Containers avoid host ports 5432 and 6379
**Date:** 2026-08-30 · **Status:** Accepted · **Amended:** 2026-08-30

**Context.** A host Postgres already listens on 5432 — and, found during B2, a host
`redis-server` on 6379.

**Decision.** No container publishes on a port a host service owns. Every connection string in
`.env`, compose files and the LangGraph checkpointer config uses the remapped port.

**Rationale.** Left on 5432, the container would either fail to bind or — worse — application
code would silently connect to the host database and write checkpoints there.

**Amendment (2026-08-30).** The original wording said "all containerised Postgres is published
on 5433". There are now two Postgres containers (ADR-004), so the map is explicit:

| Port | Service | Owner |
|---|---|---|
| 5433 | `checkpointer-postgres` | ours — the only one code connects to |
| 5434 | LangFuse `postgres` | LangFuse; inspection only |
| 6380 | LangFuse `redis` | LangFuse; inspection only |

---

## ADR-004 — The LangGraph checkpointer gets its own Postgres container
**Date:** 2026-08-30 · **Status:** Accepted · **Amended:** 2026-08-30

**Decision.** Checkpoint state and trace state are kept in separate Postgres *instances*:
`checkpointer-postgres` (ours, 5433) and LangFuse's own `postgres` (5434).

**Rationale.** The Day 7 deliverable is "a run survives a process restart and resumes".
Debugging that is far easier when checkpoint state can be dropped and inspected without
touching the trace store.

**Amendment (2026-08-30).** Originally this meant two databases inside one Postgres. That was
written before B2 established that LangFuse self-hosts *its own* Postgres container, whose
schema its migration runner owns and rewrites on every version bump. Putting our checkpoint
tables in that instance means a LangFuse upgrade can touch our data, and `docker compose down
-v` couples the two lifecycles. Superseded by a **second Postgres container**,
`checkpointer-postgres`, published on 5433. Same rationale, stronger isolation, and ADR-003
still holds.

---

## ADR-005 — Local-first inference; hosted APIs only as the parity baseline
**Date:** 2026-08-30 · **Status:** Accepted

**Decision.** Ollama (already holds `qwen3.8`, `nomic-embed-text`) for iteration, vLLM for the
Day 9 serving benchmark. Hosted APIs appear only as the comparison arm.

**Rationale.** The differentiating claim is an air-gapped stack with no data leaving the
perimeter. That claim is only credible if the default path is local, including the Day 0
hello-world trace.

---

## ADR-006 — LangFuse pinned to v4 on both sides; the v4 stack is six services
**Date:** 2026-08-30 · **Status:** Resolved

**Context.** The plan assumed LangFuse v2/v3. Resolution produced SDK **4.15.1**, and it was
unclear whether the v4 self-host stack still required ClickHouse + Redis + MinIO, and what
that cost in RAM alongside vLLM on one box.

**Resolved.** Pulled the official compose file
(`langfuse/langfuse@67eec1cb`, fetched 2026-08-30) and read it rather than guessing:

- Server images are tagged `:4` — matching SDK 4.15.1, so `langfuse>=4,<5` is correct and stays.
- The stack **is** six services: `langfuse-web`, `langfuse-worker`, `clickhouse:25.12`,
  `minio`, `redis:7`, `postgres:17`. ClickHouse and Redis are not optional in v4 — ingestion
  is async and goes Redis queue → worker → ClickHouse.
- RAM is a non-issue on this box: ~4–6 GB against 22 GB available, and vLLM's footprint is
  VRAM, not host RAM. Revisit only if the Day 9 benchmark runs concurrently with the stack.

**Consequence.** `TELEMETRY_ENABLED` defaults to `true` upstream and is forced to `false` in
`.env.example` — the air-gapped claim (ADR-005) has to hold for the observability plane too.

---

## ADR-007 — Upstream compose is vendored verbatim; local deltas live in an override
**Date:** 2026-08-30 · **Status:** Accepted

**Context.** Upstream's compose publishes host ports this workstation already owns:
`127.0.0.1:5432` (host PostgreSQL 16, pid 2478) and `127.0.0.1:6379` (host redis-server,
pid 2297). As shipped, `docker compose up` fails to bind on two services.

**Decision.** `docker/docker-compose.yml` is a verbatim vendored copy carrying a provenance
header and is never edited. Every local change — the port remaps and our
`checkpointer-postgres` — lives in `docker/docker-compose.override.yml`. Both files are
passed via `scripts/stack.sh`.

**Port map.** LangFuse Postgres → 5434, LangFuse Redis → 6380, checkpointer → 5433. Both
LangFuse remaps are inspection-only; the containers reach each other on the compose network
at their default ports, so no LangFuse env var changes.

**The trap.** Compose *concatenates* multi-value keys (`ports`, `expose`, `dns`, `tmpfs`) when
merging files — it does not replace them. A naive override republishes upstream's 5432
*alongside* 5434 and the bind still fails. The override therefore uses the `!override` YAML
tag (Compose ≥ 2.24; this box runs 2.35.1). Verified with `docker compose config`: postgres
resolves to a single published 5434, redis to a single 6380.

**Alternative rejected.** Editing the vendored file in place — it makes refreshing from
upstream a manual three-way merge, and LangFuse ships schema-relevant compose changes between
minors.

**Consequence (tooling).** `pre-commit`'s `check-yaml` cannot construct the `!override` tag —
no generic YAML parser can, it is a Compose extension. The hook is split: the override file is
checked with `--unsafe` (syntax only, unknown tags tolerated), everything else normally.
`docker compose config` is the real validator for these files and is what CI should call.

**Consequence.** Never run `docker compose -f docker/docker-compose.yml up` directly; the
override is not auto-discovered from a non-default filename. `scripts/stack.sh` is the entry
point and refuses to run without a `.env`.

---

## ADR-008 — Credentials that upstream embeds in defaults must be set explicitly
**Date:** 2026-08-30 · **Status:** Accepted

**Context.** Rotating the compose passwords off their shipped defaults broke the stack.
LangFuse came up but `langfuse-web` exited during migration with Prisma `P1000:
Authentication failed`.

**Cause.** Upstream does not compose its connection strings from the `*_PASSWORD` variables —
it embeds the default credential a second time, in a different variable:

```
POSTGRES_PASSWORD:   ${POSTGRES_PASSWORD:-postgres}
DATABASE_URL:        ${DATABASE_URL:-postgresql://postgres:postgres@postgres:5432/postgres}
                                                        ^^^^^^^^ not derived
```

So setting `POSTGRES_PASSWORD` alone initialises Postgres with the new password while LangFuse
keeps authenticating with the literal `postgres`. MinIO has the same shape:
`MINIO_ROOT_PASSWORD` against three separate `LANGFUSE_S3_*_SECRET_ACCESS_KEY` defaults.

**Decision.** `.env` sets all four derived variables explicitly, next to the passwords they
must track: `DATABASE_URL`, and the event / media / batch-export S3 secret keys.
`.env.example` carries them as `<POSTGRES_PASSWORD>` / `<MINIO_ROOT_PASSWORD>` placeholders
with the reason written out.

**Not affected.** `CLICKHOUSE_PASSWORD` and `REDIS_AUTH` are referenced by name on both the
server and client side, so they stay consistent under rotation. Audited the full compose:
those four are the only offenders.

**Note.** The hostnames in `DATABASE_URL` and the S3 endpoints are compose-network internal
(`postgres:5432`, `minio:9000`) — *not* the remapped host ports from ADR-003. Substituting
5434 there is a natural mistake and fails only at runtime.

**Consequence.** Passwords must stay URL-safe or be percent-encoded, since one of them is
carried inside a URL. The generator uses hex, which sidesteps this.

---

## ADR-009 — Reasoning tokens are billed to the completion budget on qwen3.5
**Date:** 2026-08-30 · **Status:** Accepted

**Context.** The first `hello_trace.py` run returned an empty answer with 160 completion tokens
consumed. `qwen3.5:9b` is a reasoning model: it emits thinking into a separate `reasoning`
field, and those tokens are billed against `max_tokens`. A limit sized for the visible answer
alone silently yields empty `content` with `finish_reason="length"` — no error, just nothing.

**Measured**, same one-sentence question, `qwen3.5:9b`:

| Path | Completion tokens | Latency |
|---|---|---|
| OpenAI-compat endpoint (thinking on) | 1140 | 13.1 s |
| Native `/api/chat`, `think: false` | **52** | **0.8 s** |

22x the tokens, 16x the latency, for the same answer.

**Decision.** `MAX_TOKENS = 2048` in `hello_trace.py`, and it fails loudly rather than
returning an empty string when `finish_reason == "length"` with no content.

**Finding for Day 9.** Thinking cannot be disabled over the OpenAI-compatible endpoint —
neither `extra_body={"think": False}` nor `reasoning_effort` is honoured; only Ollama's native
`/api/chat` respects `think: false`. This directly threatens the plan's "small model handles
classification, extraction and lookup" routing: a small *reasoning* model is not cheap, and on
a lookup task it is ~20x more expensive than its parameter count suggests. Day 9 must either
route through the native API for those tasks, pick a non-reasoning small model, or measure
vLLM's own controls. Benchmark thinking-on and thinking-off as separate arms.

---

## ADR-010 — LangFuse v4 `events_only` mode: read traces via the v2 API, not v1
**Date:** 2026-08-30 · **Status:** Accepted

**Context.** The B3 trace ingested correctly but `GET /api/public/traces/{id}` returned 404:
*"This endpoint is not available on deployments running in Langfuse v4 events_only mode."*

**Cause.** Not a misconfiguration. `events_only` is the **default write mode for new v4
deployments** — v3's `legacy`/`dual` modes exist only as migration waypoints. Data lands in
ClickHouse `events_core` / `events_full`, and the legacy `traces` / `observations` tables stay
empty by design. Confirmed: `SELECT count() FROM traces` = 0 while `events_core` = 6.

**Audited endpoint availability on this deployment:**

| Endpoint | Status |
|---|---|
| `/api/public/traces`, `/api/public/observations` | 404 — removed in `events_only` |
| `/api/public/metrics` (v1) | 404 — removed |
| `/api/public/v2/observations` | ✅ list + cursor pagination |
| `/api/public/v2/metrics` | ✅ aggregates |
| `/api/public/projects` | ✅ |

**Decision.** Stay on `events_only` — it is the forward path, and reverting to `legacy` on a
new deployment would mean adopting a mode that exists solely to be migrated off. Everything
that reads traces programmatically targets the v2 API.

**Consequence for Days 5, 8 and 9.** The eval harness and benchmark reporting must not use the
v1 endpoints that most tutorials and older blog posts still show. `/api/public/v2/metrics`
already returns what the results tables need — verified:

```
{"view":"observations","metrics":[{"measure":"totalTokens","aggregation":"sum"},
                                  {"measure":"latency","aggregation":"p95"}],
 "dimensions":[{"field":"providedModelName"}], ...}
→ {"providedModelName":"qwen3.5:9b","sum_totalTokens":4972,"p95_latency":13671.5}
```

Note `/api/public/v2/observations` returns a slim projection — no `model` or `usageDetails`.
Per-observation token counts come from `/api/public/v2/metrics`, or from ClickHouse directly.

---

## ADR-011 — Corpus is MAS-only; document *type* is the variety axis
**Date:** 2026-08-30 · **Status:** Accepted

**Context.** The plan called for a MAS-heavy corpus with a ~20% SGX slice, so that Day 5 could
show "retrieval behaves differently by document type".

**Decision.** MAS only. Variety comes from MAS's own document types rather than from a second
issuer.

**Why SGX was dropped.** `sgx.com` is client-side rendered — `curl` on
`/regulation/public-consultations` returns **0 bytes** — and the rulebooks live on a separate
JS application at `rulebook.sgx.com`. Extracting them needs a headless browser, which is a
disproportionate cost for a fifth of the corpus. The plan already earmarks the ~140 42 Macro
reports as the deliberately contrasting corpus (narrative prose vs. legal text), so the
"different document shapes" finding does not depend on SGX.

**Where the variety comes from instead.** Four MAS sections, genuinely different in shape:
`notices` (prescriptive, clause-numbered), `guidelines` (advisory prose), `circulars` (short,
operational), `consultations` (long, discursive). The sitemap yields 338 / 126 / 179 / 426
landing pages respectively. Day 0 fetches notices + guidelines; the rest are one flag away.

**Revisit if** an interview pipeline skews hard to SGX, in which case a headless-browser
fetcher for the rulebook is a half-day, not a Day 0 task.

---

## ADR-012 — Corpus fetch: URL-derived IDs, committed manifest, enforced politeness
**Date:** 2026-08-30 · **Status:** Accepted

**`doc_id` is `sha256(canonical_url)[:16]`, never derived from file bytes.** MAS reissues PDFs
in place under the same URL. A byte-derived ID would mint a second document on every amendment
and break Day 3's idempotent re-ingestion; a URL-derived one updates the same logical document.
`canonical()` strips query and fragment and lowercases the host, so the cache-busting `?v=`
suffixes MAS emits do not fork the ID.

**The manifest is committed; the PDFs are not.** `corpus/manifest.jsonl` carries
`{doc_id, url, source_page, issuer, doc_type, title, filename, sha256, bytes, fetched_at}`.
The PDFs are third-party documents and bulky — `sha256` is what makes a re-fetch verifiable.

**`.gitignore` bug fixed.** The Day 0 rules were `corpus/` followed by `!corpus/manifest.jsonl`.
Git cannot re-include a file whose *parent directory* is excluded, so the negation never fired
and the one artifact B5 exists to produce was silently unstageable. Now `corpus/*` +
`!corpus/manifest.jsonl`.

**Politeness is enforced, not assumed.** `robots.txt` is parsed with
`urllib.robotparser` and consulted per URL; MAS publishes `Crawl-delay: 2`, which is the
default and the script warns if overridden. Re-runs skip anything already fetched, so an
interrupted crawl re-requests only what it missed.

**User-Agent must keep its `Mozilla/5.0 (compatible; ...)` prefix.** MAS's WAF answers any
other UA with an HTML "Maintenance" page at **HTTP 200** — which parses as a sitemap with zero
entries, so it looks like an empty result rather than a refusal. This cost real debugging time.
The `Mozilla/5.0 (compatible; <product>; +<url>)` form is the standard well-behaved-crawler
convention (Googlebot, bingbot) and keeps the crawler identifiable via product token and
contact URL. `tests/test_fetch_corpus.py` guards it.

---

## ADR-013 — Docling replaces the provisional parser behind an unchanged schema
**Date:** 2026-09-03 · **Status:** Accepted

**Context.** ADR-003 in `regdocs-mcp` committed to a swap: the index schema is the contract,
the Day 1 PyMuPDF parser is provisional, and Day 3's pipeline would replace it without the four
MCP tools moving. This is that swap.

**Decision.** `regops_ingest.parse` uses Docling 2.124.0 (CUDA) and writes the same three
tables `regdocs_mcp.index` defines. `regdocs_mcp.build` is retained, still marked provisional.

**Docling had to earn a 121-package install**, including torch 2.13.0 and 15 `nvidia-*` CUDA
wheels. Measured against the Day 1 splitter on three deliberately chosen documents — a 6-page
notice, a 25-page prose guideline, a 131-page forms notice:

| | Day 1 splitter | Docling |
|---|---|---|
| short notice | 11 sections, paths jump `3.2 → 5` | 14 sections, `1.1`–`6.2` unbroken |
| prose guideline | 26 sections, paths jump `9 → 12` | 70 sections, full `3.1.1` hierarchy |
| forms notice (131p) | 23 sections | 221 sections |
| headings recovered | **0 of 3 documents** | 13/14, 57/70, 140 headers |
| tables | none — flattened into text | 1, 65 |

**The mechanism, not just the score.** The regex recovered clause numbers by matching
line-leading digits, which forced two heuristics that are structure questions in disguise:
telling a footnote marker from a clause number, and telling a page number from a section
marker. Docling answers both by *label* — `footnote`, `page_header`, `page_footer` arrive
tagged — and hands back MAS's own clause number in `ListItem.marker`, with lettered limbs
`(a)`/`(b)` arriving as `enumerated=False` and staying attached to their parent clause. The
Day 1 splitter did not lose clause 4's *text*; it merged it into 3.2, which is worse than
losing it, because a citation then points at the wrong clause.

**OCR is routed by detection, not applied globally.** Parse without OCR, and re-run only
documents that yield under 200 characters. Exactly 2 documents of 463 are scans; global OCR
would bill 9,043 pages to serve two. On the full run it fired on exactly those two — Notices
817 and 818, the Day 1 carried-forward debt — and both now have text.

**Measured over the full corpus:** 463 documents, 9,043 pages, **11,171 sections in 1,484s**
(0.164 s/page; median 0.085, max 16.9). Day 1 produced 8,055 sections, so this is +39%.
`effective_date` resolved for **409/463 (88.3%)** against Day 1's 341/463 (73.6%) — using the
*same* extractor, imported from `regdocs_mcp.build`, so the +14.7 points are attributable to
input quality alone rather than to a better regex. 2,173 tables carrying 17,538 rows were
recovered where Day 1 had none.

**The consequence that justifies ADR-001's two-repo split.** Docling lands in the
`compliance-copilot` workspace only. `regdocs-mcp` keeps its own venv, stays a `uv sync` from
green CI, and needs no multi-GB CUDA download to be cloneable. Verified after the install:
`regdocs-mcp` still passes 90 tests and `import docling` fails in its venv. Day 3 is the first
day that split pays for itself.

---

## ADR-014 — Parent-child chunking where the clause is the parent
**Date:** 2026-09-03 · **Status:** Accepted

**Decision.** `sections` is the parent, `chunks` the embedded child. Retrieval matches a child;
citation and display use the parent.

**Rationale.** Most corpora have to invent a parent window — N neighbouring chunks, or a
sliding page — because the document has no unit of its own. MAS numbering hands us a real one.
The clause is what the document declares, what a compliance officer cites, and what survives
re-parsing (ADR-003's point about `section_path` being a clause number and not a chunk index).
It is also, already, exactly what `get_document_section(doc_id, section_path)` returns, so the
retrieval design and the Day 1 tool surface agree by construction rather than by coincidence.

**Children exist only because embedding models have a context limit.** At 1,200 characters,
measured over the full corpus: 11,171 sections → **22,090 chunks**, 1.98 chunks per section,
median 928 characters. Most clauses are one chunk; the split is the exception.

**A repeated clause number is qualified by its enclosing header, not by a counter.** MAS Notice
129 restarts numbering at 1 inside roughly forty forms — 188 of its 221 clause paths collided
on a first pass. The first occurrence in document order keeps the bare number, so
"Notice 129, paragraph 17" still cites what a reader means by it; a repeat becomes
`Notes to Form A1/1`. That is still a citation, where `1#38` is not. Over the full corpus this
leaves **237 opaque paths of 11,171 (2.1%)**, against 85% on that document before the rule.

---

## ADR-015 — Contextual retrieval: reasoning off, per clause, outline not document
**Date:** 2026-09-03 · **Status:** Accepted

**Decision.** Each clause gets one LLM-written locator sentence, generated on `qwen3.5:9b` with
thinking disabled, from a structural outline rather than document text, and applied to every
chunk of that clause.

**Three measurements shaped this, and each overturned an assumption in the day's plan.**

**1. Reasoning has to be off — 15×.** Timed on this corpus:

| | per item | over the corpus |
|---|---|---|
| `think=True` (default) | 7.98 s | 17.9 h |
| `think=False` | 0.53 s | 71 min |

The slow call was also *worse*: thinking tokens exhausted the 120-token cap, so it returned a
truncated answer for its eight seconds. Writing a locator is the least reasoning-shaped task
imaginable. This is ADR-009 collecting.

**2. That forces the native API, and hand-written tracing.** Day 0 established that
`think: false` is not honoured on Ollama's OpenAI-compatible endpoint — neither `extra_body`
nor `reasoning_effort` reaches it. So this module posts to `/api/chat` directly and gives up
the free instrumentation `langfuse.openai` provides. The 15× is worth writing the span by hand.

**3. Concurrency is not a lever.** The plan said "start at 4, measure". Measured, on a free
GPU, over 60 items:

| concurrency | 1 | 4 | 12 |
|---|---|---|---|
| s/item | 0.65 | 0.63 | 0.62 |

5% from a 12× increase. Ollama serialises against one loaded model and a single stream already
saturates the 3090, so throughput is a property of the server's `OLLAMA_NUM_PARALLEL`, not of
the client. Raising it means restarting a shared service, which is left as a deliberate
non-change.

**The unit is the clause, not the chunk.** Anthropic's method contextualises each chunk. Here
the parent is a real unit (ADR-014), so the sentence situating chunk 2 of clause 6.14 *is* the
sentence situating clause 6.14. Generating it once per clause and applying it to that clause's
chunks costs 11,171 calls instead of 22,090 — **2.0 hours against 3.9** — for a locator that is
identical either way. The plan assumed 8,055 chunks; the real pipeline produces 2.7× that, and
this is what keeps the technique affordable at the new scale.

**The prompt carries an outline, not the document.** A 1,110-page notice cannot be situated by
stuffing it into a 9B context, and doing so would invalidate the timing above. The prompt
carries title, issuer, type, effective date, and the clause spine around the target. For legal
text that is not a compromise: a clause's position in the numbering *is* its context.

**Cost of the real prompt, re-timed before committing** (the plan required this): 281 prompt
tokens per call against ~140 in the original probe, landing at 0.63 s — under the 2 s/item
threshold at which the plan said to descope to a golden-set subset. Full scope was kept.

**Delivered:** 11,171 clauses, **0 failures**, 7,177s (2.0h) at 0.64 s/clause, 3.60M prompt and
0.45M completion tokens, applied to all 22,090 chunks. Traced to LangFuse at 1% sampling plus
every failure plus one job-summary span — verified landing in ClickHouse as 25 `locator`
generations and 1 `contextual-retrieval` span from a fully-sampled batch. Note that LangFuse
4.24 writes to its newer `events_core`/`events_full` tables; the legacy `traces`/`observations`
tables stay empty and reading them is what makes a working trace look broken.

---

## ADR-016 — Vectors live in DuckDB VSS, not in an eighth container
**Date:** 2026-09-03 · **Status:** Accepted

**Decision.** Embeddings sit in an `embeddings` table in the same DuckDB file as the clauses,
searched by an HNSW index from the `vss` extension. No Qdrant, no new service.

**Rationale.** Day 0 left this open ("Qdrant or DuckDB volume"). DuckDB 1.5.5 loads `vss` and
builds HNSW, so the whole index — documents, clauses, chunks, tables, vectors, and the BM25
index — stays one copyable file. The stack already runs seven containers; an eighth needs to
earn itself, and a single-node corpus of 22,090 vectors does not make that case. Keeping BM25
and vectors in one engine also makes Day 5's hybrid retrieval a join rather than a merge across
two systems.

**Both arms are embedded over the same chunks.** Every chunk is embedded twice, under distinct
`model` labels: `nomic-embed-text:latest` on its own text, and `…+ctx` with the locator
prepended. Day 5 sweeps contextual retrieval on against off, and that comparison is only clean
if the arms differ in *one* thing — otherwise they differ in what was chunked as well as in
what was embedded.

**Measured:** 44,180 vectors (22,090 chunks x 2 arms) embedded at 57-71 chunks/s, HNSW built
in 14.4s, whole index 433 MB. A vector query over either arm returns in 0.2-0.5s and puts
Notice 626 clause 6.14 top-1 for "what must a bank do to identify the beneficial owner of a
corporate customer".

**The file must be compacted after a re-run.** DuckDB does not return freed pages to the OS,
and both `context` and `embed` delete-then-reinsert. A second embedding pass took the index
from 651 MB to **2,926 MB holding identical data** — 4.5x for nothing. `COPY FROM DATABASE`
into a fresh file brings it to **433 MB in 57s**, carrying the HNSW *and* BM25 indexes intact
(verified by running a BM25 query against the compacted file). This ships as
`regops-ingest compact`, because a 2.9 GB artifact that should be 433 MB is the kind of thing
that is discovered much later and blamed on the wrong thing.

**The honest limit.** Single-node, no replication, one writer at a time. `vss` still flags
persistent HNSW as experimental, so the index is rebuilt rather than incrementally maintained.
If Day 12 goes multi-node or the corpus grows past a single machine, this is the decision to
revisit — and it is cheap to revisit, because nothing above the `embeddings` table knows where
the vectors live.

---

## ADR-017 — The golden set is machine-built and machine-verified, with a stated human boundary
**Date:** 2026-09-04 · **Status:** Accepted

**Decision.** `golden/v1/golden.jsonl` ships 150 items generated by `qwen3.5:9b`, verified by a
**different** model (`qwen3.8`) plus mechanical checks, and labelled `human_reviewed: false` on
every item. A confidence-ranked review queue ships beside it.

**Why a different verifier.** The prep plan says "hand-correct every one", which assumes a
human. The nearest honest substitute is not the generator checking its own work — a model
agreeing with itself is not evidence — so verification runs on a second model, and the artifact
says which model did which job in every item's `provenance` and `verification` blocks.

**A model's self-report of knowledge is worth nothing, and this was measured.** The closed-book
check exists to catch questions answerable from general knowledge, which would measure the model
rather than the retriever. Asked "do you know this requirement", `qwen3.8` answered *yes* for
**45 of 115** grounded items — and then produced generic regulatory boilerplate: "cybersecurity,
data privacy and operational resilience" where the clause says money-laundering risk. So the
self-report was discarded and replaced by a comparison between the closed-book answer and the
gold answer. Over the finished set that overlap has median **0.083** and maximum **0.455**, and
**0 items** clear the 0.45 bar. The corpus is genuinely required to answer these questions —
which is the claim a retrieval benchmark has to be able to make, and it now rests on a
measurement rather than on a model's opinion of itself.

**Nothing is filtered by retrievability.** There are two easy ways to manufacture headroom and
both produce a worse artifact than a saturated one. Discarding questions BM25 happens to answer
tunes the benchmark to embarrass a chosen baseline. Selecting gold spans from what retrieval
returned makes the ground truth a function of the system under test. So gold spans are fixed in
`select` before any retriever runs, and the saturation gate reports a number without ever
removing an item.

**Disagreement flags, it does not delete.** 28 of 150 items carry at least one failed check
(26 verifier disagreements, 17 "not answerable from this span", 1 answerable unaided). They stay
in the file, flagged, ranked, and quoted in `review_queue.md` with their gold span inline. A
clean file would have been easy to produce and would have said less: *the verifier disagreed on
26 of 150* is a quality claim, where a silently filtered file is not.

**Where the human boundary sits.** `human_reviewed: false` is asserted by a test, so a future
review pass has to flip it deliberately rather than by drift. The review queue is sorted by
ascending confidence so the prep plan's three hours land on the ~28 contested items rather than
spreading evenly over 150 of which most are fine.

---

## ADR-018 — Query-type taxonomy, and why `temporal` means stated-time here
**Date:** 2026-09-04 · **Status:** Accepted

**Decision.** Five types, with the counts declared in code (`schema.STRATIFICATION`) before
generation ran, so the mix is a decision rather than an outcome: `factual_lookup` 45,
`multi_hop` 30, `comparative` 25, `temporal` 15, `negative` 35.

**`temporal` is stated-time, not version-diff.** `regdocs-mcp` ADR-004 ships `diff_versions`
with an honest empty state because the corpus has no version pairs, and Day 4 re-confirmed it:
**0 of 463 documents have more than one version row**. Generating "what changed between v1 and
v2" questions would have required inventing the pair, which is precisely the fake that ADR
refused. What the documents *do* record was measured instead: **74 amendment-history entries
across 32 documents**, **67 `[Deleted by ...]` markers across 44**, **422 clauses stating "with
effect from"**, and effective dates spanning **1973-11-01 to 2027-01-01** including one notice
not yet in force. `temporal` items are drawn from those three sources in equal thirds. The
version-diff variant is out of scope and becomes available on the first re-fetch that finds
changed bytes.

**`multi_hop` is grounded in cross-references that actually resolve.** Two families were
measured. A guidelines document citing "paragraph X of the Notice" it annotates resolves through
20 guideline/notice pairs: **467 hops from 120 distinct source clauses**. An explicit "paragraph
X of MAS Notice NNN" resolves through a title-derived code map: **129 hops from 46 sources**.
Only pairs where **both** ends resolve to a real clause become items; an unresolvable reference
is counted and reported, because that is a finding about the corpus rather than a defect in the
set. The shipped mix leans on the first family, which is worth stating plainly.

**`negative` carries five distinct absence reasons**, not one trick repeated 35 times:
another jurisdiction, an out-of-scope instrument type (the corpus is notices and guidelines, not
Acts or Regulations), a withdrawn requirement, an invented-but-plausible specific, and a topic
MAS does not regulate. Each item records which. A negative set made of nonsense would measure
nothing, because any retriever returns nothing for nonsense; these are seeded from real corpus
topics so they read like ordinary questions.

**Negatives get the heaviest verification, because they fail worst.** A negative that turns out
to be answerable teaches the eval to reward abstention when abstention is wrong. So each one is
searched for *hard* — BM25 top-10 and dense top-10, deduplicated to 12 excerpts — and the
verifier is asked whether any of them answers it. **0 of 35 were answerable.**

---

## ADR-019 — Difficulty is engineered from entity-class near-duplication
**Date:** 2026-09-04 · **Status:** Accepted

**The problem.** Twelve questions generated from randomly sampled clauses gave **BM25 92%
recall@5 and dense 92%** — at ceiling before any hybrid, rerank or contextual variant. A sweep
over seven configurations against a set like that produces seven identical rows, and Day 5's
deliverable (*different architectures win on different query types*) becomes unreachable. The
cause is mechanical: a question generated *from* a clause reuses that clause's rare vocabulary,
so lexical search cannot lose.

**The corpus supplies the fix.** MAS issues near-identical AML/CFT notices per regulated entity
class — **25 of them here**. Against Notice 626's clause 6.14, **13 clauses from other documents
sit within cosine 0.10**, and they differ mainly in *whom they bind*. So a question about a
merchant bank ships with a dozen near-perfect distractors, and answering it needs the right
*document*, not just the right topic. Selection is therefore stratified by measured crowding —
`factual_lookup` is split 15/15/15 across isolated (0 near duplicates), moderate (1–4) and
contested (5+) — rather than sampled uniformly into the easy region.

**This is fair, not adversarial, and one rule is what makes it so.** Every question in a
contested neighbourhood **must name its entity class**. The information needed to disambiguate
is in the question; the difficulty is in using it. A question that omitted the class would have
no single right answer, and the item would be unfair rather than hard. That rule is enforced
mechanically, with the class matched on its stem — MAS writes "Banks" and a compliance officer
says "a bank".

**A shared clause number does not mean a shared topic, and assuming it did was a real defect.**
The first `comparative` pass took the same `section_path` across parallel notices. Clause 11.7
is wire-transfer originator information in Notices 824 and 1014 — and **correspondent accounts**
in Notice 626A. The generated question compared two things and one unrelated third, and the
answer was nonsense. Measured across all **196** shared paths in the family, the median maximum
pairwise cosine distance within a group is **0.330**: most shared paths are not parallel at all.
Alignment is now verified with the vectors (≤ 0.25), which leaves 73 groups — ample for 25 items,
and it moved the shipped set's worst group from 0.474 to **0.246**.

**Long boilerplate survives every other filter, so it needed its own.** Definitions, scope
paragraphs and exemption schedules are lengthy, plausible, and near-identical across notices —
and they bind nobody. Comparing two institutions on an exemption schedule yields a question whose
honest answer is "identically, it is the same boilerplate". `factual_lookup` and `comparative`
therefore draw only from clauses carrying an obligation marker (*shall*, *must*, *is required
to*), which is **5,949 of the 7,993** eligible clauses. The other three types are exempt, because
each is legitimately grounded in a clause that states no duty: an amendment endnote records
rather than binds, and a `multi_hop` item often starts from a guidelines paragraph.

**The result, measured over the shipped set** (`golden/v1/saturation.json`, hit@5 = any gold
span retrieved, full@5 = all of them):

| query type | bm25 hit@5 | dense hit@5 | bm25 full@5 | dense full@5 | n |
|---|---|---|---|---|---|
| `factual_lookup` | 0.733 | 0.733 | 0.733 | 0.733 | 45 |
| `multi_hop` | **0.800** | 0.600 | 0.167 | 0.167 | 30 |
| `comparative` | 0.560 | 0.560 | 0.160 | 0.160 | 25 |
| `temporal` | 0.400 | 0.333 | 0.400 | 0.333 | 15 |
| **overall** | **0.670** | **0.609** | **0.417** | **0.409** | 115 |

Against the naive set's 92%/92%, this has headroom on both arms, and the per-type rows already
diverge: BM25 leads `multi_hop` by 20 points, `temporal` is hardest for both, and `full@5` on the
two multi-span types sits at **0.16** — which is exactly where reranking and metadata filtering
have room to earn their place on Day 5.

**The gate reports; it never filters.** If a future version comes back saturated, the named
remedy is to *add* contested and multi-hop items. `regops-evals gate` deliberately returns 0 even
when saturated, so no build ever gets a reason to reach for the fix this ADR forbids.

---

## ADR-020 — Seven configurations as a ladder plus ablations, not as a factorial
**Date:** 2026-09-05 · **Status:** Accepted

**Context.** The prep plan names the sweep as *"dense only · BM25 only · hybrid RRF · hybrid +
cross-encoder rerank · contextual chunks on/off · parent-child on/off · query decomposition
on/off"*. Read as a factorial that is 4 × 2 × 2 × 2 = **32** configurations over 115 grounded
items — a table nobody reads, in which every cell is thin and no comparison is clean.

**Decision.** Seven rows, read as a **4-rung ladder plus 3 ablations against the top rung**:

```
C1 bm25 → C2 dense(+ctx) → C3 hybrid RRF → C4 hybrid + cross-encoder
                                              │
                    C5 contextual off · C6 parent-child off · C7 decomposition on
```

Every rung holds contextual **on** and parent-child **on**, so the ladder varies one thing:
what ranks the pool. Each ablation moves exactly one switch against C4, which is asserted by a
test (`test_each_ablation_moves_exactly_one_switch_against_c4`) rather than by intent. This is
the only reading in which an ablation means anything, because an ablation needs a fixed
reference.

**C7 reads backwards, and that is deliberate.** Decomposition is off on the whole ladder, so its
ablation turns it *on*. It is still one switch against a fixed reference, which is the property
that matters; calling it an "ablation" is a small abuse of the word and a smaller one than
inventing an eighth row.

**Every configuration is a declared object** in `regops_retrieval.configs`, not a flag
combination assembled at the call site, and the report is rendered from that list. If the
table's rows and the code's objects were not literally the same list, the table would be a claim
about code that may not exist.

**One pool for all seven.** Every configuration ranks the same 50 candidates and reports the top
20. Without that, C3 → C4 would differ in two ways at once — reranking *and* pool depth — and
the rerank column would be unreadable. It also makes a property of the design explicit rather
than surprising: **reranking a pool it does not extend cannot change recall at the pool depth**,
so C4's `hit@20` moving by zero against C3 is arithmetic, not a null result.

**Constants left untuned, and admitted as such.** RRF `k = 60` is the published default from
Cormack et al. (2009). Rerank `top_n = 50` is simply the pool. Cross-encoder pair truncation is
the model card's 512 tokens. None was fitted, because fitting a constant on the same 115 items
the table is read off is fitting noise and calling it a result. If a future day tunes them, it
needs a held-out split first.

**Where retrieval now lives.** The primitives moved out of `regops_evals.corpus` into
`regops_retrieval`; `corpus.py` imports them back under their old names, and a test asserts the
identity (`corpus.Index is regops_retrieval.index.Index`). Two reasons: an eval package must not
own the thing it evaluates, and Day 6's agent needs these retrievers without importing an eval
harness. Day 4's `gate` therefore calls the same code the sweep does, which is what makes its
published baseline comparable by construction rather than by coincidence.

---

## ADR-021 — Retrieval metrics on all seven configurations, generation metrics on four
**Date:** 2026-09-05 · **Status:** Accepted

**Context.** Measured on this box: recall, nDCG, MRR and latency for one configuration over 150
items cost **4–75 seconds**; the whole seven-configuration sweep is **8 minutes** including 165s
of one-off query decomposition. Answer generation is the other order of magnitude — the Day 5
plan budgeted **6.76s per answer** from a research probe, which put seven configurations at ~2
hours of generation before any judging.

**The estimate was wrong, and it does not change the decision.** The actual batch ran at
**~1.9s per item** — one configuration in ~5 minutes, so seven would have been ~35 minutes, not
two hours. The probe measured a cold model on its first calls; the batch amortises that. Had the
decision been made on the measured figure it would have been closer, and it would still have
gone the same way, because the binding constraint is not the clock: it is that the three
ablations answer *retrieval* questions (does contextual retrieval still pay once a cross-encoder
is present; does the assembly unit change the ranking) which the retrieval columns already
answer completely. Recording this because a plan's estimate that turns out 3.5× pessimistic is
worth catching in writing rather than quietly inheriting.

**Decision.**

- **Retrieval metrics: all 7 configurations × all 150 items.** Complete, no sampling.
- **Generation metrics: the 4 ladder rungs × all 150 items.** The ladder is where the
  architecture question lives.
- **The 3 ablations get an explicit empty cell** in the generation columns, reading *not
  measured*, with this ADR as the reason.

The alternative offered was 7 configurations × ~75 items. It was rejected because the per-type
cells are already thin — 15 `temporal` items means one item is 6.7 points — and halving the set
turns every generation cell into an anecdote. Dropping the three ablations loses the least
interesting generation comparisons; halving the set damages all of them. **An empty cell that
says why is worth more than a cell filled from a subset and quoted as though it were the set.**

**Abstention is two rates, never one.** Recall is undefined for the 35 negatives — there is no
gold span to find — and they are 23% of the set and the reason it is interesting. So abstention
is measured as a 2×2 over all 150 and reported as two numbers:

| | system answered | system abstained |
|---|---|---|
| **35 negatives** (no gold span) | **false answer** — *dangerous* | correct |
| **115 grounded** (gold span exists) | correct | **false abstention** — *useless* |

A single "abstention accuracy" would let a system that abstains constantly score well, and would
hide which of the two failures it has. In a compliance tool those failures are not
interchangeable: confidently answering a question the corpus cannot answer is the one that
causes harm, and refusing questions it can answer is the one that makes the tool unused.

**Part of the false-abstention column belongs to the golden set, and it is split out rather than
argued about.** Measured across all four ladder rungs, every one of them refuses *flagged* items
at several times the rate it refuses unflagged ones (C4: 39.3% against 12.6%), and the gap widens
as retrieval improves. Some of those items are genuinely unanswerable as written — `gs-0005` asks
*"when does this notice become effective"* with no referent for *this notice*, and abstaining is
the right answer to it. So the table publishes the rate three ways: overall, on flagged items, and
on unflagged items, and says that the unflagged column is the fairer one to quote. The split is
computed from the answers file alone, because abstention is mechanical and needs no judge.

**Groundedness is measured only where a claim was made.** An abstention has no claims to
support; counting it as grounded would reward silence, and counting it as ungrounded would
punish the correct behaviour on the negatives. So groundedness is the rate over *answered*
grounded items, and its `n` is printed next to it.

**Cost per query: measured locally, estimated for Bedrock, and labelled in the column header.**
There are no AWS credentials on this box (no `~/.aws`, no `AWS_*` in the environment), so a
measured parity number would need an account and spend today. GPU-seconds and token counts are
measured from Ollama's own `prompt_eval_duration` / `eval_duration` / token counts; the Bedrock
figure is computed from published per-token rates against those same token counts, and the words
*estimated from published rates* sit in the header rather than in a footnote, because that is
where they will be read. The estimate is linear in two named constants, so a reader with current
rates can rescale the column without re-running anything. This is consistent with ADR-005, which
positions hosted APIs as a parity baseline rather than a dependency.

**Query decomposition is evaluated on all 150 items, and reported per type.** Running it only
where it was expected to help would assume the conclusion. The expected finding — helps the
multi-span types, costs latency everywhere — is itself a routing result, and the measured one
turned out to be more interesting than that (see `results/day5/retrieval.md`).

---

## ADR-022 — Ranking was not reproducible, twice, and the first fix hid the second bug
**Date:** 2026-09-05 · **Status:** Accepted

**What happened.** Before any Day 5 measurement, six identical dense queries were issued against
the finished index and compared. They returned **six different orderings**, diverging at rank 18.
The cause: there is an exact cosine-distance tie inside the top 20, and DuckDB's parallel
aggregation does not break ties in a fixed order, so the winner of that tie depends on which
thread finished first. BM25 was stable across the same test.

**Why this was nearly invisible.** `hit@k` and `full@k` are *set* tests, and they survived it
intact — Day 4's entire published baseline is set metrics, which is why nothing had gone wrong
yet. **MRR and nDCG read the order and do not survive it.** Day 5 is the first day whose
headline claims are ranking claims, and a two-point MRR movement between two configurations is
not distinguishable from thread scheduling unless this is fixed first.

**And the first fix was not enough.** `ORDER BY score DESC, section_uid` was applied, verified
against the fixture, and shipped — and BM25 was **still** not reproducible on the real index.
Three consecutive full sweeps returned C1 MRR of 0.490, 0.495 and 0.492, for a pure-BM25
configuration over a fixed index that had no business moving at all.

The second cause is different from the first. DuckDB sums each term's BM25 contribution in a
parallel reduction; floating-point addition is not associative, so the same query returns the same
score **varying in its last bit** — `7.665345794357177` against `7.665345794357176`. A tie-break
on `section_uid` fires only on *exact* equality, and two scores differing by one ULP are not
equal, so it never ran on precisely the pairs it existed for. Measured over 40 real questions, the
top-20 reordered between runs on **10 of them**.

The fix is to round before ordering — `round(score, 9)` — which collapses the jitter into a real
tie that the uid then breaks. Nine decimal places is about six orders of magnitude above the
observed jitter and far below any score difference that means anything. Verified: 10 of 40
unstable → **0 of 40**. The same rounding goes on the dense and chunk paths, which were already
stable (`MIN` over floats is exact) but are exposed to the same class of jitter in the distance
computation itself.

**Why the test passed anyway, which is the part worth keeping.** The determinism test ran the same
query six times against a five-clause fixture with hand-written orthogonal vectors. There are no
near-ties in that fixture, so there was nothing for floating-point jitter to disturb, and the test
could not have failed however broken the ordering was. **A determinism test over clean synthetic
data proves nothing about determinism.** The suite now also carries a `slow` test that runs 20
real questions against the real index four times each and asserts one ordering — the only place
the defect can be observed.

**Decision.**

1. **A deterministic secondary sort key on every ranked query, applied to a rounded score.**
   `ORDER BY round(score, 9) DESC, section_uid` for BM25, `ORDER BY round(d, 9), c.section_uid`
   for dense, `ORDER BY round(d, 9), c.chunk_id` for the chunk variant, and an explicit uid tie-break in the RRF fusion and the reranker's sort. Ties are
   broken by something stable and arbitrary, which is the honest treatment: the tie is real, and
   pretending to order it by relevance would be worse than ordering it by name.
2. **Query embeddings computed once per run and cached** (`QuestionVectors`). They are
   bit-identical across calls, so this changes no number; it removes a confound and an Ollama
   round trip. The cache does *not* flatter the latency column — an embed it serves is added
   back at the price the first one measured, so the reported p50 is the cold path either way.
3. **Tests at both levels, because one level was not enough.** The fixture tests cover the
   tie-break logic and run in CI. `test_the_real_index_ranks_the_same_way_every_time` covers the
   float jitter, needs the real 433 MB index, and is marked `slow`.

**What this invalidated.** Every ranking metric computed against this index before the *second*
fix — the MRR and nDCG figures in the Day 5 plan's research section, **and the first two full
sweeps run on Day 5 itself**. The published table is the third sweep. The invalidated numbers were
close to the final ones (C1 MRR moved by 0.005 across the three runs, inside the noise floor the
write-up already refuses to narrate) so no conclusion changed — but that is luck, not method. The
movement was the same size as a real effect on the 15-item `temporal` cell, where one item is
0.067, and a two-point claim on that cell would have been unsupportable.

**Why this is worth an ADR.** "Our benchmark's ranking was nondeterministic" is exactly the kind
of defect that survives into a published table: it produces plausible numbers, it moves them by
about the size of a real effect, and nothing downstream can detect it. The first instance was
found by deliberately running one query six times before measuring anything. The second was found
only because three full sweeps were run and their headline numbers *compared*. **Re-running a
benchmark and diffing its output is a test, and it is one no unit suite can perform for you.**

---

## ADR-023 — `verify --no-judge` must not overwrite a judged run
**Date:** 2026-09-05 · **Status:** Accepted

**What happened.** Day 5's Phase 0 pre-flight is
`regops-evals verify --index index/regdocs.duckdb --no-judge` — a cheap check that all 150 gold
spans still bind to the index before anything is measured against them. It passed: 150 resolved,
0 moved, 0 missing. It also **rewrote `golden.jsonl` and reset all 28 flagged items to
`unverified`**, discarding the verifier's findings, its confidence ranking and the failure list
behind `review_queue.md`.

**Why it was nearly invisible.** The summary that run prints is computed from the *flag* count,
so it reported `"machine_verified": 150, "flagged": 0` and looked like a clean bill of health
rather than a data loss. The file was restored from git, and the day's headline table is computed
over a 122-item unflagged subset — which would silently have become a 150-item subset, reported
as a sensitivity run, and shown no sensitivity at all.

**Decision.** `--no-judge` now **merges** rather than rebuilds. Mechanical results (`span_exists`,
`no_leakage`) refresh; judge fields, `verifier`, `confidence` and existing flags are preserved; a
newly failing mechanical check still raises a flag. Two tests cover both directions — an existing
flag survives a `--no-judge` run, and a newly leaked question is flagged by one.

**The general rule this is an instance of.** A command whose *purpose* is to check something must
not be able to damage what it is checking. `verify` writes because the judged run genuinely
produces new state; the no-judge path produces almost none, and had no business taking the same
write path. Where a check and a mutation share an entry point, the cheap read-only mode is the
one that will be run casually — in a pre-flight, in CI, out of a plan's checklist — and it is
therefore the one that must be safe.

---

## ADR-024 — The negative set was verified through a 700-character window, and `gs-0118` is wrong because of it
**Date:** 2026-09-05 · **Status:** Accepted

**How it was found.** Day 5's generation pass measures false answers on the 35 negatives. `C4`
produced exactly one: `gs-0118`, which asks what disclosure formats or supplementary reporting
templates MAS requires. The system answered that Notice 653 prescribes the NSFR Disclosure
Template in Table 1 of Annex 1, published semi-annually in the Pillar 3 report. Every one of
those phrases is in the retrieved context. **The answer is correct and the item is wrong** — its
gold answer asserts that MAS "does not mandate specific visual disclosure formats or provide
templates", which the corpus contradicts.

**Why Day 4's verifier passed it with confidence 1.0.** Not because it failed to retrieve the
clause — it had it at rank 3 of its candidate list. `negative_excerpts` cut each candidate to
`cl.text[:700]`. Notice 653's clause is **12,689 characters**, and its disclosure-template
requirement begins at character **3,697**. The judge was asked *"does anything here answer the
question?"* and shown a window that stopped three thousand characters short of the answer. It
answered honestly about the evidence it was given.

**The general failure.** A silent truncation is a judge being lied to about its evidence. It does
not look like a bug from either side: the retrieval was right, the judge's reasoning over what it
saw was right, and the output is a confident, well-formed, wrong verdict. This is the same class
of defect ADR-022 records for ranking — a mechanism that produces plausible numbers and that
nothing downstream can detect — and it is why Day 5's own `assemble_context` records
`truncated_excerpts` and `dropped_excerpts` per query rather than silently capping.

**Decision.**

1. `NEGATIVE_EXCERPT_CHARS` is raised from 700 to **6,000**, and whatever is still cut is
   labelled inline (`[…truncated from 12,689 characters]`) so the judge knows the evidence is
   partial and can say so.
2. A test drives `negative_excerpts` with a clause longer than the window and asserts the label
   appears.
3. **`gs-0118` is not edited or deleted today.** The rule from ADR-017 stands — disagreement
   flags, it does not delete — and the flag has to come from the checker, not from a hand edit.

**What is deliberately deferred, and why.** Re-running `verify` with the wider window would
change which items are flagged, and the entire Day 5 table is keyed to the current 122/28 split:
the sensitivity run, the abstention split, every "n=" in the write-up. Re-verifying and then
re-sweeping is a Day 4 change with a Day 5 cascade, and doing it in the same commit as the
benchmark would mean publishing a table whose instrument moved underneath it. So Day 5 publishes
the defect, names the item, and quotes the affected number **both ways**: `C4`'s false-answer
rate is **1/35 = 0.029 as measured, 0/35 once `gs-0118` is excluded**. The re-verification is
first work on Day 6.

**What this does not license.** One demonstrated bad negative is not a reason to assume the other
34 are bad. It is a reason to assume the *verification* was weaker than its confidence scores
suggested — which is an argument about the checker, and it is now fixed.

---

## ADR-025 — The agent gets both tool surfaces, and the portable one's cost is a number
**Date:** 2026-09-06 · **Status:** Accepted

**Context.** The prep plan mandates a LangGraph agent consuming `regdocs-mcp`. That is the
deliverable and the portability story: any MCP host can call those four tools. But
`regdocs-mcp` has no vectors anywhere in it — `search_notices` is BM25 over section text —
because the server repo must stay a `uv sync` from green CI without a multi-gigabyte CUDA
download (ADR-001, ADR-013). Day 5 measured that arm as the **bottom rung** of its own ladder:

| | hit@5 | MRR | what it is |
|---|---|---|---|
| C1 BM25 | 0.670 | 0.486 | what `search_notices` does |
| C4 hybrid + cross-encoder | **0.835** | **0.681** | what `regops-retrieval` does |

Routing the agent through the portable tool costs **0.165 hit@5 and 0.195 MRR** against
retrieval this workspace already had, measured, on the same golden set.

**Decision.** The agent is given **both**, as two clearly-named tools with the same shape —
query in, ranked `(doc_id, section_path)` out, no full text — so the only variable between them
is the retrieval behind the call. `search_notices` is the portable surface; `search_local` is
C4. Neither repo gains a dependency it did not have: nothing is added to `regdocs-mcp`.

**Why not pick one.** Only-MCP is the cleaner story and accepts 0.195 MRR of loss silently.
Only-local abandons the deliverable the plan names and the `langchain-mcp-adapters` exercise
that motivated it. Both costs one extra tool description — 232 characters, against a
`tools/list` baseline of 8,454 bytes (ADR-005) — and converts an architectural preference into
a measurement. It also hands Day 8 two trajectories to compare rather than one.

**And the measurement did not go the way the retrieval numbers predict.** The same 30 golden
questions, the same prompt, the same validator, differing only in which arm supplied the
context:

| arm | citations resolve | cited nothing | cited something unresolvable | abstained | p50 |
|---|---|---|---|---|---|
| BM25 (`search_notices`) | **19/30** | 10 | 1 | 4 | 3.19s |
| C4 (`search_local`) | **14/30** | 15 | 1 | 3 | 3.34s |

Better retrieval produced **worse citation compliance**, and the entire difference is the model
declining to cite at all — fabrication is 1 in both arms. This is a measurement of citation
compliance, not of answer correctness: Day 5 establishes that C4 retrieves better and nothing
here contradicts it. What it says is that **citation compliance is not a retrieval property**.
Choosing the better retriever does not buy a better-grounded answer, and the fix for F2 has to
live in the prompt or the schema, not in the ranker. n=30, one model, one prompt; quoted as a
caution against the obvious inference rather than as a result about C4.

**What is deliberately not done.** F1 would be *durably* fixed by removing `issuer`, `doc_type`
and `date_from` from the tool the agent sees. That is a change to `regdocs-mcp`'s public surface
for the benefit of one consumer, and the filters are correct for every other host that might use
the server. Rejected; the prompt mitigation and its measured limits stand instead (F1).

---

## ADR-026 — Validation is three layers, and only the first is free
**Date:** 2026-09-06 · **Status:** Accepted

**Decision.** A generated answer is validated at three separate layers, each reported as its own
rate, and **no single number is quoted as "validated"**:

| layer | what it proves | cost | measured, n=30 |
|---|---|---|---|
| 1. shape | Pydantic accepts the JSON | free | **30/30** |
| 2. reference | every `(doc_id, section_path)` is in the index | one lookup | **19/30** |
| 3. support | the cited clause contains the claim | a judge | Day 5's machinery |

**Why this is not over-engineering.** "We use structured outputs" is a common answer to "how do
you know the citation is real", and the two numbers above are why it is not an answer. Ollama's
`format: <json schema>` with the full Pydantic schema produced **zero** malformed answers — the
shape problem is solved, completely, for free. It was also never the problem. 100% of answers
are schema-valid and 63% carry a citation that resolves.

**The two ways layer 2 fails are different problems and are counted separately.**

- **Omission — 10 of 11.** `sufficient: true`, `citations: []`. A list field is present and a
  list is what it contains, so nothing about the shape is wrong. A claim with no citation is
  unfalsifiable, which is the property this whole pipeline exists to prevent, so it is a failed
  validation and not a style issue.
- **Fabrication — 1 of 11.** The model writes the excerpt's *header* into the identifier field:
  `"doc_id": "[1] Notice 637 Risk Based … (d60d84ece1ddaefe:Section 1: …/1.1)"` — with the
  correct `doc_id` visible inside the string it got wrong.

The plan's research predicted fabrication as the dominant failure. It is the rarer one. Both are
caught by the same lookup, which is the argument for the layer.

**An abstention is exempt from layer 2, and that is not a loophole.** 35 of the 150 golden items
have no answer in the corpus; there is nothing to cite when the honest answer is "not here", and
requiring a citation would penalise the correct behaviour. `sufficient: false` is an explicit
field rather than a phrase to regex for, so Day 5's abstention machinery reads it directly.

**Layer 3 is deliberately not implemented today.** Reference validity is mechanical and needs no
GPU, so it runs in CI on every commit; support needs a judge, and Day 5 already has that
machinery pointed at `qwen3.8`. Building a second judge here would duplicate it. What matters is
that the three are *named separately*, so "validated" cannot silently mean "layer 1".

**The repair loop was built, measured, and turned off.** The plan called for a retry that hands
the model its own output and the specific violation, with **the repair's own success rate
measured** — because an unmeasured repair loop is just a slower way to fail. Measured: **0 of 11
repaired.** Ten changed nothing; one converted omission into fabrication at double the latency.
It is off by default and `--repair` retains it so the number can be reproduced. See F11.

**What would actually fix F2** is a schema-level constraint — a non-empty `citations` array, so
constrained decoding cannot emit `[]` — since constrained decoding is the one mechanism that has
worked perfectly here. It cannot express "unless this is an abstention", so it needs two schemas
and a routing decision. Not attempted, named so it is not mistaken for done.

---

## ADR-027 — LangGraph and Pydantic AI on the same task, and why the comparison is not a winner
**Date:** 2026-09-06 · **Status:** Accepted

**Method.** The same six golden questions, the same `qwen3.5:9b`, the same measured system
prompt, the same `Answer` schema, the same `regdocs-mcp` over stdio. A test asserts both agents
carry the identical prompt and output type, because a comparison whose arms drift measures the
drift. `regops_agents.compare`, raw rows in `results/day6/frameworks.json`.

| | LangGraph 1.2.11 | Pydantic AI 2.37.0 |
|---|---|---|
| completed | **6/6** | **1/6** |
| tool calls (6 questions) | 11 | 19 |
| tool errors | 1 | 3 |
| p50 wall-clock | **5.61s** | 27.23s |
| lines to stand the agent up | ~140 | ~25 |

**The completion columns do not measure the same thing, and the difference is the finding.**
LangGraph's 6/6 means "returned prose". Pydantic AI's 1/6 means "returned a *schema-valid*
`Answer`" — it refuses to return anything else, and five of six runs died on
`UnexpectedModelBehavior: Exceeded maximum output retries`. Reading that as "LangGraph is six
times better" would be reading a stricter bar as a worse result. The like-for-like number is
this repo's own: LangGraph plus a separate validation pass produced schema-valid output on
**30/30** and citations that resolve on **19/30** (ADR-026). Pydantic AI enforces the first
inline and, on this model, that enforcement is what fails.

**Retries were tested and are not the explanation.** `retries=1` is Pydantic AI's default and
was the first measurement. At `retries=3`: still **1/6**, with p50 27.2s → **77.2s**, and one
run newly dying on the provider's token limit because the retry loop grew the conversation past
the context window. **Tripling the retry budget bought zero additional completions and tripled
the latency.** That is the third independent measurement today of "hand it back and ask again" —
after F11's 0-of-11 hand-rolled repair loop and Pydantic AI's own internal output retry — and all
three recovered nothing.

**Where each framework is genuinely better, on evidence rather than taste.**

*Pydantic AI, on the axis the prep plan cares about most.* Its MCP support is in-tree
(`MCPToolset` + `StdioTransport`) and works against `mcp>=2.1` unchanged. LangGraph's route is
`langchain-mcp-adapters`, which **cannot talk to this server at any published version** — 0.3.1
declares `mcp>=1.24.0` with no upper bound, resolves against 2.1 and dies at import; 0.3.2 pins
`<2.0.0`, which excludes spec `2026-07-28`. That cost this repo a 60-line bridge it now maintains
(F12). On MCP, the framework the plan treats as secondary wins outright.

*Pydantic AI, on failing loudly.* Every failure above is an exception with a name. LangGraph's
`recursion_limit` raises nothing on either `stream` or `invoke`, returns a run that looks
complete, and appends *"Sorry, need more steps to process this request."* as though the model had
said it (F9, F10). For a compliance tool, an exception beats a plausible sentence.

*LangGraph, on the endpoint.* `ChatOllama` posts to Ollama's native `/api/chat` and can set
`reasoning=False`. Pydantic AI's Ollama provider speaks the OpenAI-compatible `/v1`, which
ignores it — the 15× that ADR-009 measured. **So the wall-clock column is substantially a
comparison of which endpoint each framework chose to speak, not of either one's design.** Stated
here rather than in a footnote, because 5.6s against 27.2s invites the wrong conclusion.

*LangGraph, on control.* Pydantic AI has no step ceiling: it loops until the model emits a valid
`final_result`, and one question consumed **24 tool calls** against LangGraph's one or two. A
ceiling had to be built by hand for LangGraph, but it exists and it returns a partial result;
Pydantic AI's equivalent is a retry counter on output validation, which is a different control
and does not bound tool use.

**Lines of code, reported and explicitly not treated as a quality signal.** ~25 against ~140.
Almost all of the difference is the MCP bridge LangGraph needed and the exhaustion detection
LangGraph needed — that is, LangGraph's line count is inflated by two of its own defects, which
makes the metric a restatement of the findings above rather than independent evidence.

**Recommendation, with the parts that are preference marked as such.** Keep **LangGraph** for
Days 7–8: the supervisor, the Postgres checkpointer and the human-in-the-loop interrupt are
first-class there, this codebase already carries the bridge and the ceiling, and a 5× latency
difference matters when Day 8 runs thirty tasks. Keep the **Pydantic AI** agent as a maintained
second implementation rather than a demo — it is the honest counter-example to "we chose
LangGraph", and its MCP support is the better one. *Preference, not evidence:* Pydantic AI's
declarative agent reads better and its failures are easier to diagnose; if this project were
starting today against a hosted model with a native provider, the endpoint objection would
disappear and the recommendation could go the other way.

**What this comparison cannot say.** n=6, one local 9B model, one prompt, on a machine where one
framework reaches the model through a lossier endpoint than the other. It is enough to support
the qualitative claims — MCP compatibility, failure loudness, control surfaces, retry futility —
and not enough to rank the frameworks on answer quality. The completion columns in particular
should not be quoted without the sentence explaining that they measure different bars.
