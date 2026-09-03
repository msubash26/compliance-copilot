# `golden/tasks/v1` — thirty end-to-end agent tasks

Thirty tasks with machine-checkable expectations, used by `regops-evals agent-eval`
to measure the single agent, the supervisor and plan-and-execute on the same work.

**Derived, not written.** Every task carries the `golden_id` it came from, and
nothing about it is invented: the question is the golden question verbatim,
`gold_doc_ids` come out of `gold_spans`, and `must_abstain` is
`query_type == "negative"`. A hand-written task file would be a second ground
truth to maintain, and the two would drift — `golden/v1` is re-verified against
`span_sha256` on every re-parse and a copied question is not. So a change to
`golden/v1` shows up here as a **failing test** rather than as silent drift, and
`evals/tests/test_tasks.py::test_the_committed_file_is_what_the_builder_produces`
means a hand-edit to this file fails the build too.

Regenerate with:

```
uv run regops-evals build-tasks --golden golden/v1/golden.jsonl
```

## The mix

| query type | tasks | of 150 golden | distinct gold documents | `min_tool_calls` |
|---|---|---|---|---|
| `factual_lookup` | 12 | 45 | 1 | 2 |
| `multi_hop` | 6 | 30 | 2 | 3 |
| `comparative` | 4 | 25 | 2 or 3 | 3 or 4 |
| `temporal` | 3 | 15 | 1 | 2 |
| `negative` | 5 | 35 | 0 | 1 |

Proportional to the golden strata, declared in `tasks.TASK_STRATIFICATION` before
anything was selected, so the mix is a decision rather than an outcome.

## Fields

| field | where it comes from |
|---|---|
| `golden_id` | the item this task is derived from — the staleness link |
| `question` | that item's question, verbatim |
| `gold_doc_ids`, `gold_uids` | its `gold_spans` |
| `must_cite` | true iff the item has gold spans |
| `must_abstain` | true iff `query_type == "negative"` |
| `min_tool_calls` | `1 + len(gold_doc_ids)` — one search, one read per gold document |
| `absence_reason` | for negatives, which of the five reasons it is unanswerable |

`min_tool_calls` is a **floor**, not a target. An agent that searches twice
because the first query missed is doing legitimate work; the metric reports the
raw pair beside the ratio so that a 0.5 from two calls instead of one is
distinguishable from a 0.5 from twelve instead of six.

## Selection

Deterministic, no RNG: lowest golden id first, `machine_verified` only. 28 of the
150 golden items carry a failed verification check, and an eval that gates a build
should not be gated by an item the set itself flags as doubtful.

The five negatives are stratified across all five `absence_reason` values — one
each — because a negative set that is five variations of one trick measures one
trick (ADR-018).

## What is not here

- **No version task.** `diff_versions` is unreachable from the supervisor by
  design (ADR-028 forbids model-supplied identifiers), and `regdocs-mcp` ADR-004
  records that this corpus holds no genuine multi-version document. A task nothing
  can pass measures the task set, not the agent.
- **No coverage tasks.** Day 7's three ("which documents address X, and which are
  silent") live in `tasks.COVERAGE_TASKS` because their expectations are
  hand-written rather than derived. They are run and reported, never gated, and
  keeping them out of this file is how the distinction stays visible.
- **No human review.** Like every item in `golden/v1`, these inherit
  `verification.human_reviewed: false`. See `golden/judge_calibration/` for the one
  place in this project where a human score exists, and for the boundary around it.
