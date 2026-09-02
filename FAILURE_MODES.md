# Failure modes

Twelve ways this agent fails, each with a trigger that reproduces it, a symptom measured with
an `n`, the mitigation applied, and **what that mitigation cost**. A failure with no
reproduction is a story; a mitigation with no cost is a sales pitch.

Everything below was measured on 2026-09-06 against the real 433 MB index, the real
`regdocs-mcp` server over stdio, and the 150-item golden set. The sample where one is used is
30 grounded questions drawn deterministically from the golden set — 12 `factual_lookup`, 8
`multi_hop`, 6 `comparative`, 4 `temporal` — declared in `toolcall_probe.SAMPLE` so a re-run is
the same run. Model: `qwen3.5:9b` at temperature 0. Raw rows: [`results/day6/`](results/day6/).

**Four of these are the framework's, not the model's** (F9–F12). That split is worth keeping in
view: a lot of writing about agent failure assumes the model is the unreliable part.

| | failure | where it lives | still open? |
|---|---|---|---|
| F1 | Invented tool arguments narrow the search past the answer | model | mitigated |
| F2 | A schema-valid answer cites something that does not exist — or nothing | model | **open** |
| F3 | Over-long prompts are truncated from the front, silently | runtime | mitigated |
| F4 | Tool-call loops: the same search, permuted, until the budget goes | model | bounded |
| F5 | A tool error is delivered, and its recovery path is ignored | model | **open** |
| F6 | Oversized tool results exhaust the step budget | tool surface | mitigated |
| F7 | The right tool, called with an invented identifier | model | **open** |
| F8 | The same query returned a different ranking each run | tool | **fixed** |
| F9 | The step ceiling neither raises nor reports | framework | mitigated |
| F10 | The framework substitutes its own answer at that ceiling | framework | mitigated |
| F11 | The repair loop fixes nothing, and converts one failure into another | design | **removed** |
| F12 | The MCP adapter cannot talk to a spec-current MCP server | framework | worked around |

---

## F1 — Invented tool arguments narrow the search past the answer

**Trigger.** `uv run python -m regops_agents.toolcall_probe --system bare`. Give the model the
four tool schemas exactly as `tools/list` publishes them and one golden question. Nothing else.

**Symptom.** `search_notices` advertises three filters — `issuer`, `doc_type`, `date_from` — and
the model reaches for them unbidden. Over 30 questions:

| system prompt | model | emitted a call | added a filter | **filter excluded the gold document** |
|---|---|---|---|---|
| bare | `qwen3.5:9b` | 29/30 | 5/29 | **1/29** |
| bare | `qwen3.8` | 29/30 | 1/29 | 0/29 |
| steered | `qwen3.5:9b` | 30/30 | **0/30** | **0/30** |
| steered | `qwen3.8` | 29/30 | 0/29 | 0/29 |

The single loss is `gs-0012`: the model filtered to `doc_type: notices` and the gold clause is
in a guideline. The filter is applied by the index as an equality predicate, so the answer is
not ranked low — it is *absent*, and nothing in the result says a filter removed it.

**Mitigation.** One sentence in the system prompt: *"Do not set issuer, doc_type or date_from
unless the user's question names one explicitly — a wrong filter silently removes the answer
from the results, and you will not be told that it did."* Measured above: 5 filters → 0, one
lost document → none.

**Cost.** Two things, and the second is the real one.

1. **It suppresses a capability, not just a mistake.** This corpus is MAS-only and every
   document is a notice or a guideline, so no filter here is ever *needed*. On a multi-issuer
   corpus the same sentence would suppress a genuinely useful narrowing, and the mitigation
   would have to become "filter only on terms the question names" — which is what it says, but
   enforcing it needs a check the prompt cannot provide.
2. **It is a prompt, so it is not a guarantee.** 0 of 30 is not 0 of ∞. The durable fix is to
   remove the filters from the tool the agent sees, which is a change to `regdocs-mcp`'s public
   surface for the benefit of one consumer — rejected for now, and named in ADR-025.

**A finding worth more than the mitigation.** The plan expected model size to be the lever here
and pre-committed to measuring `qwen3.8` on tool-call accuracy. It measured: **one sentence of
prompt buys what a 2.6× larger model buys**, at half the latency and 6.6 GB against 17 GB. The
model-size question was not the binding constraint. Day 6's research pass recorded 9/29 losing
the gold document on `qwen3.5:9b`; that did not reproduce here (1/29) and the earlier sample and
prompt cannot be reconstructed, so this table is what is quoted.

---

## F2 — A schema-valid answer cites something that does not exist, or cites nothing

**Trigger.** `uv run python -m regops_agents.measure_structured --arm bm25`. Answer 30 golden
questions with Ollama's `format: <json schema>` and a Pydantic `Answer` model, over real
retrieved context, then check every `(doc_id, section_path)` against the index.

**Symptom.**

| layer | what it proves | result |
|---|---|---|
| 1. shape | Pydantic accepts the JSON | **30/30** |
| 2. reference | every citation resolves against the index | **19/30** |

**Structured output solved the shape problem completely and the reference problem not at all.**
Constrained decoding against the full JSON Schema produced zero malformed answers, which makes
schema validity free — and free is also uninformative. 100% shape-valid, 63% reference-valid.

The 11 failures are two different problems:

- **10 of 11 cite nothing at all.** `sufficient: true`, `citations: []`. Schema-valid: the field
  exists, and an empty list is a list. A claim with no citation is unfalsifiable, which is the
  exact property this pipeline exists to prevent.
- **1 of 11 cites an identifier that does not exist.** The model pastes the *excerpt header* into
  the field instead of the identifier inside it:
  `{"doc_id": "[1] Notice 637 Risk Based Capital … (d60d84ece1ddaefe:Section 1: …/1.1)"}` — with
  the real `doc_id` visible inside the string it got wrong.

**Mitigation.** Layer 2 itself: every citation is resolved against the index before the answer is
returned, and an unresolvable one is a *failed validation*, not a cosmetic issue. An answer
claiming sufficiency with no citation fails too.

**Cost.** One index lookup per citation — negligible — and the honest part: **layer 2 detects,
it does not fix.** 11 of 30 answers are now correctly marked invalid rather than silently wrong,
and the system has no valid answer for those 11. That is the right trade for a compliance tool
and it is a real reduction in coverage.

**Not reproduced.** The plan's research 2 measured 18/20 schema-valid and 12/20 resolvable, and
predicted fabricated citations as the dominant failure. Shape validity is better here (30/30) and
the dominant failure is *omission*, not fabrication. The layered argument survives either way —
it is strengthened, since the gap between layers 1 and 2 is wider than predicted.

---

## F3 — Over-long prompts are truncated from the front, silently

**Trigger.** `uv run python -m regops_agents.provoke --only f3_context_overflow`. Put a fact that
cannot be inferred at the very start of an ~8,000-token prompt, set `num_ctx` below the prompt
length, and ask for the fact back.

**Symptom.**

| `num_ctx` | prompt tokens actually evaluated | needle survived | error raised |
|---|---|---|---|
| 2048 | 1,026 | **no** | **no** |
| 4096 | 2,050 | **no** | **no** |
| 16384 | 7,366 | yes | no |

At 2048 the model replied fluently that there was no such code in the text. Nothing raised,
nothing warned, and the reply is indistinguishable from a correct negative answer.

**The dangerous part is the direction.** Truncation is from the *front*. In an agent the front of
the prompt is the system prompt and the user's question, so an over-long tool result does not
crowd out the tool result — it crowds out the instructions saying what to do with it, and F1's
mitigation is the first thing to go.

**Mitigation.** Two, neither of them "set a bigger window". Tool results are bounded at 12,000
characters by the bridge and the truncation **says so in the text the model reads**
(`mcp_tools.MAX_RESULT_CHARS`). And `num_ctx` is left at the server default in normal operation —
it is a parameter on `build_agent` purely so this failure can be provoked.

**Cost.** A bounded tool result is an incomplete one, and the agent has to page to see the rest —
which is F6. The default window is 262,144 tokens on this model, so the bound costs nothing here
and would cost more on a model with a small window.

---

## F4 — Tool-call loops: the same search, permuted, until the budget goes

**Trigger.** Ask for something the tool cannot return.
`uv run regops-agents "When did MAS Notice 626 take effect?"`

**Symptom.** Four searches, each a permutation of the last, then a give-up:

```
1. search_notices({"query": "MAS Notice 626 effective date"})       -> 6,176ch
2. search_notices({"query": "MAS Notice 626"})                      -> 6,215ch
3. search_notices({"query": "Notice 626 effective date take effect"}) -> 5,184ch
4. search_notices({"query": "Notice 626 dated"})                    -> 6,189ch
```

`effective_date` is document **metadata**, not clause text, and `search_notices` is BM25 over
section text — so no permutation of that query can succeed. The agent has no way to learn this
and re-phrases instead. The F7 run produced the same shape: **6 searches, 5 of them distinct**,
into the step ceiling.

**Mitigation.** A hard step ceiling (12 graph steps ≈ 6 tool calls) and a hard wall clock (180s),
both returning a partial `Run` rather than raising — see F9 for why that had to be built by hand.
`Run.stopped_by` names which fired, and `Run.tool_calls` keeps the work done before the stop.

**Cost.** A ceiling cannot distinguish a loop from a hard question. A genuinely multi-hop question
needing seven tool calls is cut at six and returns a partial answer that a careless caller could
read as a complete one — which is why every partial run is marked in the answer text itself.
Tuning the ceiling upward trades that against paying for more loops.

---

## F5 — A tool error is delivered, and its recovery path is ignored

**Trigger.** `uv run python -m regops_agents.provoke --only f5_tool_error`. Insist on a `doc_id`
that does not exist: *"Read clause 6.14 of document zzzzzzzzzzzzzzzz … That document id is
correct; use it."*

**Symptom.** The server raises `ToolError` and the message reaches the model intact, carrying the
recovery path ADR-005 rule 3 requires:

```
TOOL ERROR from get_document_section: no document 'zzzzzzzzzzzzzzzz'.
Use search_notices to obtain a valid doc_id.
```

The model did **not** fabricate a clause — the failure the prep plan predicts — and it did **not**
take the offered recovery either. It stopped and asked the user for a valid id.
`recovered_with_search: false`, 1 error seen, 4 steps.

**Assessment: milder than predicted, and still a failure.** Refusing safely is much better than
inventing a clause. But a tool that goes to the trouble of naming its own recovery path and is
then ignored means that design effort bought nothing here, and a one-shot question ends in a
question back to the user rather than an answer.

**Mitigation.** Partial: errors are surfaced rather than swallowed — `_harvest` marks each tool
call's `error` flag, so a run that answered *around* an error is visible in the trace instead of
looking clean. **Not fixed:** making the model act on the recovery path needs it in the system
prompt, which is untested and would be another unmeasured prompt claim.

**Cost of what was applied.** None; it is bookkeeping. The cost of the *unapplied* fix is another
sentence of prompt competing with F1's for the model's attention — and F1's sentence is measured,
so it is not being diluted before this one is.

---

## F6 — Oversized tool results exhaust the step budget

**Trigger.** `uv run python -m regops_agents.provoke --only f6_pagination`. Ask for a complete
list: *"List every obligation in MAS Notice 637 … the complete list, not a sample."*

**Symptom.** Seven tool calls, five of them escalating searches, then two `list_obligations`
calls — and then the ceiling:

```
search_notices(top_k=5)   -> 3,127ch     list_obligations(...)                 -> 12,098ch
search_notices(top_k=10)  -> 6,128ch     list_obligations(..., cursor="bzo1")  -> 12,098ch
search_notices(top_k=10)  -> 6,417ch
search_notices(top_k=20)  -> 12,098ch    stopped_by: step_ceiling at 16 steps
search_notices(top_k=20)  -> 12,098ch
```

**The predicted failure did not occur and a worse one did.** The prediction was that the agent
would answer from page one and call it complete. It did not — `used_a_cursor: true`, it paged
correctly. What defeated it was volume: `list_obligations` on Notice 637 is 59,307 characters for
one page and 2,219,320 unpaginated, so every call returns the bridge's 12,000-character cap, and
seven of them is ~84,000 characters of history. The agent ran out of *steps* while doing exactly
the right thing.

**Mitigation.** The 12,000-character cap, which is what stands between this and F3 — without it,
two `list_obligations` pages would have pushed the system prompt out of the window. Pagination
itself is the tool surface working as designed (ADR-005 rule 2): the difference between one page
and none is 15,000 tokens against 555,000.

**Cost.** The agent cannot answer "list everything" for a large document within its budget, and
returns a marked partial. That is the honest outcome for a question whose complete answer is half
a million tokens, but it is a capability gap and not a solved problem: the real fix is a tool
that *aggregates* rather than paginates, which does not exist yet.

---

## F7 — The right tool, called with an invented identifier

**Trigger.** `uv run python -m regops_agents.provoke --only f7_wrong_tool`. Ask a version
question: *"What changed between the versions of MAS Notice 626, and when did each take effect?"*

**Symptom.** The prediction was that the agent would never reach for `diff_versions`. It did —
and called it with `doc_id: "MAS-N-626"`, an identifier of a shape this corpus does not use:

```
Tool 'diff_versions' failed: no document 'MAS-N-626'. Use search_notices to obtain a valid doc_id.
```

Then six searches, five distinct, into the step ceiling.

**This is F1 again, from the other end.** Tool *selection* was correct; argument selection was
not. Taken with F1 and F5, the pattern across every failure the model owns is the same: it knows
which tool it wants and invents what to pass it. That is the sentence worth carrying into Day 7 —
routing is not the hard part.

**Mitigation.** None applied. `diff_versions` already returns the valid versions on record when
given a bad id, which is the best a tool can do unilaterally. Making the agent look the id up
first is a plan-step constraint, and that is Day 7's supervisor, not a prompt patch here.

**Cost.** Of doing nothing: this class of question fails, visibly, at the step ceiling. Given
ADR-004 (`regdocs-mcp`) records that this corpus has no genuine multi-version document, the
question has no good answer anyway — which is a reason to leave it failing loudly rather than to
paper over it.

---

## F8 — The same query returned a different ranking each run · **fixed**

**Trigger.** Run one BM25 query against a fixed index four times and compare the top-20. Over 40
golden questions: `uv run pytest tests/test_determinism.py` in `regdocs-mcp` with
`$REGDOCS_INDEX` set.

**Symptom.** **9 of 40 questions returned a different top-20 between runs.** `search_notices` has
ordered by `score DESC, effective_date DESC NULLS LAST, doc_id, ordinal` since Day 1 — three
deterministic tie-breaks that never ran, because they compare for *exact* equality and DuckDB
sums BM25 term contributions in a parallel reduction. Float addition is not associative, so two
clauses whose true scores are equal come back differing in the last bit.

**Mitigation.** `ORDER BY round(score, 9) DESC, …`. Rounding turns the jitter into a real tie the
existing columns can break. **9 of 40 → 0 of 40.** `regdocs-mcp` ADR-008, ported from this repo's
ADR-022.

**Cost.** Two clauses whose scores differ below 1e-9 are now ordered by `doc_id` rather than by
score. At BM25 magnitudes that difference is noise, and a deterministic order is worth more than
a meaningless one.

**Kept here although it is fixed**, because it is the entry that shows this document is a log of
things found and closed rather than a list of complaints — and because a tool whose output is not
a function of its input cannot be cached and cannot be diffed between agent runs, which is
exactly what Day 8's trajectory comparison intends to do.

---

## F9 — The step ceiling neither raises nor reports

**Trigger.** Drive a `create_react_agent` with a model that always emits a tool call, set
`recursion_limit=6`, and iterate. `uv run pytest agents/tests/test_agent.py -k ceiling`.

**Symptom.** Nothing is raised. Not on `stream`, not on `invoke`. The run stops and returns
normally, with the last message an `AIMessage` whose tool calls were never answered:

```
stream lim=4: ended normally, 4 chunks    invoke lim=6: ended normally, 6 msgs
stream lim=6: ended normally, 6 chunks
stream lim=10: ended normally, 10 chunks
```

`GraphRecursionError` exists, is what older versions raised, and is what the documentation points
at. An agent that catches it — the obvious implementation — **reports an exhausted run as a
completed one**, and its caller cannot tell a finished answer from a truncated one.

**Mitigation.** Detect exhaustion structurally, from the message state, with two independent
signals: the step count reached the limit, or the last message is an `AIMessage` with unanswered
tool calls (`agent._exhausted`). The `GraphRecursionError` handler is kept for versions that
raise.

**Cost.** A structural check is version-coupled in a different way — it depends on ReAct's message
shape rather than on an exception name. `test_a_step_ceiling_returns_a_partial_run_rather_than_raising`
pins it, so a framework upgrade that changes either behaviour fails a test here instead of
silently mislabelling runs. Measured on `langgraph` 1.2.11.

---

## F10 — The framework substitutes its own answer at that ceiling

**Trigger.** As F9, then read `run.answer`.

**Symptom.** At the recursion limit LangGraph appends an `AIMessage` of its own:

> Sorry, need more steps to process this request.

Fluent, plausible, first-person, and **indistinguishable from a model that considered the
question and declined**. Combined with F9 — nothing raised — a caller reading the last message
records the framework's budget exhaustion as the agent's considered judgement. On a compliance
tool that is an abstention that never happened.

**Mitigation.** Every partial run is prefixed with what actually happened, and the framework's
text is kept rather than hidden:

```
[stopped by step_ceiling after 16 steps, 14.9s, 7 tool call(s)] Sorry, need more steps to process this request.
```

**Cost.** The marker is in the answer string, so a downstream consumer that expects clean prose
gets a prefix it has to strip. That is deliberate: making it easy to ignore is how it would come
to be ignored. `Run.stopped_by` carries the same fact structurally for consumers that want it
clean.

---

## F11 — The repair loop fixes nothing, and converts one failure into another · **removed**

**Trigger.** `uv run python -m regops_agents.measure_structured --repair`. On any validation
failure, hand the model its own output plus the specific violation and retry once.

**Symptom.** **0 of 11 repaired.** Not "helped a little" — zero.

| | |
|---|---|
| repairs attempted | 11 |
| repairs that fixed the failure | **0** |
| repairs that changed nothing at all | **10** |
| repairs that changed the failure into the *other* failure | 1 |

The eleventh is the instructive one. Attempt 1 cited nothing. Told so, attempt 2 obediently cited
— and pasted the entire excerpt header into `doc_id`. The repair prompt succeeded at making the
model cite and failed at making it cite correctly, trading F2's omission failure for F2's
fabrication failure at double the latency.

**Mitigation.** The loop is **off by default** (`answer_once(..., repair=False)`); `--repair`
retains it so the measurement can be repeated. An unmeasured repair loop is just a slower way to
fail, and this one is measured.

**Cost of removing it.** None detectable: it fixed nothing. The cost of *keeping* it was p50
3.19s → roughly double on the 11 affected items, for zero recovered answers. What would be worth
trying is a schema-level constraint — requiring a non-empty `citations` array so constrained
decoding cannot emit `[]` — which is a real fix rather than a retry, and cannot express "unless
the answer is an abstention". Not attempted; named here so it is not mistaken for done.

---

## F12 — The MCP adapter cannot talk to a spec-current MCP server

**Trigger.** `uv add langchain-mcp-adapters` in a workspace whose server pins `mcp>=2.1,<3`, then
`from langchain_mcp_adapters.client import MultiServerMCPClient`.

**Symptom.**

```
ImportError: cannot import name 'RequestContext' from 'mcp.shared.context'
```

```
langchain-mcp-adapters 0.3.1  requires  mcp>=1.24.0       (no upper bound)
langchain-mcp-adapters 0.3.2  requires  mcp>=1.24.0,<2    (the latest release)
regdocs-mcp                   requires  mcp>=2.1,<3       (spec 2026-07-28)
```

0.3.1's bound is not permissive, it is **wrong**: it resolves against `mcp` 2.1 and dies at import
on a name v2 removed. 0.3.2 corrects the pin, and the corrected pin excludes this server. There is
no version of the adapter that works. **The adapter ecosystem is a major version behind the
protocol.**

**Mitigation.** `regops_agents.mcp_tools` — 60 lines over the MCP SDK directly, which was the
plan's stated fallback. It keeps the property the adapter was wanted for: `tools/list` is read
over real JSON-RPC and each `inputSchema` is handed to LangChain **verbatim**, so a description
edited in `regdocs_mcp.server` reaches the agent on the next run with nothing here to update.

**Cost.** Code this repo now owns and must maintain against two moving APIs instead of one — and
losing whatever the adapter does that this does not (its callback plumbing, multi-server routing).
The alternative was downgrading the SDK, which would abandon spec revision `2026-07-28`, break the
server's own pin, and give up the transport work Day 2 exists for. **Do not take a framework's
integration package as evidence the integration is available**: check its constraints against your
own pins before designing around it.

---

## What this list says, taken together

**The model's failures are all one failure.** F1 (invented filters), F5 (ignored recovery path)
and F7 (invented `doc_id`) are the same defect seen three times: the model picks the right tool
and is careless about what it passes. Tool *selection* was correct in every single provocation.
Routing is not the hard part — argument grounding is.

**Four of twelve belong to the framework, and those are the quiet ones.** F9, F10 and F12 produce
no error at all; F9 and F10 actively produce output that looks like success. The model's failures
are loud by comparison — a wrong filter still returns results you can inspect, a loop is visible
in the trace. It is the infrastructure that lies quietly.

**Two mitigations that sound responsible are worth nothing here.** Structured output (F2) is 100%
effective at the layer that was never the problem, and the repair loop (F11) recovered zero of
eleven. Both are standard recommendations. Both were measured rather than assumed, and only the
measurement distinguishes them from the one-sentence prompt change in F1 that actually worked.
