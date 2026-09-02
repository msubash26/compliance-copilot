# Day 6 — A single agent, and the failure modes it actually has

**Repo:** `compliance-copilot` (member `regops-agents`) + one cross-repo fix in `regdocs-mcp`
**Date:** 2026-09-06 · **Budget:** ~6.5h

> The prep plan's bar: *"`FAILURE_MODES.md` has 8+ documented failures with the mitigation you
> applied to each. Interviewers love this document. Nobody else brings one."*

---

## Context

Day 5 produced a measured retriever and a reproducible harness. Day 6 puts a model in front of it
and finds out what breaks. The deliverable is **not** a working demo — a working demo is the easy
half and every candidate has one. It is a document of failures, each with a trigger that
reproduces it, a symptom that was measured, and a mitigation whose cost is stated.

### Carried forward from Days 1–5

- **Two debts fall due today**, both named in Day 5's close-out. Re-verifying the golden set with
  the wider excerpt window (ADR-024) has to happen before any agent eval quotes a flag count, and
  it moves the 122/28 split. It is Phase 1, not a footnote.
- **`regops-retrieval` exists and is measured.** C4 (hybrid RRF + `bge-reranker-v2-m3`) is the best
  configuration at hit@5 0.835 / MRR 0.681, and its arms are importable objects rather than a
  benchmark's internals — which was the point of moving them out of `regops_evals` (ADR-020).
- **The golden set is the eval substrate again**, but Day 6 uses it differently: Day 5 asked *did
  the right clause come back*, Day 6 asks *did the agent call the right tool with the right
  arguments and cite something that exists*.
- **Ollama serialises.** Third day running this has forced a redesign. An agent loop that
  interleaves a generator and an embedder pays a 17.7 GB swap per step.
- **`qwen3.5:9b` generates at ~1.9s per answer** over five assembled clauses (Day 5, measured).
  An agent that takes six steps to answer is a twelve-second answer before any tool latency.

### Research completed before planning (ADR-002's rule)

Everything below was measured today, against the real index, the real MCP server and the real
golden set.

**1. The model calls tools, and it invents arguments that lose the answer.** 30 grounded golden
questions, `qwen3.5:9b` at temperature 0, given the four `regdocs-mcp` tool schemas verbatim:

| | |
|---|---|
| emitted a tool call | **29 / 30** |
| added a filter nobody asked for (`doc_type`, `issuer`, `date_from`) | **16 / 29** |
| …and that filter **excludes the gold document** | **9 / 29 (31%)** |
| set `top_k` below 5 | 0 / 29 |
| latency of the tool-call decision | p50 0.8s, max 8.4s |

Tool-calling works. What fails is *argument selection*: the description advertises three filters,
and the model reaches for them unprompted. Nearly a third of the time it filters to `guidelines`
when the obligation is in a notice. This is the prep plan's "hallucinated arguments", and it is
not an edge case on this corpus — it is the single largest source of lost answers before the
retriever is even consulted.

**2. Structured output validates shape, not reference.** Ollama's `format: <json schema>` with a
Pydantic model, over real BM25 context, 20 grounded questions:

| | |
|---|---|
| schema-valid (Pydantic accepted it) | **18 / 20** |
| every cited `(doc_id, section_path)` resolves against the index | **12 / 20** |

**6 of the 18 validated answers carry a citation that does not exist.** A representative one:
`{"doc_id": "[1]", "section_path": "clause 6.14 (d0000001:6.14)"}` — the model filled the fields
with the *excerpt label* rather than the identifiers sitting in the excerpt header. Pydantic is
satisfied; a compliance officer following the citation is not. **Schema validation is necessary
and nowhere near sufficient**, and "we use structured outputs" is not the answer to "how do you
know the citation is real".

**3. The agent's tool surface is Day 5's *worst* configuration.** `regdocs-mcp` has no vectors
anywhere in it — `search_notices` is BM25 over section text and nothing else. Day 5 measured that
arm:

| | hit@5 | MRR | what it is |
|---|---|---|---|
| C1 BM25 | 0.670 | 0.486 | **what the MCP tool does** |
| C4 hybrid + cross-encoder | **0.835** | **0.681** | what `regops-retrieval` does |

Routing the agent through the portable tool costs **−0.165 hit@5 and −0.195 MRR** against the
retrieval this project already built and measured. That is not a bug in the server — it is what
keeps it a `uv sync` from green CI without a multi-GB CUDA download (ADR-001, ADR-013). But it is
a tradeoff that has to be *measured and stated*, not discovered by an interviewer.

**4. `regdocs-mcp` carries the determinism bug ADR-022 fixed here, and nobody has looked.** Same
test, same corpus, same 40 questions: **10 of 40 return a different top-20 between runs** — the
identical rate `compliance-copilot`'s BM25 showed before the rounding fix, and 0/40 after. The fix
landed in one repo. `search_notices` orders by `score DESC, effective_date DESC, doc_id, ordinal`,
which are deterministic tie-breaks that never fire, because two scores differing by one ULP are
not equal. A non-reproducible tool makes Day 8's trajectory comparison meaningless.

**5. Tool results are large, and one of them is enormous.**

| call | payload | ≈ tokens |
|---|---|---|
| `search_notices` top_k=10 | 6,685 chars | 1,700 |
| `search_notices` top_k=50 (the server's max) | 32,975 chars | 8,200 |
| `list_obligations` one page (50 items, Notice 637) | **59,307 chars** | **15,000** |
| `list_obligations` unpaginated (Notice 637) | 2,219,320 chars | 555,000 |
| largest single clause | 127,564 chars | 32,000 |

Pagination is doing real work — it is the difference between 15k tokens and 555k. But **one page
is still 15k tokens**, and an agent that pages twice while holding its history has spent 30k
tokens on one tool.

**6. Context overflow is silent, and it eats the instructions first.** This Ollama build does not
cap at 4,096: it passed 30,038 prompt tokens through, and `qwen3.5:9b` reports a 262,144-token
context. So the *default* is not the hazard. What is: when `num_ctx` is set below the prompt, the
prompt is truncated **from the front**, no error is raised, and the model answers confidently
from what is left. Measured with a needle at the start of an 8k-token prompt:

| `num_ctx` | prompt tokens actually evaluated | needle survived | error raised |
|---|---|---|---|
| 2048 | 1,026 | **no** | no |
| 4096 | 2,050 | **no** | no |
| 16384 | 10,037 | yes | no |

At 2048 the model replied *"There is no secret authorization code hidden in that text."* — fluent,
confident, wrong. **In an agent, the front of the prompt is the system prompt and the user's
question**, so an over-long tool result does not crowd out the tool result; it crowds out the
instructions telling the model what to do with it.

**7. Framework versions, none installed yet.** `langgraph` 1.2.11, `langchain-mcp-adapters` 0.3.2,
`langchain-ollama` 1.1.0, `pydantic-ai` 2.37.0, `langgraph-checkpoint-postgres` 3.1.2. LangGraph is
past 1.0, so the API is stable enough to pin without expecting churn mid-week. The checkpointer
Postgres has been up since Day 0 (ADR-004) and is unused so far — it is Day 7's, not today's.

**8. Nothing in `regops-agents` exists yet.** The package is a Day 0 scaffold with an empty
`__init__.py` and no dependencies. Today is its first code.

---

## The four problems Day 6 has to solve

**1. The agent's best tool is not its only tool, and which one it should use is a measurement.**
The prep plan mandates a LangGraph agent consuming `regdocs-mcp` — that is the deliverable and the
portability story. Research 3 says that surface is 0.195 MRR worse than the retrieval sitting in
this workspace.
*Resolution:* the agent gets **both**, as two clearly-named tools, and Day 6 measures the
difference on the same questions. `search_notices` is the portable surface any MCP host can call;
`search_local` is the measured one. The finding — *"the portable tool costs us N points, and here
is the number"* — is worth more than either choice made silently, and it hands Day 8 two
trajectories to compare instead of one. Nothing is added to `regdocs-mcp` that would drag torch
into a repo that must stay CUDA-free (ADR-001, ADR-013).

**2. A validated answer is not a true answer, and Pydantic cannot tell the difference.**
Research 2: 18 of 20 schema-valid, 12 of 20 with citations that resolve.
*Resolution:* validation is **three layers, not one**, and each is a separate measured rate.
*Shape* — Pydantic accepts it. *Reference* — every `(doc_id, section_path)` resolves against the
index. *Support* — the cited clause actually contains the claim. Only the first is free; the
second is a dictionary lookup and catches the failure research 2 found; the third needs a judge and
inherits Day 5's machinery. The repair loop retries on layers 1 and 2, and **the repair's own
success rate is measured**, because an unmeasured repair loop is just a slower way to fail.

**3. Failure modes have to be provoked on purpose, or the document is anecdotes.**
"8+ documented failures" is easy to fake by writing down whatever happened to go wrong.
*Resolution:* every entry in `FAILURE_MODES.md` carries four things — a **trigger** that
reproduces it on demand, a **measured symptom** with an n, a **mitigation**, and the **cost of
that mitigation**. Three of the eight are already measured above and will be first (hallucinated
filter arguments, unresolvable citations, front-truncated context). A failure with no reproduction
is a story; a mitigation with no cost is a sales pitch.

**4. "Which framework is nicer" is not a finding.**
The prep plan wants LangGraph and Pydantic AI compared from experience.
*Resolution:* the same task, the same model, the same two tools, the same golden subset, and four
numbers: tool-call accuracy, steps to answer, wall-clock, and what each does when a tool **raises**
— which research has not yet touched and is where frameworks actually differ. Lines of code gets
reported and explicitly *not* treated as quality. The output is a tradeoff, not a winner.

---

## Phase 0 — Housekeeping · 15 min

- [x] `gh auth status` — drifts back to `99Tungsten99`; both repos are touched today
- [x] `./scripts/stack.sh ps` — 7 services; LangFuse is needed for agent traces
- [x] `nvidia-smi` idle, and `ollama ps` empty — the reranker wants 1.33 GB alongside a 9B model
- [x] Re-read ADR-001 (why the server repo stays CUDA-free), ADR-003 (the schema is the contract),
      ADR-020 (the config ladder), ADR-022 (the determinism fix that has to travel)

## Phase 1 — Clear Day 5's debt · 45 min

Neither of these is agent work. Both are load-bearing for it, and both were promised.

- [x] **Re-verify the golden set** with `NEGATIVE_EXCERPT_CHARS = 6000` (ADR-024). Expect the
      flagged count to move off 28 and `gs-0118` to flag itself. Republish
      `verification.json`, `review_queue.md`, and the flagged count in `golden/v1/README.md`.
- [x] **Re-run `regops-evals bench --configs all`** afterwards. The 122/28 split is what the Day 5
      sensitivity run and the abstention split are keyed to, so the table has to be regenerated
      against the new split rather than left describing an instrument that has changed. Re-check
      the Phase 3 baseline gate: C1 must still reproduce `saturation.json`.
- [x] Update `results/day5/retrieval.md` and the README's numbers from the regenerated JSON.
      **Nothing here is hand-edited** — the renderer reads the data or the data is wrong.
- [x] **Port ADR-022's rounding fix to `regdocs-mcp`** (research 4): `ORDER BY round(score, 9) DESC`
      in `search_sections`, its own ADR in that repo's `DECISIONS.md`, and a test that runs one
      query four times against a fixture and asserts one ordering. Green CI on both repos before
      any agent code is written.

## Phase 2 — The LangGraph agent over `regdocs-mcp` · 90 min

- [x] `uv add --package regops-agents langgraph langchain-mcp-adapters langchain-ollama`. **Into
      the member, not the root**, and never into `regdocs-mcp`.
- [x] A ReAct agent over the four MCP tools, loaded through `langchain-mcp-adapters` against the
      server over **stdio**. The adapter is the point of the exercise: the tool schemas the model
      sees must come from the server's own definitions, not from a hand-written copy that can
      drift from them.
- [x] Add `search_local` as a second tool backed by `regops_retrieval.configs.C4` (problem 1).
      Both tools are declared in one place with their descriptions, because a tool description is
      prompt real estate and Day 6 is going to measure what a change to one does.
- [x] **A hard step ceiling and a hard wall-clock ceiling**, both returning a partial result rather
      than raising. An agent that cannot answer must say so with what it has, not disappear into a
      retry loop — and "hard-fail at N steps with a partial result" is the shape Day 7's cost
      ceiling will extend.
- [x] Trace every run to LangFuse: one span per tool call with its arguments and result size, so
      the failure work in Phase 4 has something to read afterwards.
- [x] Done when: one compliance question is answered end to end, and the trace shows the model
      calling `search_notices` and then `get_document_section` with a `doc_id` it got from the
      first call rather than one it invented.

## Phase 3 — Structured output, and citations that resolve · 60 min

- [x] A Pydantic `Answer` model — answer text, citations as `(doc_id, section_path)`, and an
      explicit `sufficient: bool` so abstention stays a first-class output rather than a phrase to
      regex for. Day 5's abstention machinery already reads that field.
- [x] **Layer 2, the one research 2 says is missing:** every citation is resolved against the index
      before the answer is returned. An unresolvable citation is a *failed validation*, not a
      cosmetic issue.
- [x] A repair loop: on schema or reference failure, hand the model its own output and the specific
      violation, and retry once. **Measure the repair rate** — how often one retry fixes it, how
      often it fails the same way twice.
- [x] Report all three layers as separate rates over the golden subset, with the research-2 numbers
      (18/20 and 12/20) as the before.

## Phase 4 — Break it deliberately · 90 min

`FAILURE_MODES.md`. Every entry: **trigger · measured symptom · mitigation · cost of mitigation.**
Three are already measured; five have to be provoked.

- [x] **F1 Hallucinated tool arguments** — measured: 9/29 filtered the gold document away.
      Mitigation candidates: drop the filters from the description, or make them opt-in via the
      system prompt. Measure the tool-description change (the prep plan's *"tool descriptions are
      prompt real estate — measure how tool-call accuracy changes when you rewrite a description"*).
- [x] **F2 Unresolvable citations** — measured: 6/18 validated answers cite something absent.
- [x] **F3 Context overflow, silent and front-first** — measured: needle at prompt start gone at
      `num_ctx` 2048/4096 with no error. Provoke it in the agent with a `list_obligations` page.
- [x] **F4 Tool-call loops** — provoke with a question whose answer is not in the corpus and watch
      whether the agent re-searches with permuted queries until the ceiling. Report steps to
      give-up with and without the ceiling.
- [x] **F5 Silent failure when a tool errors** — `regdocs-mcp` raises `ToolError` on a bad
      `doc_id`. Does the model see it, retry sensibly, or fabricate around it? Provoke by feeding
      a `doc_id` that does not exist.
- [x] **F6 Pagination ignored** — `search_notices` and `list_obligations` return `next_cursor`.
      Does the agent ever use it, or does it answer from page 1 and call that complete?
- [x] **F7 The wrong tool for the question** — a `temporal` question answered from
      `search_notices` instead of `diff_versions`. Day 5 measured `temporal` as the type reranking
      helps most, so it is the type most likely to be under-served by a lexical tool.
- [x] **F8 Non-reproducible tool output** — research 4, before the Phase 1 fix. Worth keeping as an
      entry precisely because it is *fixed*: it shows the document is a log of things that were
      found and closed, not a list of complaints.
- [x] Two more if provoking turns them up. Eight is the floor, not the target.

## Phase 5 — The same agent in Pydantic AI · 60 min

- [x] `uv add --package regops-agents pydantic-ai`. The same two tools, the same model, the same
      `Answer` model, the same question set.
- [x] Four measured columns (problem 4): tool-call accuracy, steps to answer, wall-clock p50, and
      **behaviour when a tool raises** — the one that is not a matter of taste.
- [x] Report lines of code and explicitly decline to treat it as a quality signal.
- [x] The write-up is a **tradeoff with a recommendation**, and it says which parts are preference.

## Phase 6 — Tests and write-up · 60 min

- [x] Agent tests that call **no model and no server**: a stub chat model returning scripted tool
      calls, so the graph, the step ceiling, the repair loop and the citation resolver are all
      testable in CI. The suite's no-model rule has held for five days and CI has no GPU.
- [x] A citation-resolver test with a fabricated `doc_id`, using research 2's actual bad output
      (`doc_id: "[1]"`) as the fixture — the failure that happened, as the test.
- [x] One `slow` end-to-end test: real model, real server, one question.
- [x] **`FAILURE_MODES.md`** — the deliverable.
- [x] **ADR-025** the two tool surfaces, and the measured cost of the portable one.
- [x] **ADR-026** three-layer validation, and why schema validity is not citation validity.
- [x] **ADR-027** LangGraph vs Pydantic AI on this task, with the numbers.
- [x] `agents/README.md`, root `README.md`, `initial-setup.md`; commit, push, CI green on both repos.

---

## Deliverables

`regops-agents` with a LangGraph ReAct agent over `regdocs-mcp` and a local retrieval tool ·
three-layer output validation with a measured repair rate · a Pydantic AI agent on the same task ·
**`FAILURE_MODES.md` with 8+ reproducible failures** · 3 ADRs · a re-verified golden set and a
regenerated Day 5 table · `regdocs-mcp` determinism fixed and released · green CI on both repos.

**Done when** `FAILURE_MODES.md` has eight entries a stranger could reproduce from the document
alone, and the tool-surface tradeoff is a number rather than an opinion.

## Decisions I would want a steer on

1. **Does the agent get the local retrieval tool at all, or only the MCP surface?**
   *Recommendation: both, and measure.* Only-MCP is the cleaner portability story and is 0.195 MRR
   worse on measured evidence; only-local abandons the deliverable the prep plan actually names.
   Both costs one extra tool description and converts an architectural assumption into a number.
   If the portfolio story is "my MCP server is the product", that argues for MCP-only and it is a
   decision to take now, because it changes Phase 2.
2. **Does Phase 1's re-verification block the day, or run unattended alongside Phase 2?**
   *Recommendation: block on it.* It is ~20 min of GPU and it changes the flagged split; starting
   agent work against numbers that are about to move is how Day 5's table would have ended up
   describing an instrument that had already changed. The Day 5 close-out committed to doing it
   first, and the reason still holds.
3. **`qwen3.5:9b` for the agent, or the larger `qwen3.8`?**
   *Recommendation: `qwen3.5:9b`, and measure the gap on tool-call accuracy only.* It is the model
   Day 5's generation numbers were taken on, so agent results stay comparable, and the tool-call
   decision measured at p50 0.8s against `qwen3.8`'s 18.1s on the first call. If tool-call accuracy
   turns out to be the binding constraint rather than retrieval, that is itself the finding, and
   Day 9's model-routing work is where it gets acted on.

## Risks

1. **The failure document becomes a list of things the model did once.** The whole value is
   reproducibility. Mitigated by the four-field format — an entry without a trigger and an n does
   not go in — and by three of the eight already having measured numbers before the day starts.
2. **`langchain-mcp-adapters` 0.3.2 is pre-1.0 and the MCP spec has moved fast.** The server pins
   `mcp>=2.1,<3` and targets spec revision `2026-07-28`; the adapter may not. Mitigated by trying
   the adapter against the running server in the first 20 minutes of Phase 2, before any graph is
   written, and by falling back to the SDK client directly if it fights — the deliverable is an
   agent that speaks MCP, not one that speaks LangChain's wrapper of it.
3. **Phase 1 changes the flagged split enough to move a Day 5 conclusion.** Possible: the
   parent-child verdict already flips between the 150- and 122-item runs. Mitigated by the fact
   that this is the intended outcome of a sensitivity run doing its job — the write-up updates and
   says what moved, rather than the fix being avoided to protect a published number.
4. **Eight failure modes is more provoking than 90 minutes holds.** Mitigated by F1–F3 being
   measured already, and by the descope order below.

**Descope order if behind:** F6/F7 (pagination, wrong-tool) → the Pydantic AI comparison's
wall-clock column → the repair loop's second retry. **Never cut** Phase 1, the citation resolver,
or the four-field format in `FAILURE_MODES.md`: the first is a promise already made in writing, the
second is the only thing standing between a validated answer and a fabricated citation, and the
third is what makes the document evidence instead of an anecdote.

---

## Outcome

All six phases complete. 198 tests green (1 skipped, 2 `slow` deselected), ruff clean, CI green
on both repos. `FAILURE_MODES.md` ships **12 entries** against a floor of 8, each with a trigger,
a symptom with an `n`, a mitigation and the mitigation's cost. Three ADRs here, one in
`regdocs-mcp`.

The day's sentence, read off the evidence rather than decided in advance:

> **Tool *selection* was correct in every single provocation. F1 invents filters, F5 ignores a
> recovery path a tool handed it, F7 calls the right tool with an invented `doc_id` — routing is
> not the hard part, argument grounding is. And four of the twelve failures belong to the
> frameworks, where they are silent.**

### What the plan got right

**Blocking on Phase 1 was correct and cheap.** Re-verification moved exactly one item and the
re-sweep produced byte-identical rankings, so the cost of doing it first was ~45 minutes and the
cost of doing it after would have been a table describing an instrument that had moved.

**The four-field format is what makes the document evidence.** Writing "trigger · symptom · n ·
mitigation · cost" for every entry forced two of them to be downgraded honestly (F5's failure is
milder than predicted; F6's predicted failure did not occur) and forced the mitigations to carry
their costs — F1's prompt suppresses a capability, F3's cap creates F6, layer 2 detects without
fixing.

**Problem 1's resolution earned itself twice.** Giving the agent both tool surfaces produced the
number ADR-025 needed *and* the finding that contradicts it: C4 context made citations resolve
**less** often (14/30 vs 19/30). Choosing one surface silently would have produced neither.

**Research 6 was right about the hazard and right about the direction.** Front-first truncation
reproduced exactly — needle gone at `num_ctx` 2048 and 4096, no error either time.

### Where the plan was wrong, and what replaced it

- **`langchain-mcp-adapters` was listed as Risk 2 and is a hard blocker, not a risk.** 0.3.1's
  `mcp>=1.24.0` has no upper bound, resolves against `mcp` 2.1 and dies at import on a name v2
  removed; 0.3.2 pins `<2.0.0`, which excludes spec `2026-07-28`. **No version works.** The
  plan's fallback — the SDK directly — was taken inside the first twenty minutes, as written.
  Lesson worth more than the workaround: *do not take a framework's integration package as
  evidence the integration is available.*
- **Research 1 did not reproduce.** It recorded 9/29 questions losing the gold document to an
  invented filter; a declared, deterministic 30-question sample with schemas read live from the
  server measured **1/29**. The earlier sample and prompt cannot be reconstructed, so the new
  table is what is quoted and `FAILURE_MODES.md` says the earlier figure did not reproduce rather
  than using the more dramatic one.
- **Research 2 did not reproduce either, in the direction that strengthens the argument.** It
  measured 18/20 schema-valid; passing the full JSON Schema to Ollama's `format` gives **30/30**.
  Constrained decoding has solved the shape problem completely — and the reference problem not at
  all, at 19/30. And the dominant failure is *omission* (10 of 11 cite nothing), not the
  fabrication the research predicted.
- **Decision 3 was resolved by measurement rather than by the recommendation.** The plan proposed
  `qwen3.5:9b` and to "measure the gap on tool-call accuracy only". Measured on both models and
  both prompts, **one sentence of prompt bought what a 2.6× larger model bought** — 5 unasked-for
  filters to 0, at half the latency and 6.6 GB against 17 GB. Model size was never the binding
  constraint, which is not what the plan expected to find.
- **The repair loop was a named deliverable and is now off by default.** The plan required its
  success rate to be measured. Measured: **0 of 11**. Ten changed nothing; one converted omission
  into fabrication. Keeping it would have doubled latency on the affected items for nothing.
- **Two Phase 4 predictions were wrong in useful ways.** F6 predicted answering from page one; the
  agent paged correctly with a cursor and died of *volume* instead. F7 predicted `diff_versions`
  would never be called; it was called, with an invented `doc_id`. Both replacements are better
  findings than the predictions.
- **Phase 1 exposed a defect in the renderer, not the data.** `results/day5/retrieval.md` is
  generated, but the generator carried `122` and `28` as literals — including a JSON key named
  `unflagged_122` — so a re-verification silently made a *generated* document wrong. The sweep now
  records a `counts` block at run time and the write-up reads it.

### Findings worth carrying forward

- **The frameworks fail quietly and the model fails loudly.** F9, F10 and F12 raise nothing at
  all, and two of them emit output that looks like success — LangGraph appends *"Sorry, need more
  steps to process this request."* at its ceiling, first-person and indistinguishable from a model
  declining. A wrong filter, by contrast, still returns results you can inspect.
- **"Hand it back and ask again" recovered nothing, three times independently.** The hand-rolled
  repair loop: 0 of 11. Pydantic AI's internal output-validation retry: 5 of 6 runs exhausted it.
  Tripling that retry budget: **zero** additional completions and 3× the latency.
- **Citation compliance is not a retrieval property.** Better retrieval (C4 over BM25) made
  citations resolve *less* often, entirely through the model declining to cite. F2's fix belongs
  in the prompt or the schema, not the ranker.
- **Batch by model, for the fourth day running.** The C4 measurement embeds with
  `nomic-embed-text` and answers with `qwen3.5:9b`; unbatched that is one 17.7 GB swap per item.
  Every question vector is computed before the generator is touched.
- **A four-member workspace needs a fourth fixture spelling.** `agents/tests/` uses
  `fixtures_agents.py` with `pytest_plugins`, for the reason `retrieval/tests/` does.
- **A scripted chat model must return fresh message ids.** Returning the same `AIMessage` twice
  does not loop a LangGraph agent, it *ends* it — `add_messages` merges by id, so the second reply
  replaces the first and the tool call reads as answered. A test that cannot repeat itself cannot
  exercise a step ceiling.

### Deliberately deferred

**Layer 3 (support) is named and not implemented.** Reference validity is mechanical and runs in
CI; support needs a judge, and Day 5 already has that machinery pointed at `qwen3.8`. Building a
second judge here would duplicate it. What matters is that the three layers are named separately
so "validated" cannot silently mean "layer 1".

**A schema-level fix for F2** — requiring a non-empty `citations` array so constrained decoding
cannot emit `[]` — is the one mechanism that has worked perfectly here, and it cannot express
"unless this is an abstention". It needs two schemas and a routing decision. Named, not done.

**F5 and F7 ship open.** Making the model act on a tool's recovery path is another unmeasured
prompt claim competing with F1's measured one; constraining it to look up an id before using it is
Day 7's supervisor, not a prompt patch.

### End-to-end proof

`uv run regops-agents "What must a bank do to identify the beneficial owner of a customer?"`
answers end to end, and the trace shows `search_notices` followed by `get_document_section` called
with a `doc_id` taken from the first result rather than invented. Every number in
`FAILURE_MODES.md` has a command next to it that reproduces it, and the rows those numbers average
over are committed in `results/day6/`.
