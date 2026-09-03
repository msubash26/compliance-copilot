# Day 7 — Multi-agent, and the case against it

**Repo:** `compliance-copilot` (member `regops-agents`) · **Date:** 2026-09-07
**Budget:** ~6.5h

> The prep plan's bar, which is unusually an argument rather than an artefact: *"Be ready to argue
> the case against multi-agent. The honest answer for many tasks is that a single well-toolled
> agent is cheaper, faster and easier to debug, and that multi-agent earns its keep only when
> subtasks are genuinely parallel or need different context windows. Saying that unprompted marks
> you out."*

---

## Context

Day 6 put one model in front of the index and wrote down what broke. Day 7 puts five in front of
it and has to answer a harder question: **did that help?** The prep plan asks for a supervisor, a
fan-out, a checkpointer, an interrupt, a ceiling and a comparison — six mechanisms — and then tells
you the interesting answer is probably *no*. So the deliverable is not a working supervisor. A
working supervisor is the easy half. It is a **comparison table with the single agent in it**, and
a fan-out measurement that is allowed to come back negative.

It already has. See research 1.

### Carried forward from Days 1–6

Six items are open, and Day 6 assigned three of them to today by name.

- **F7 — the right tool, called with an invented identifier — ships open**, and Day 6's close-out
  says why: *"constraining it to look up an id before using it is Day 7's supervisor, not a prompt
  patch."* A `citation_checker` node that resolves every `(doc_id, section_path)` before the
  synthesiser sees it is that constraint, expressed structurally.
- **F5 — a tool error's recovery path is ignored — ships open.** The single agent stops and asks
  the user for a valid id. A supervisor can route that back to the `retriever` worker instead of
  back to the human, which is the one thing the extra machinery is obviously good for.
- **Layer 3 (support) is named and not implemented.** Day 6 built shape and reference validation
  and deferred support because it needs a judge and Day 5 already has one pointed at `qwen3.8`.
  The prep plan's `citation-checker` sub-agent **is** layer 3's home. Building it as a new judge
  today would duplicate Day 5's machinery; building it as a node that calls Day 5's machinery
  closes a deferred item at roughly zero marginal cost.
- **F2's schema-level fix is named, not done** — requiring a non-empty `citations` array so
  constrained decoding cannot emit `[]`, which needs two schemas and a routing decision. The
  supervisor has a router. This is the first day where the two-schema fix is cheap.
- **LangFuse is not wired into any agent.** `pyproject.toml` pins the v4 SDK and
  `scripts/hello_trace.py` proves the connection; nothing in `regops_agents` emits a span. Day 8's
  plan says *"all traces in LangFuse"*. Today is the first day with nested spans worth looking at.
  See decision 3 — this is a genuine steer, not a foregone conclusion.
- **Ollama serialises, for the fifth day running.** This has now shaped four designs, and today it
  determines the day's headline number rather than merely constraining the schedule.

And two facts today is measured against:

- **Day 6's single agent, on six golden questions:** 6/6 completed, 11 tool calls, 1.83 mean,
  p50 **5.61s**, one tool error survived. That is the number the supervisor has to beat, and on
  these questions it will not. `results/day6/frameworks.json`.
- **The golden set is 150 items** across `factual_lookup` 45 / `negative` 35 / `multi_hop` 30 /
  `comparative` 25 / `temporal` 15. The router does **not** get a new taxonomy invented for it; it
  gets Day 4's, which is already the axis Day 5's results are cut along.

### Research completed before planning (ADR-002's rule)

Everything below was measured today, against the running stack, the real index and pinned
versions.

**1. Parallel fan-out buys 1.01× on this hardware.** Four independent subtasks over one 14,796-char
assembled context — the exact shape a supervisor's fan-out takes — `qwen3.5:9b`, `think: false`,
`num_ctx` 8192, model pre-warmed so neither arm pays the load:

| | sequential | parallel (`asyncio.gather`) |
|---|---|---|
| wall clock, 4 subtasks | **5.69s** | **5.64s** |
| per-subtask latency | 2.25 / 0.47 / 2.05 / 0.92 | 2.19 / 4.72 / 4.26 / 5.64 |
| output tokens | 165 / 13 / 161 / 55 | identical |
| | | **speedup 1.01×** |

The parallel arm's per-task latencies are the cumulative sum of the sequential ones. That is not
contention, it is a queue: the server ran them one after another and every caller waited for its
turn. `OLLAMA_MAX_LOADED_MODELS=1` and `OLLAMA_NUM_PARALLEL` unset. **The theoretical ceiling if
fan-out were free is 5.69 / 2.25 = 2.53×**, and that is the number to quote as the prize, because
it bounds what any amount of orchestration could ever win here.

This is the day's headline and it should be stated first, not buried: *on a single-GPU,
single-model-server deployment, fanning LLM subtasks out in parallel buys nothing, because the
bottleneck is not the orchestrator.*

**2. The Postgres checkpointer works, and the Day 0 container was provisioned for it.**
`langgraph-checkpoint-postgres==3.1.2` resolves against the pinned `langgraph==1.2.11` and
`langchain-core==1.6.1` **without moving `langgraph-checkpoint` off 4.2.0**, imports clean (both
`PostgresSaver` and `AsyncPostgresSaver`), and against the live `regops-checkpointer-postgres-1`
on 127.0.0.1:5433 `setup()` created `checkpoints`, `checkpoint_blobs`, `checkpoint_writes` and
`checkpoint_migrations` in **0.01s**. `CHECKPOINTER_DSN` is already in `.env` from Day 0 (ADR-004).

This was checked by installing and importing, not by reading a version constraint, because F12
is what happens when you read the constraint.

**3. A run survives a process boundary and resumes.** A three-node graph interrupting in `review`,
started in one interpreter and resumed in another with nothing shared but Postgres:

```
A: interrupts -> [Interrupt(value={'ask': 'approve the gap report?'...}, id='4aec6c35...')]
A: state now  -> ('review',)
--- process A exited ---
B: pending    -> ('review',) | tasks: [(Interrupt(... id='4aec6c35...'),)]
B: final      -> ['draft', 'review', 'finalise:approved']
```

Same interrupt id across the boundary. The mechanism the prep plan asks for exists and is one
import away.

**4. …and the node body before `interrupt()` executes twice.** Same probe with a side-effect
counter as the first statement of the interrupting node: **2 executions for 1 logical visit**,
once on the interrupting run and once on resume. `interrupt()` replays its node from the top.

This is the finding that changes a design rather than confirming one. A `gap_analyst` node that
calls the model *and then* asks for approval pays for that inference twice, silently, and any
non-idempotent side effect happens twice. The rule falls out of it: **`interrupt()` is the first
statement of its own node**, and the expensive work sits in the node before it, so the checkpoint
boundary lands between them. It becomes F13.

**5. `langgraph-supervisor==0.0.31` resolves and imports.** Against the same pins,
`create_supervisor` is importable and pulls only `langchain-protocol==0.0.19` in addition. So the
prebuilt path is genuinely available — which makes not taking it a decision to argue rather than a
constraint to accept. See decision 1.

---

## The five problems Day 7 has to solve

**1. The prep plan asks for a measurement whose answer is already known to be "nothing".**
Research 1: 1.01×. The tempting move is to quietly drop the fan-out, or to fan out something
trivially parallel and report a flattering ratio.
*Resolution:* publish the negative result as the headline, and make it *informative* by measuring
three fan-out shapes rather than one — (a) four LLM subtasks, the measured 1.01× baseline; (b) a
**mixed** fan-out where one branch is retrieval and reranking (CPU/GPU-bound but not the LLM queue)
and the others are model calls; (c) LLM subtasks with `OLLAMA_NUM_PARALLEL` raised, to establish
whether the ceiling is the server's configuration or the GPU. Three numbers and a stated ceiling of
2.53× answer *"when would fan-out earn its keep here"*, which is the question behind the prep
plan's bullet. One number answers nothing.

**2. "Multi-agent" must not be a more expensive way to do Day 6's job.**
Five model-calling nodes against a serialising server is, on Day 6's six questions, strictly worse
than one agent that answered them in p50 5.61s.
*Resolution:* the supervisor is run on **Day 6's exact six questions**, where it is expected to
lose, *and* on a multi-document gap-analysis task the single agent structurally cannot do — "which
of these obligations does this policy fail to cover", which needs one context window per document
and a synthesis across them. **Both numbers get published**, including the losing one. The
sentence the day is aiming for is not *"multi-agent is better"*; it is *"multi-agent cost us 3× the
wall clock on lookup and was the only thing that completed the coverage task, so we route by task
shape"* — and that sentence is only available if the losing number is measured.

**3. The citation-checker is Day 6's deferred layer 3, and building a second judge would be waste.**
*Resolution:* `citation_checker` is one node with two stages — layer 2 reuses Day 6's
`check_references` verbatim (mechanical, free, no model), and layer 3 calls **Day 5's existing
judge machinery** on `qwen3.8`. It closes the deferred item, gives F7 a structural fix instead of
another prompt sentence, and gives F2 a second line of defence. Nothing new is built that Day 5 or
Day 6 already built.

**4. A human-in-the-loop interrupt has a measured double-billing hazard.**
Research 4: 2 executions per logical visit.
*Resolution:* the graph is arranged so `interrupt()` is the first statement of `approve_report`,
with `gap_analyst` — the expensive node — immediately before it. This is enforced by a **test that
counts node-body executions across a resume and asserts 1**, so the arrangement cannot be undone by
a later refactor without CI saying so. It is written up as F13 with its trigger, its n and the cost
of the mitigation (one extra node, one extra checkpoint write).

**5. "$X" has no meaning on a 3090, and a step ceiling wearing a dollar sign is the cheap version.**
The prep plan says *"hard-fail at N steps or $X, with a partial result returned rather than an
exception"*. There is no per-token price here.
*Resolution:* the budget is denominated in the three things that are actually scarce — **steps,
wall-clock seconds, and tokens** — with tokens read from Ollama's `eval_count` and
`prompt_eval_count` (research 1 collected both, so the plumbing is known to work). A single
published `$`-equivalent is computed from one named cloud price, so the ceiling is demonstrably a
*cost* ceiling with a currency conversion rather than a step ceiling with a dollar sign painted on
it. The shape of the stop is Day 6's, already built and already argued: the run returns, marked,
with what it had. `Run.stopped_by` gets a sibling.

---

## Phase 0 — Housekeeping · 15 min

- [x] `gh auth status` — drifts back to `99Tungsten99`; verify `msubash26` and `user.email`
- [x] `./scripts/stack.sh ps` — 7 services. Today the one that matters is
      `regops-checkpointer-postgres-1` on 5433, idle since Day 0
- [x] `nvidia-smi` idle, `ollama ps` empty — five model-calling nodes on one 6.6 GB model, and the
      judge is 17 GB, so **batch by model for the fifth day**: the judge runs after the graph, not
      inside it
- [x] Re-read ADR-004 (why the checkpointer has its own Postgres), ADR-025 (both tool surfaces),
      ADR-026 (three layers), ADR-027 (the framework comparison is a tradeoff, not a winner), and
      F5 / F7 / F9 / F10 — today either closes them or inherits them

## Phase 1 — State, budget, checkpointer · 75 min

Nothing here is multi-agent. All of it is load-bearing for everything that follows, and the budget
is the piece most likely to be bolted on badly if it is left until last.

- [x] `uv add --package regops-agents langgraph-checkpoint-postgres` — research 2 says 3.1.2, and
      that it does **not** move `langgraph-checkpoint` off 4.2.0. Re-check the lock diff and stop if
      it does.
- [x] `SupervisorState` as a `TypedDict` of JSON-shaped values only. The budget goes in as a
      **dict, not a dataclass** — the checkpointer serialises state, and a dataclass is how that
      turns into a debugging afternoon (risk 4).
- [x] `Budget`: `max_steps`, `max_seconds`, `max_tokens`, with `spend()` debited by **every** worker
      into one shared counter. Five workers with five private ceilings is five ceilings, not one.
- [x] The ceiling returns a **partial result**, in Day 6's shape and with Day 6's vocabulary —
      `stopped_by` says which of the three fired, and the answer is prefixed with what was spent.
      An agent that exhausts its budget has usually searched and read two clauses; throwing that
      away turns a degraded answer into no answer.
- [x] The `$`-equivalent: one function, one named cloud price in a constant with a dated comment,
      tokens → dollars. It is a conversion, and the code says so.
- [x] Tests, no model and no Postgres: budget arithmetic; each of the three ceilings fires
      independently; the partial result carries the work already done; a worker cannot spend past
      zero. Reuse `agents/tests/fixtures_agents.py` and **fresh message ids** — Day 6's scripted
      model does not loop a graph without them.
- [x] One `slow`-marked test for the two-process resume (research 3), skipped when
      `CHECKPOINTER_DSN` is unset, so CI stays honest without Postgres.

## Phase 2 — The supervisor graph · 90 min

- [x] Hand-rolled `StateGraph`, not `langgraph-supervisor` — decision 1, and it is the decision I
      most want a steer on before this phase starts.
- [x] `router` classifies with **Day 4's taxonomy** (`factual_lookup` / `multi_hop` / `comparative`
      / `temporal` / `negative`). Do not invent a second taxonomy; Day 5's results are already cut
      along this one and Day 8's eval will be too.
- [x] Four workers, each reusing what exists rather than restating it:
      - `retriever` — Day 6's two tool surfaces (`search_notices` and `search_local`, ADR-025)
      - `obligation_extractor` — Day 6's `Answer` schema through Ollama's `format`, which measured
        **30/30** on shape
      - `gap_analyst` — the only genuinely new worker, and the only one that needs its own context
        window per document
      - `citation_checker` — layer 2 (`check_references`, free) then layer 3 (Day 5's judge)
- [x] `synthesiser` sees only what `citation_checker` passed. That is F7's structural fix: an
      invented `doc_id` cannot reach the answer, because a node between the two resolves it.
- [x] The router may route a failed tool call back to `retriever` instead of back to the human —
      F5's fix, and the clearest case for the extra machinery existing at all.
- [x] Every worker debits the one shared `Budget` before it returns.

## Phase 3 — Fan-out, and what it actually bought · 60 min

- [x] `Send` for the fan-out; the independent subtasks are per-document extraction inside
      `gap_analyst`, which is the only place in this graph where independence is real.
- [x] Measure **three shapes** (problem 1): all-LLM (re-confirming research 1's 1.01× *inside the
      graph*, not just against the raw API), mixed LLM + retrieval, and all-LLM with
      `OLLAMA_NUM_PARALLEL` raised. Record the 2.53× ceiling next to each.
- [ ] `results/day7/fanout.json`, and a renderer that reads it. **Nothing hand-edited** — Day 6
      Phase 1 found a generated document carrying `122` as a literal, and that lesson cost 45
      minutes.
- [ ] An ADR that says what the numbers decided: fan-out kept for context-window isolation, or
      removed. If it is kept for a reason that is not wall-clock, the ADR says which reason and
      concedes the wall-clock case.

## Phase 4 — The interrupt, and the double-execution rule · 45 min

- [x] `approve_report` with `interrupt()` as its **first statement**; `gap_analyst` immediately
      before it. Research 4 is the reason and the ADR says so.
- [x] The regression guard: a test that counts executions of the interrupting node's body across a
      resume and asserts **1**. Without it, the arrangement is a comment.
- [x] CLI: `--thread <id>`, `--resume`, `--approve` / `--reject <reason>`. A rejection routes back
      to `gap_analyst` with the reason in state, which is the only version of HITL that is worth
      more than a confirmation dialog.
- [ ] **F13** in `FAILURE_MODES.md`, four fields as always: trigger (the probe), symptom (2 of 2),
      mitigation (interrupt-first node placement), cost (one extra node and one extra checkpoint
      write per approval).

## Phase 5 — Plan-and-execute, and the case against multi-agent · 60 min

This is the prep plan's own descope item 4. It survives here only because it costs one node.

- [ ] Plan-and-execute as a **variant of the same graph** — plan once up front, execute the steps —
      rather than a second implementation. The router already produces a plan-shaped artefact; the
      variant stops re-consulting it.
- [ ] Run three architectures on the same set: **Day 6's single agent**, the supervisor, and
      plan-and-execute. Six golden questions (where the single agent should win) plus three
      gap-analysis tasks (where it should fail).
- [ ] The table: task completion, steps, tool calls, wall-clock p50, tokens, `$`-equivalent. Lines
      of code reported and explicitly **not** treated as quality — ADR-027's rule, applied again.
- [ ] Write the paragraph the prep plan actually asks for, and write it against the day's own
      numbers rather than from the blog-post version: where the single agent wins, by how much, and
      the two conditions under which that reverses.

## Phase 6 — Tests, ADRs, write-up · 60 min

- [ ] ADRs: the supervisor is hand-rolled (or not); the budget is denominated in three currencies
      and converted once; fan-out's verdict from Phase 3; `interrupt()` node placement.
- [ ] `FAILURE_MODES.md`: F13, plus **honest status changes to F5 and F7** — closed by the graph,
      or still open with the reason. Day 6 assigned them here; leaving them silently open is worse
      than leaving them open loudly.
- [ ] `README.md` — Day 7 section, the architecture table, the status line, the test count.
- [ ] `results/day7/` committed: `fanout.json`, `architectures.json`, the resume transcript.
- [ ] `/home/subash/regops/initial-setup.md` — Days 0–7, and the new gotchas (the interrupt replay,
      `dict_row` on the checkpointer connection, `CHECKPOINTER_DSN` living in `.env`).
- [ ] `## Outcome` appended here. Green CI.

---

## Deliverables

`regops-agents` with a supervisor graph over five workers · a Postgres checkpointer with a
demonstrated cross-process resume · an HITL interrupt whose node placement is enforced by a test ·
a three-currency budget that returns a partial result · **a fan-out measurement that is allowed to
be negative** · a three-architecture comparison including Day 6's single agent · F13 and honest
status changes to F5 and F7 · 3–4 ADRs · green CI.

**Done when** the comparison table has the single agent in it and the fan-out number is published
whatever it says — and when the paragraph arguing *against* multi-agent cites this project's own
measurements rather than received wisdom.

## Decisions I would want a steer on

1. **`langgraph-supervisor` (0.0.31, verified importable) or a hand-rolled `StateGraph`?**
   *Recommendation: hand-rolled.* The three things that make today interesting — one budget shared
   across five workers, an interrupt placed to avoid a measured double-billing, a partial result at
   the ceiling — are precisely what a prebuilt supervisor owns and would hide, and F12 is four days
   old. Cost: roughly 80 more sloc, and losing the "I used the standard package" line.
   **The counter-argument is real and worth hearing**: an interviewer may read hand-rolling as not
   knowing the ecosystem, and "I evaluated `langgraph-supervisor` and rejected it because X" is
   only a good answer if X is specific. If the portfolio story is *"I ship on the ecosystem's
   rails"*, that argues for the package and it changes Phase 2 entirely, so it is a decision for
   now rather than for 90 minutes in.
2. **Does a negative headline lead the write-up?**
   *Recommendation: yes.* 1.01× is the most defensible number this project has produced about
   architecture, and the prep plan explicitly says the unprompted case against multi-agent is what
   marks a candidate out. The risk is that a skim reads "the fan-out didn't work" as "the candidate
   couldn't build a fan-out", which is a presentation problem — mitigated by publishing the 2.53×
   ceiling in the same table, so the reader can see the prize was small before the attempt.
3. **LangFuse today, or Day 8?**
   *Recommendation: today, minimally — spans on the five nodes and nothing else.* Today is the
   first thing in this project with a nested trace worth looking at, and the fan-out measurement is
   far easier to *show* as a Gantt of spans than to argue from a JSON file. But it is written in
   Day 8's bullet list, and half an hour spent here is half an hour not spent on Phase 5, which is
   already the descope candidate. Genuine steer.
4. **Do the gap-analysis tasks get scored expectations today?**
   *Recommendation: three hand-written tasks, unscored.* Day 8 owns the ~30-task eval and its
   judge calibration; inventing a scoring rubric today produces a second one to reconcile. Today
   needs something to *run*, not something to grade.

## Risks

1. **The day produces a negative result and reads as a failed day.** This is the intended outcome
   of a measurement doing its job, and it is the prep plan's own stated thesis. Mitigated by making
   the comparison table the primary artefact rather than the supervisor, and by publishing the
   ceiling alongside the result so the size of the forgone prize is visible.
2. **Five model-calling nodes against a serialising server make a 60-second task.** Research 1 says
   the queue is real and total. Mitigated by the wall-clock budget being a first-class ceiling
   rather than a safety net, by all five workers sharing **one** model so there is no swap, and by
   the 17 GB judge running after the graph rather than inside it.
3. **`Send` fan-out and `interrupt()` have an interaction nobody here has tested.** Mitigated by
   ordering: Phase 3 lands the fan-out and Phase 4 lands the interrupt, so the interaction is met
   with exactly one new moving part. If they fight, the interrupt wins and the fan-out is measured
   outside the interrupting path.
4. **The checkpointer serialises state, and state that is not JSON-shaped fails at the boundary
   rather than at construction.** Mitigated by the budget being a dict, the state being a
   `TypedDict` of primitives and messages, and the two-process resume test existing from Phase 1 —
   before there is anything complicated in the state to break it.
5. **`citation_checker` reaching for Day 5's judge drags a 17 GB model into the graph.** Mitigated
   by layer 2 running inside the graph (mechanical, free) and layer 3 running as a post-pass over
   the completed runs, which is also what makes it comparable across the three architectures.

**Descope order if behind:** Phase 5's plan-and-execute variant (the prep plan's own item 4) → the
third fan-out shape (raised `OLLAMA_NUM_PARALLEL`) → layer 3 in `citation_checker`, leaving layer 2.
**Never cut:** the ceiling returning a partial result, the two-process resume proof, and the fan-out
measurement. The first is the prep plan's explicit wording, the second is the only claim here that
a restart cannot fake, and the third is the day's finding.
