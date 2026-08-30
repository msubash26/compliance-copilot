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

## ADR-003 — Containers avoid host port 5432
**Date:** 2026-08-30 · **Status:** Accepted

**Context.** A host Postgres already listens on 5432.

**Decision.** All containerised Postgres is published on **5433**. Every connection string in
`.env`, compose files and the LangGraph checkpointer config uses 5433.

**Rationale.** Left on 5432, the container would either fail to bind or — worse — application
code would silently connect to the host database and write checkpoints there.

---

## ADR-004 — Separate databases for LangFuse and the LangGraph checkpointer
**Date:** 2026-08-30 · **Status:** Accepted

**Decision.** Distinct logical databases, not a shared one.

**Rationale.** The Day 7 deliverable is "a run survives a process restart and resumes".
Debugging that is far easier when checkpoint state can be dropped and inspected without
touching the trace store.

---

## ADR-005 — Local-first inference; hosted APIs only as the parity baseline
**Date:** 2026-08-30 · **Status:** Accepted

**Decision.** Ollama (already holds `qwen3.8`, `nomic-embed-text`) for iteration, vLLM for the
Day 9 serving benchmark. Hosted APIs appear only as the comparison arm.

**Rationale.** The differentiating claim is an air-gapped stack with no data leaving the
perimeter. That claim is only credible if the default path is local, including the Day 0
hello-world trace.

---

## ADR-006 — LangFuse SDK pinned to the major that matches the server
**Date:** 2026-08-30 · **Status:** Open question, revisit on B2

**Context.** The plan assumed LangFuse v2/v3. Resolution today produced SDK **4.15.1**.

**Decision.** Constraint set to `langfuse>=4,<5`. Before standing up the container, confirm the
self-hosted server major matches the SDK major and pull the official compose file from the
LangFuse repo rather than hand-writing the service graph.

**Open.** Whether the v4 self-host stack still requires ClickHouse + Redis + MinIO, and what
that costs in RAM alongside vLLM on a single box.
