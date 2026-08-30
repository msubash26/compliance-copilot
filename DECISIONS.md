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
