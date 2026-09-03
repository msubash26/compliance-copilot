# Day 8 — Agent evaluation, and a gate that can actually fail

**Repo:** `compliance-copilot` (members `regops-evals`, `regops-agents`) · **Date:** 2026-09-08
**Budget:** ~7h, of which ~45 min is human hand-scoring that nothing else can do

> The prep plan's bar: *"you can change a prompt, push, and have CI tell you whether you made it
> worse. Very few portfolio projects can do this, and it's exactly what 'productionising GenAI'
> means."* Day 8 is on the never-cut list, with Days 4, 5 and 13.

---

## Context

Days 6 and 7 built two agents and measured them once each. Day 8 makes the measurement
**repeatable, mechanical and enforced** — which is a different thing, and the harder one. A number
in a write-up is a claim about a day. A gate is a claim about every day after it.

The day has one genuine obstacle and one genuine gift, and both were found before planning.

The obstacle: **the gate cannot run where the prep plan says to run it.** CI has no GPU, this
account has no self-hosted runner, and the project's own rule since Day 4 is that a test which
cannot run in CI is not a gate. The gift: **this pipeline is exactly deterministic** — the same
tasks re-run produce byte-identical answers, across process boundaries, to the digit. That makes
the prep plan's ">5% drop" threshold about fifty times looser than it needs to be.

### Carried forward from Days 1–7

- **LangFuse is still not wired into any agent.** Day 7's decision 3 recommended it and it lost to
  Phase 5; the close-out recorded it as *genuinely undone rather than half-done*. It is Day 8's own
  bullet — *"all traces in LangFuse, screenshot the dashboard"* — and a supervisor with five
  workers and a fan-out is the first thing in this project with a trace worth looking at.
- **Layer 3 (support) has been deferred twice**, on Day 6 (needs a judge) and Day 7 (layer 2 was
  already at its ceiling, so a judge would have measured nothing). Day 8's LLM-as-judge bullet
  *is* layer 3. Third time it gets built, and this time there is something for it to disagree with.
- **No golden item has ever been reviewed by a human.** Every one carries
  `verification.human_reviewed: false` and `evals/tests/test_golden_set.py` asserts it (ADR-017).
  Day 8 needs ~20 hand-scored examples to state a judge agreement rate. That boundary is
  load-bearing and must not be dissolved by accident — see problem 4.
- **The supervisor does not record its individual tool calls.** `retrieve` performs one search and
  N reads and reports "15 hits, 11,579 chars". Tool-call precision and recall need the calls
  themselves, and so does a LangFuse span tree. One piece of instrumentation serves both.
- **The fan-out width is 4 against 18 matching documents**, named and left in Day 7's close-out.
  Day 8's coverage tasks will expose it as a recall ceiling rather than a design preference, which
  is the right way for it to come back.
- **`diff_versions` is unreachable from the supervisor** (ADR-028 forbids model-supplied
  identifiers). Any task set that includes a version question is measuring a tool nothing can call.

### Research completed before planning (ADR-002's rule)

Measured today, against the running stack and the real index.

**1. The pipeline is exactly deterministic, and that changes the gate.** Ten golden tasks through
the supervisor, three times in one process and once more in a **fresh interpreter**:

| | |
|---|---|
| items differing in route, citations, steps, tokens or answer text | **0 / 10** |
| resolvable citations, per run | 21, 21, 21, 21 |
| total tokens, per run | 39,737 — identical to the digit |
| total steps, per run | 42, 42, 42, 42 |
| wall clock, per run | 67.2s / 58.6s / 59.7s / 60.3s (**6.5% spread**) |

Cross-process, 10 of 10 answers were byte-identical. **The noise floor on every quality metric is
zero.** Latency is the only thing that moves.

This is not luck and it was not free: temperature 0, `think: false`, Ollama's constrained
decoding, and two ranking-determinism fixes that cost the better part of a day between them
(ADR-022 here, ADR-008 in `regdocs-mcp` — 9 of 40 queries returned a different top-20 before them).
A gate that can detect a single regressed task is the dividend from that work.

**2. The self-hosted LangFuse v4 stack is write-only.** Ingestion works —
`auth_check` returns `True`, and a span with three nested generations lands with **0.8 ms** of
in-process overhead, which is nothing against a 5.9s run. The read API does not:

| endpoint | |
|---|---|
| `/api/public/health`, `/api/public/projects` | 200 |
| `/api/public/traces`, `/observations`, `/scores` | **404** — *"not available on deployments running in Langfuse v4 events_only mode"* |

Two consequences. The API shape has changed: v3's `start_as_current_span` and
`start_as_current_generation` are **gone**, replaced by
`start_as_current_observation(name=..., as_type="span" | "generation")`, and most published
examples still show the old names. And **LangFuse cannot be the measurement store** — scores
pushed to it cannot be read back here — so the gate reads a committed artifact. That is the right
architecture anyway; now it is a measured constraint rather than a preference.

**3. The judge discriminates, and it is ten times cheaper than Day 5 implied.** `qwen3.8` with Day
5's `JUDGE_GROUNDED` rubric, over eight of the supervisor's own answers, each judged twice — as
produced, and with one invented requirement appended (*"retain these records for at least 17 years
and notify the Authority within 3 business days"*):

| | |
|---|---|
| poisoned answers judged grounded | **0 / 8** — it caught every one |
| as-produced answers judged grounded | **6 / 8** — not a rubber stamp |
| seconds per judge call | **3.6** |

Both numbers matter. A judge that passed everything would be perfectly self-consistent and
worthless; this one refused two of the graph's own answers, and those two are exactly where a
human hand-score has something to decide. At 3.6s, judging thirty tasks is two minutes, not the
hour Day 5's `qwen3.8` timings implied.

Caveat to carry into the write-up: an invented 17-year retention period is a *blatant* poison.
8/8 on blatant says nothing about subtle, and the calibration set is where that gets tested.

**4. Minimum steps are supplied by the golden set, not invented.** Distinct gold documents per
item, by query type:

| query type | items | distinct gold documents |
|---|---|---|
| `factual_lookup` | 45 | 1 |
| `temporal` | 15 | 1 |
| `multi_hop` | 30 | 2 |
| `comparative` | 10 / 15 | 2 / 3 |
| `negative` | 35 | 0 |

So the minimum trajectory for a grounded task is **one search plus D reads**, where D is a number
the data supplies. Trajectory efficiency becomes a ratio against a principled floor rather than
against a guess, and the query-type taxonomy (ADR-018) is doing a third job it was not designed
for.

**5. There is no GPU in CI and no self-hosted runner.** `gh api .../actions/runners` returns
`total_count: 0`. The evaluation harness cannot run on the machine that gates the build. This is
problem 1 and it is the day's real design work.

---

## The five problems Day 8 has to solve

**1. The gate cannot run where the prep plan puts it.**
Research 5: no GPU, no runner. The tempting move is a CI job that skips when there is no model,
which is a green check mark that proves nothing — and this project has already written down that
a test which cannot run in CI is not a gate.
*Resolution:* **the eval runs locally and produces an artifact; CI gates the artifact.** Three
mechanisms, and the middle one is what makes it honest rather than ceremonial:

- **Comparison.** `results/day8/eval.json` is committed. CI compares it against
  `results/day8/baseline.json` and fails on any regression in the mechanical metrics.
- **Staleness.** The artifact records a **content hash of every prompt, worker and system message
  it was produced from**. CI recomputes that hash from the working tree and fails if it differs.
  *A prompt change pushed without a re-run therefore fails the build* — which is the prep plan's
  requirement, satisfied by refusing to believe a stale number rather than by pretending to
  measure one.
- **Replay.** A `pytest` suite drives the whole graph against **recorded** tool results with a
  scripted model, so routing, ceilings, the reroute and the fan-out are exercised in CI with no
  GPU. It catches structural breakage; it cannot catch quality regression, and the plan says so
  rather than letting a green replay imply a good model.

**2. The prep plan's 5% threshold is wrong by roughly fifty times.**
Research 1: zero variance on every quality metric, across processes.
*Resolution:* gate the mechanical metrics **exactly** — any drop in task success, citation
resolution, tool-call recall or abstention accuracy fails the build, and a single regressed task is
visible. Keep a band only for **latency**, where the measured spread is 6.5%, and set it at 25% so
it fires on a real change rather than on thermal drift. The write-up states the threshold *and*
the measurement that justifies it, because "we gate at 5%" and "we gate at zero because we
measured the noise floor at zero" are very different claims about the same system.

**3. "Task success" has to be something a machine decides, or the eval is a vibe.**
*Resolution:* four mechanical outcomes per task, every one derived from the golden set rather than
asserted here — **gold document retrieved** (tool-call recall), **cited and resolvable** (Day 6's
layer 2), **abstained when it should have** (the 35 negatives, and this is the dangerous
direction), and **steps against the minimum** from research 4. The judge measures only the fifth
thing none of those can see — whether the prose is supported by what it cited — and it is reported
in its own column so that a judge outage degrades the report rather than taking down the gate.

**4. The agreement rate needs a human, and this project has been careful about that line.**
`golden/v1` carries `human_reviewed: false` on every item, asserted by a test, because ADR-017
draws an explicit boundary around what a machine-built set can claim.
*Resolution:* the hand-scores are a **separate artifact** — `golden/judge_calibration.jsonl`, its
own provenance, its own README, never merged into `golden/v1` and never used to change an item's
label. Selection is deliberately **biased toward disagreement**: research 3 found the judge
refusing 2 of 8 of the graph's own answers, and twenty examples on which the judge and the
mechanical checks already agree would measure nothing. **This is the one part of Day 8 that cannot
be automated**, it is roughly 45 minutes of reading clauses, and the agreement-rate claim is
blocked on it rather than estimated. If it does not happen, the write-up says the judge is
uncalibrated — which is a weaker claim and an honest one.

**5. p95 over 30 tasks is a single order statistic.**
*Resolution:* report **p50, p95 and max with n printed beside them**, and do not gate p95. Repeating
the run does not tighten it either: research 1 says the outputs are identical, so a re-run
resamples only the server's latency, which is a fact about Ollama rather than about the agent. The
honest cost story is tokens, which are exact.

---

## Phase 0 — Housekeeping · 15 min

- [ ] `gh auth status` — drifts back to `99Tungsten99`; verify `msubash26` and `user.email`
- [ ] `./scripts/stack.sh ps` — 7 services. Today LangFuse on 3000 is the one that matters, and
      `regops-checkpointer-postgres-1` is not needed
- [ ] `nvidia-smi` idle, `ollama ps` empty. **Batch by model for the sixth day**: every agent run
      finishes before `qwen3.8` is loaded for judging. Interleaving is a 17.7 GB swap per item
- [ ] Re-read ADR-017 (the human boundary), ADR-018 (the taxonomy the minimums come from),
      ADR-021 (why abstention is two rates), ADR-028 (no model-supplied identifiers) and Day 7's
      `## Outcome`

## Phase 1 — Thirty tasks with expected outcomes · 75 min

- [ ] `golden/tasks/v1/tasks.jsonl`. **Derived from the golden set, not rewritten from it** — each
      task carries the golden `id` it came from, so a change to `golden/v1` shows up here as a
      failing check rather than as silent drift.
- [ ] The split, proportional to the golden strata and covering every route the supervisor has:
      **12 `factual_lookup` · 6 `multi_hop` · 4 `comparative` · 3 `temporal` · 5 `negative`** = 30,
      plus the **3 coverage tasks** from Day 7 held separately because their expectations are
      hand-written rather than derived.
- [ ] Expected outcome per task, all four mechanical: `gold_doc_ids` (from `gold_spans`),
      `must_cite` (resolvable, non-empty for grounded), `must_abstain` (true for negatives),
      `min_tool_calls` = `1 + len(gold_doc_ids)` (research 4).
- [ ] **No version task.** `diff_versions` is unreachable from the supervisor by design (ADR-028)
      and `regdocs-mcp` ADR-004 records that this corpus has no genuine multi-version document. A
      task nothing can pass measures the task set, not the agent.
- [ ] Tests: every task resolves against `golden/v1`; every `gold_doc_id` exists in the index;
      `min_tool_calls` matches the derivation; the strata sum to 30. No model.

## Phase 2 — The metrics harness · 90 min

- [ ] **Instrument the workers to record each tool call** — name, arguments, result size, error
      flag, elapsed. One change, and Phase 3's spans read the same record. Day 6's `Run.tool_calls`
      is the shape to match so the single agent and the graph stay comparable.
- [ ] `regops_evals.agenteval`, five metrics, each defined in the module docstring before it is
      computed:
      - **task success** — the four mechanical outcomes, and the composite that requires all of
        them, reported both ways
      - **tool-call precision / recall** — against `gold_doc_ids`; recall is *did it read the gold
        document*, precision is *what fraction of what it read was gold*
      - **trajectory efficiency** — `min_tool_calls / actual`, capped at 1.0, with the raw pair
        kept so a 0.5 caused by two calls instead of one is distinguishable from one caused by
        twelve instead of six
      - **cost per task** — tokens (exact) and the ADR-029 dollar conversion (assumed)
      - **latency** — p50, p95, max, with `n` printed next to them (problem 5)
- [ ] Run it over the single agent, the supervisor and plan-and-execute — the same three arms as
      Day 7, so `results/day8/` and `results/day7/day7.md` describe the same systems.
- [ ] `results/day8/eval.json`, and `baseline.json` as a copy of the first clean run.

## Phase 3 — LangFuse, and a trace worth looking at · 45 min

- [ ] `start_as_current_observation(as_type=...)`, **not** v3's `start_as_current_span` —
      research 2, and the old names appear in most published examples.
- [ ] One trace per task; a span per node; a generation per model call carrying
      `usage_details` from Ollama's `prompt_eval_count` / `eval_count`; a span per tool call. The
      fan-out's four branches must appear as siblings — that is the picture that shows Day 7's
      1.00× rather than arguing it.
- [ ] Tracing is **opt-in and non-fatal**: `--trace`, and a LangFuse that is down degrades the run
      to untraced rather than failing it. An eval harness that cannot run without the observability
      stack has made the observability stack a dependency of the measurement.
- [ ] Screenshot the dashboard into `docs/` — the prep plan asks for it and research 2 says the
      read API cannot produce it here.
- [ ] Do **not** push scores to LangFuse as the gate's source. They cannot be read back
      (research 2), and a gate that reads a mutable store is not reproducible anyway.

## Phase 4 — The judge, and the human half · 75 min

- [ ] Rubric: **three axes, scored separately** — `supported` (every claim is in the cited
      clauses), `complete` (the answer covers what the gold spans state), `cited_correctly` (the
      citations are the clauses the support actually came from). One composite hides which of the
      three failed, and they fail for different reasons.
- [ ] Reuse Day 5's judge machinery and `qwen3.8` (ADR-017's rule: the checker is not the writer).
      Research 3 measured 3.6s per call, so this is ~2 minutes for 30 tasks.
- [ ] **`golden/judge_calibration.jsonl` — 20 items hand-scored by the human**, its own README and
      provenance, never merged into `golden/v1`, never used to relabel an item. **Selection is
      biased toward disagreement**: every task the judge and the mechanical checks disagree on
      first, then a stratified fill.
- [ ] Report **agreement rate per axis**, plus the confusion — where the judge is harsh and where
      it is lenient. A single accuracy number over three axes hides that.
- [ ] If the hand-scoring does not happen, the write-up says **"the judge is uncalibrated"** and
      the agreement claim is absent. It is not estimated, and no number is quoted for it.

## Phase 5 — The gate, and making it able to fail · 75 min

- [ ] `regops-evals gate-agent`: reads `eval.json` and `baseline.json`, fails on **any** regression
      in the mechanical metrics (problem 2), and on a latency p50 regression beyond **25%**.
- [ ] **The staleness hash.** `eval.json` records a hash over every prompt, worker and system
      message that produced it. CI recomputes it and fails on a mismatch. This is the mechanism
      that turns the prep plan's requirement into something real: *a prompt change pushed without a
      re-run fails the build.*
- [ ] The **replay suite** — the graph over recorded tool results with a scripted model, in
      `pytest`, no GPU. It gates structure, not quality, and the docstring says so.
- [ ] CI: a `agent-eval` job after `test` running the gate and the replay suite. Green on both
      repos.
- [ ] **Prove the gate can fail.** Degrade one prompt deliberately, re-run, watch the gate reject
      it, then revert. A gate never observed failing is a gate nobody knows the polarity of, and
      the transcript of that run goes in the write-up.

## Phase 6 — Tests and write-up · 60 min

- [ ] ADRs: what "task success" means and why it is four outcomes; why the gate is exact rather
      than 5%; where the eval runs and why CI gates an artifact; the judge rubric and its
      calibration boundary.
- [ ] `results/day8/day8.md`, **generated** — Day 6 Phase 1's lesson, applied for the third day.
- [ ] `README.md` — the eval section, the gate, the trace screenshot; `agents/README.md`;
      `golden/tasks/v1/README.md`; `golden/judge_calibration/README.md`.
- [ ] `/home/subash/regops/initial-setup.md` — Days 0–8, and the new gotchas (LangFuse v4's
      renamed span API and its read-only 404s; batching the judge after the agent).
- [ ] `## Outcome` appended here. Green CI.

---

## Deliverables

30 end-to-end tasks with machine-checkable expectations derived from the golden set · five metrics
over three architectures · LangFuse traces with the fan-out visible as siblings, and a screenshot ·
a three-axis judge with a stated agreement rate against 20 hand-scored examples · **a CI gate that
fails on a stale artifact and on any mechanical regression** · a demonstration of the gate
rejecting a deliberately degraded prompt · 4 ADRs · green CI.

**Done when** a prompt is changed, pushed without re-running the eval, and **CI fails** — and when
changing it, re-running, and pushing tells you by how much you made it worse.

## Decisions I would want a steer on

1. **Do the 20 hand-scores happen?**
   *Recommendation: yes, and budget 45 minutes for them.* It is the only part of Day 8 a machine
   cannot do, and "our judge agrees with me 17 of 20 times, and here is where it does not" is
   worth more in an interview than any other sentence this day can produce. The alternative is
   honest and much weaker — the write-up says the judge is uncalibrated. **This is a decision for
   now**, because Phase 4's selection step depends on it and the answer changes what Phase 6 can
   claim.
2. **Does the gate run against all three architectures, or only the supervisor?**
   *Recommendation: all three, gate only the supervisor.* Measuring all three keeps Day 7's
   comparison alive as a regression surface for free; gating all three triples the ways a build can
   fail for reasons nobody is working on. The single agent and plan-and-execute get reported and
   not enforced.
3. **Does `results/day8/eval.json` get committed?**
   *Recommendation: yes, and it is the point.* A gate needs something to compare against, CI cannot
   produce it, and a committed artifact with a staleness hash is auditable in a way a cached
   workflow artifact is not. Cost: a re-run produces a diff in every metric line, which makes some
   commits noisy. That noise is the eval doing its job.
4. **Is Day 7's fan-out width raised from 4 before the coverage tasks are scored?**
   *Recommendation: no — measure it at 4 first.* Day 7 left it at 4 with the reason recorded.
   Letting the eval show it as a recall ceiling is better evidence than quietly widening it, and
   the fix (if it is one) then has a number attached.

## Risks

1. **The gate is ceremonial — green because nothing it checks can move.** This is the failure that
   would waste the day. Mitigated by Phase 5's last step: deliberately degrade a prompt and watch
   the gate reject it, with the transcript in the write-up. A gate never observed failing has
   unknown polarity.
2. **The staleness hash is too sensitive and every commit turns red.** Likely on the first
   attempt — a docstring edit should not invalidate an eval. Mitigated by hashing the **prompt
   strings and system messages specifically**, not whole files, and by a test that asserts a
   docstring change does not move the hash while a prompt change does.
3. **The hand-scoring slips and the agreement rate is quietly estimated.** The mitigation is
   written into Phase 4: if it does not happen, the claim is absent rather than approximated.
   ADR-017's boundary held for four days under pressure; it holds here.
4. **Thirty tasks is not enough for the per-stratum numbers to mean anything** — five negatives
   support a false-answer rate with a very wide interval. Mitigated by reporting counts rather than
   only rates (Day 6 Phase 1's lesson about `unflagged_122`), and by gating the composite, which is
   over all 30.
5. **Instrumenting every tool call changes the thing being measured.** Research 2 measured 0.8 ms
   for four spans against a 5.9s run, so the risk is bookkeeping in the hot path rather than
   tracing. Mitigated by recording into a list and serialising once at the end, and by the
   determinism check in research 1 being re-run afterwards — **if instrumentation moved a single
   answer, it changed behaviour, and that is a bug rather than a cost**.

**Descope order if behind:** the plan-and-execute arm in Phase 2 (report the other two) → the
LangFuse screenshot and Phase 3's span tree, keeping the tool-call recording that Phase 2 needs →
the third judge axis (`complete`), keeping `supported` and `cited_correctly`. **Never cut:** the
staleness hash, the proof that the gate can fail, and the honesty rule about the uncalibrated
judge. Without the first two the gate is decoration; without the third the day's headline number is
one nobody measured.
