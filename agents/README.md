# regops-agents

A LangGraph ReAct agent over [`regdocs-mcp`](https://github.com/msubash26/regdocs-mcp), and the
twelve ways it fails.

The working demo is the easy half. The deliverable is
[`FAILURE_MODES.md`](../FAILURE_MODES.md): twelve failures, each with a trigger that reproduces
it, a symptom measured with an `n`, a mitigation, and what that mitigation cost.

```bash
uv run regops-agents "What must a bank do to identify the beneficial owner of a customer?"
uv run regops-agents "..." --local          # also offer search_local (C4); loads 1.33 GB
```

## The two tool surfaces

| tool | retrieval | hit@5 | MRR |
|---|---|---|---|
| `search_notices` (MCP) | BM25 over section text | 0.670 | 0.486 |
| `search_local` | hybrid RRF + `bge-reranker-v2-m3` | **0.835** | **0.681** |

The agent gets both. Routing through the portable MCP surface costs 0.165 hit@5 and 0.195 MRR
(Day 5, same golden set) — which is the price of a server that stays a `uv sync` from green CI
without CUDA, and it is a number rather than an opinion (ADR-025).

**The measurement did not go the way those numbers predict.** Over the same 30 questions,
citations resolved on 19/30 from the BM25 arm and **14/30** from C4, the whole difference being
the model declining to cite. Citation compliance is not a retrieval property.

## Why the MCP client is hand-rolled

`langchain-mcp-adapters` cannot talk to this server. 0.3.1 declares `mcp>=1.24.0` with no upper
bound, resolves against `mcp` 2.1, and dies importing a name v2 removed; 0.3.2 corrects the pin
to `<2.0.0`, which excludes a server targeting spec `2026-07-28`. So `mcp_tools.py` is 60 lines
over the SDK, and it keeps the property the adapter was wanted for: `tools/list` is read over
real JSON-RPC and each `inputSchema` reaches LangChain **verbatim**. Edit a description in the
server and the agent sees it on the next run. See F12.

## The system prompt is measured, not written

`toolcall_probe` ran 30 golden questions through two models against the server's own schemas:

| system prompt | model | added a filter | lost the gold document |
|---|---|---|---|
| bare | `qwen3.5:9b` | 5/29 | 1/29 |
| bare | `qwen3.8` | 1/29 | 0/29 |
| **steered** | `qwen3.5:9b` | **0/30** | **0/30** |

One sentence telling the model not to filter unasked buys what a 2.6× larger model buys, at half
the latency. Model size was not the binding constraint (F1).

## Three layers of validation

Shape (Pydantic) · reference (every citation resolves against the index) · support (a judge).
Measured over 30 questions: **30/30 shape, 19/30 reference**. Structured output solved the
problem that was never the problem. The repair loop fixed **0 of 11** and is off by default —
see ADR-026 and F11.

## Reproducing the measurements

```bash
uv run python -m regops_agents.toolcall_probe --system bare      # F1
uv run python -m regops_agents.toolcall_probe --system steered
uv run python -m regops_agents.measure_structured --arm bm25     # F2, ADR-026
uv run python -m regops_agents.measure_structured --arm c4       # ADR-025
uv run python -m regops_agents.provoke                           # F3, F5, F6, F7
```

Raw rows land in `results/day6/` and are committed.

## Tests

`uv run pytest agents/ -q` — 20 tests, **no model and no server**. A scripted chat model drives
the graph, so the step ceiling, the harvester and the citation resolver are all testable in CI.
The citation-resolver fixture is the actual bad output from the research run:
`{"doc_id": "[1]", "section_path": "clause 6.14 (d0000001:6.14)"}`.

Two framework behaviours are pinned by test because they are silent in production: `langgraph`
1.2.11 does not raise at `recursion_limit` (F9), and it appends *"Sorry, need more steps to
process this request."* as if the model had said it (F10).
