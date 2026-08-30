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
