# Tracing the agents with LangFuse

Day 0 stood the stack up. Days 6 and 7 never wired it in, and Day 7's close-out
recorded that as *genuinely undone rather than half-done*. This is what closes it.

```bash
uv run regops-evals agent-eval --trace          # opt-in, and non-fatal
```

Open <http://localhost:3000> and pick a trace. One trace per task, named
`<arm> · <task_id>` — so a LangFuse trace and a row of `results/day8/eval.json`
are the same unit. Anything coarser makes *"which task was slow"* a question you
answer by counting spans.

## What the tree looks like

| level | `as_type` | name |
|---|---|---|
| the task | `span` | `supervisor · t-901` |
| a graph node | `span` | `router`, `retrieve`, `extract`, `check`, `fan_out`, `inspect`, `synthesise` |
| a model call | `generation` | `llm:route`, `llm:extract`, `llm:inspect`, `llm:synthesise` |
| an MCP call | `tool` | `search_notices`, `get_document_section`, `list_obligations` |

The `llm:` prefix exists because a node span and the generation inside it would
otherwise both be called `extract`, which is legible in a tree and useless in a
list.

Generations carry `usage_details` from Ollama's `prompt_eval_count` and
`eval_count`, so token cost is attributable per worker rather than per run.

**The picture worth opening.** A coverage task (`t-901`–`t-903`) puts the
fan-out's four `inspect` branches under `fan_out` as **siblings**. In
[`trace-fanout.txt`](trace-fanout.txt) all four start at the same instant and
finish at **5.98s, 8.32s, 10.52s and 13.08s** — a staircase with a tread of about
2.4 seconds, which is roughly what one branch costs to compute. They are running
concurrently and being *served* one at a time. Every tool call inside them is
0.01–0.10s.

That is Day 7's 1.00× against a 3.12× ceiling, shown rather than argued. The
branches are not competing for the orchestrator; they are queueing at one model
server, and adding concurrency in front of a queue does not shorten it. The
staircase is what makes it legible: a fan-out that was genuinely parallel would
show four bars of equal length ending together.

## Three things about v4 that cost time

**1. The span API was renamed.** `start_as_current_span` and
`start_as_current_generation` — which most published examples still show — do not
exist on `langfuse` 4.15.1. There is one entry point:

```python
client.start_as_current_observation(name=..., as_type="span" | "generation" | "tool")
```

The failure is an `AttributeError` at runtime, a long way from the cause.

**2. This deployment is write-only.** It runs in v4 `events_only` mode:

| endpoint | |
|---|---|
| `/api/public/health`, `/api/public/projects` | 200 |
| `/api/public/traces`, `/observations`, `/scores` | **404** — *"not available on deployments running in Langfuse v4 events_only mode"* |

Ingestion works fine; there is simply no read API. **So LangFuse is not the
measurement store.** Scores pushed to it cannot be read back, and the Day 8 gate
reads a committed artifact instead. That is the right architecture regardless — a
gate that reads a mutable store is not reproducible — but here it is a measured
constraint rather than a preference.

**3. Traces land in `events_core`, not `traces`.** The legacy `traces` and
`observations` tables stay empty in this mode, which looks exactly like ingestion
failing. To check that spans arrived:

```bash
CH_PW=$(grep '^CLICKHOUSE_PASSWORD=' .env | cut -d= -f2-)
curl -s http://localhost:8123/ -u "clickhouse:$CH_PW" \
  --data "SELECT name, type, count() FROM events_core \
          WHERE start_time > now() - INTERVAL 1 HOUR GROUP BY name, type FORMAT TSV"
```

## Rendering a waterfall without the UI

Because there is no read API, the committed span tree in
[`trace-fanout.txt`](trace-fanout.txt) is read straight out of ClickHouse:

```bash
uv run python -m regops_evals.tracetree --name 'supervisor · t-9%' --out docs/trace-fanout.txt
```

It is a diagnostic, not a replacement for the dashboard — it proves ingestion
worked and shows the tree's shape. **The screenshot in this directory is a manual
step**: the UI is the thing a person actually looks at, and nothing in this repo
can drive a browser.

## Tracing never takes a run down

`--trace` is opt-in and every call is wrapped. No `LANGFUSE_PUBLIC_KEY`, a failed
`auth_check`, an unreachable host — each degrades the run to untraced and says so
once, on stdout, before any work starts. An eval harness that cannot run when the
observability stack is down has made observability a prerequisite for knowing
whether the system works, which is backwards.

Measured overhead when it is on: **0.8 ms** for a span with three nested
generations, against runs of five to sixty seconds.
