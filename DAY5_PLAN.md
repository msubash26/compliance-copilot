# Day 5 — Run the retrieval benchmark

**Repo:** `compliance-copilot` (members `regops-retrieval`, `regops-evals`) · **Date:** 2026-09-05
**Budget:** ~6h, of which ~1.5h is unattended GPU time

> The prep plan's bar: *"one results table showing that different architectures win on different
> query types. That finding — 'reranking bought us 11 points of nDCG on multi-hop and nothing on
> lookup, so we route by query class' — is a genuinely senior thing to say."*

---

## Context

Day 4 delivered the instrument this day reads: 150 golden items over the Day 3 index, stratified
across five query types, every gold span pinned by `doc_id` + `section_path` + `span_sha256`, and
a published baseline showing the set has headroom (BM25 hit@5 0.670, dense 0.609 — against 92%
for a naive set). Day 5 spends that headroom.

### Carried forward from Days 1–4

- **`regops-evals gate` is already half this harness.** It defines BM25 and dense once, rolls
  chunks up to the parent clause, and computes hit@k / full@k per query type. Day 5 extends it
  rather than starting a second definition of "search" — if the baseline row and the sweep rows
  disagree about what dense retrieval *is*, the whole table is uninterpretable.
- **28 of 150 items are flagged**, machine-verified but not human-reviewed. That is a
  measurement caveat, not a blocker — see problem 4.
- **Both embedding arms already exist** (`nomic-embed-text` and `…+ctx`, 44,180 vectors over the
  same chunks), so contextual on/off is a config switch and not a re-embedding job. This is what
  ADR-015's two hours bought.
- **Ollama serialises.** Generation and judging use different models; batch by model or pay a
  17.7 GB swap per item (the rule that cost Day 4 a rewrite of `verify`).

### Research completed before planning (ADR-002's rule)

Everything below was measured today, against the real index and the real golden set.

**1. The headline finding is already visible with three arms and no reranker.** Over the 115
grounded items:

| arm | | comparative | factual_lookup | multi_hop | temporal | **overall** |
|---|---|---|---|---|---|---|
| bm25 | hit@5 / MRR | 0.560 / 0.376 | 0.733 / 0.541 | **0.800 / 0.594** | 0.400 / 0.308 | 0.670 / 0.488 |
| dense | hit@5 / MRR | 0.560 / 0.401 | 0.733 / **0.628** | 0.600 / 0.353 | 0.333 / 0.245 | 0.609 / 0.457 |
| hybrid RRF | hit@5 / MRR | **0.600 / 0.409** | **0.800** / 0.623 | 0.733 / 0.548 | 0.400 / 0.349 | **0.687 / 0.521** |

Three things worth saying out loud before any tuning:

- **BM25 beats dense on `multi_hop` by 24 MRR points** (0.594 vs 0.353). Cross-references are
  citations — literal strings — and that is lexical territory.
- **Dense beats BM25 on `factual_lookup`** (MRR 0.628 vs 0.541), which is the paraphrase case.
- **RRF wins overall and *loses* on `multi_hop`** — 0.733 hit@5 against pure BM25's 0.800.
  Fusing a weaker arm in costs 7 points where the stronger arm was already right. *This is the
  routing argument, and it exists in the data before Day 5 starts.*

**2. Contextual retrieval is a real win, concentrated where it was needed.** Same queries, dense
arm only, plain vectors against context-prepended ones:

| | comparative | factual_lookup | multi_hop | temporal | overall |
|---|---|---|---|---|---|
| dense MRR | 0.374 | **0.627** | 0.353 | 0.246 | 0.451 |
| dense+ctx MRR | **0.451** | 0.613 | **0.516** | **0.345** | **0.518** |
| Δ | +7.7 | −1.4 | **+16.3** | +9.9 | +6.7 |

`multi_hop` gains 16 MRR points; `factual_lookup` loses 1. Another per-query-type divergence, and
independent evidence that ADR-015's design (locator names the instrument and clause) helps
exactly the questions that must cross documents.

**3. The reranker is cheap and needs no new heavy dependency.** `BAAI/bge-reranker-v2-m3`
measured on the 3090: 568M params, **1.33 GB VRAM in fp16**, 7.2s to load from cache, and
**138ms p50 / 451ms p95 to score 20 real clauses** (median clause 820 chars). It runs on the
`transformers` 5.8.1 + torch 2.13.0+cu130 already installed for Docling — `AutoModelForSequence-
Classification`, no `sentence-transformers`, no `FlagEmbedding`.

Retrieval latency, for the p50/p95 column: **BM25 22ms**, **dense 100ms** (including the Ollama
embed call), rerank +138ms. A full hybrid+rerank query is ~260ms p50. The retrieval sweep is not
where the day's time goes.

**4. Generation metrics cost ~30× retrieval metrics, and that shapes the whole day.** Answer
generation on `qwen3.5:9b` with five clauses of context: **6.76s p50, 10.65s max** →
**16.9 min per config per 150 queries**. Seven configs would be ~2h of generation *before*
judging. Recall, nDCG, MRR and latency for all 7×150 cost about **4 minutes** in total.

**5. Parent-child on/off is not a recall axis.** Rolling chunks up to their parent clause changes
the top-5 on only **9 of 40 queries**, by a mean of **0.25 slots of 5**. Where it does bite is
context size — top-5 assembled as clauses vs as chunks:

| | median | p90 | max |
|---|---|---|---|
| parent (clause) | 5,848 | **46,417** | **82,184** |
| child (chunk) | 3,156 | 4,516 | 5,916 |

1.85× at the median but **10× at p90**, because a MAS clause can run to 127,564 characters. So
this axis belongs in the groundedness / latency / cost columns, and a near-flat recall row is the
expected result rather than a bug.

**6. Dense rank order is not reproducible, and that would have quietly corrupted the table.**
Six identical dense queries returned six orderings, diverging at rank 18: there is one exact
distance tie in the top-20, and DuckDB's parallel aggregation does not break ties
deterministically. `hit@k` is a set test and survives; **MRR and nDCG read the order and do
not**. BM25 was stable across the same test. Fix before any measurement: a deterministic
secondary sort key (`ORDER BY d, section_uid`), plus embeddings computed once and cached — they
*are* bit-identical across calls, so caching costs nothing and removes the confound.

**7. No AWS credentials exist on this box** (`~/.aws` absent, no `AWS_*` in the environment), so
"cost per query: local GPU-seconds vs Bedrock dollars" cannot be a measurement on both sides
today. See decision 2.

**8. The Quadrant harness cannot be extended here.** The prep plan says *"extend the Quadrant
harness rather than rebuilding it"*. It is at `~/NorthStar/Capstone/quadrant` — a workspace
deliberately isolated from this one (different git identity, different GitHub account) — and
`quadrant/evals/retrieval.py` is 163 lines computing hit@5 and MRR@10, 2 of the 8 metrics Day 5
needs, against a different store. The instruction's *intent* is "do not build a second eval
harness", and the harness this project already owns is `regops-evals`. Extending that satisfies
the intent; copying code across the workspace boundary would violate ADR-001's separation for a
133-line saving.

---

## The four problems Day 5 has to solve

**1. Seven configurations, one honest definition of "config".**
"dense · BM25 · hybrid RRF · hybrid+rerank · contextual on/off · parent-child on/off · query
decomposition on/off" is not seven things if read as a factorial — it is 4 × 2 × 2 × 2 = 32.
*Resolution:* a **4-rung ladder** plus **3 ablations against the best rung**, which is seven rows
and is the only reading in which an ablation means anything (an ablation needs a fixed reference).
The ladder is C1 bm25 → C2 dense → C3 hybrid RRF → C4 hybrid+rerank, all with contextual on and
parent-child on. C5/C6/C7 turn one switch off C4 each. Every config is a declared object in code,
not a flag combination assembled at the call site, so the table's rows and the code's objects are
the same list.

**2. Generation metrics cannot be afforded on all seven, and pretending otherwise breaks the day.**
At 6.76s per answer, seven configs of 150 is ~2h of generation plus judging.
*Resolution:* **retrieval metrics (recall@5/@20, nDCG@10, MRR, latency) on all 7 × 150** — 4
minutes, complete, no sampling. **Generation metrics (groundedness, abstention) on the 4 ladder
configs × 150** — 68 min, because the ladder is where the architecture question lives. The three
ablations get retrieval metrics and a stated "not measured" in the generation columns. An empty
cell that says why is better than a cell filled from 20 samples and quoted as if it were 150.

**3. Abstention needs the negatives to be *scored*, not just retrieved.**
Recall is undefined for the 35 negatives — there is no gold span to find. They are 23% of the set
and the reason the set is interesting.
*Resolution:* abstention accuracy is measured as a 2×2 over the whole 150: did the system abstain,
and should it have. That gives false-abstention rate on the 115 grounded items (over-caution,
which makes a compliance tool useless) alongside false-answer rate on the 35 negatives (confident
fabrication, which makes it dangerous). Reporting only the second would flatter any system that
abstains constantly.

**4. The instrument has known defects and the results must carry them.**
28 of 150 items are flagged, and `comparative` is the least-verified type at 12 of 25.
*Resolution:* the headline table is computed on all 150; every config is additionally computed on
the 122 unflagged items, and both are published. If a conclusion flips between them, that
conclusion belongs to the golden set's noise rather than to the retriever, and it gets said. This
is cheap — the sweep is 4 minutes — and it is the difference between a benchmark and a number.

---

## Phase 0 — Housekeeping · 15 min

- [x] `gh auth status` — drifts back to `99Tungsten99`
- [x] `./scripts/stack.sh ps` — 7 services; LangFuse needed for sweep traces
- [x] `uv run regops-evals verify --index index/regdocs.duckdb --no-judge` — 150/150 spans must
      still resolve before anything is measured against them
- [x] Confirm `nvidia-smi` shows the 3090 idle: the reranker wants 1.33 GB alongside Ollama
- [x] Re-read ADR-014 (clause is the parent), ADR-015 (contextual), ADR-019 (how difficulty was
      engineered — the sweep is measuring against a set that was *built* to separate these arms)

## Phase 1 — `regops-retrieval`, and one definition of search · 75 min

- [x] Move the retrieval primitives out of `regops_evals.corpus` into `regops_retrieval`, and have
      `corpus.py` import them back. The eval package must not own the thing it evaluates, and
      Day 6's agent needs the same retrievers without importing an eval harness.
- [x] **Fix determinism first** (research 6): deterministic tie-break on every ranked query, and
      a `QuestionVectors` cache computed once per run. Assert it in a test — a benchmark whose
      ranking is not reproducible cannot support a 2-point claim.
- [x] `Retriever` protocol returning `list[Scored]` — `(section_uid, score, rank)` — so RRF and
      rerank compose over any arm rather than being special cases.
- [x] `bm25`, `dense(model=...)`, `rrf(*arms, k=60)`, `rerank(bge-reranker-v2-m3, top_n)`.
      RRF's `k=60` is the published default and gets stated as an unexamined constant, not
      presented as tuned.
- [x] `assemble_context(hits, mode="parent"|"child")` with a **hard character budget**. Research
      5 found a p90 of 46K chars and a max of 82K on the parent path; without a cap, the parent
      arm will silently blow the generator's context on the tail and score 0 for a reason that
      has nothing to do with retrieval. Truncation is recorded per query, not hidden.
- [x] `decompose(question)` — one LLM call, cached to disk by question hash so the 150 calls are
      paid once and every config that needs them reuses the same decompositions.

## Phase 2 — The metrics, and the sweep harness · 60 min

- [x] `regops_evals.metrics`: `recall@k` (any gold span), `full@k` (all of them), `nDCG@10`,
      `MRR`. Pure functions over `(ranked_uids, gold_uids)`, tested against hand-computed values —
      a metric bug is invisible in a results table and invalidates everything above it.
- [x] **Record what nDCG can and cannot say here.** Gold labels are binary, and 45 of 115 items
      have exactly one gold span — for those, nDCG@10 is a monotone function of the gold rank and
      carries the same information as MRR. It is genuinely informative only on the multi-span
      types (`multi_hop`, `comparative`). Report both, say this once, and do not narrate a
      single-span nDCG movement as if it were independent evidence.
- [x] `bench.py`: run a named config over the golden set, emit per-item rows (not just
      aggregates) to `results/day5/raw/<config>.jsonl` so any table cell can be traced back to
      the queries that produced it.
- [x] Latency captured per query per config, p50 and p95, with the embed call inside the
      measurement — it is 78% of the dense arm's 100ms and excluding it would flatter dense.
- [x] `regops-evals bench --configs all --golden golden/v1/golden.jsonl` and
      `--report results/day5/retrieval.md`.

## Phase 3 — Run the retrieval sweep · 30 min

- [x] All 7 configs × 150 items. Expected ~4 minutes of compute.
- [x] Emit the headline table: **config × query type × {recall@5, recall@20, nDCG@10, MRR, p50,
      p95}**.
- [x] Emit the same table over the 122 unflagged items (problem 4). Diff the conclusions, not
      just the numbers.
- [x] Sanity gate before trusting any of it: C1's row must reproduce Day 4's published baseline
      (`golden/v1/saturation.json`: bm25 hit@5 0.670, dense 0.609). A mismatch means the harness
      changed the definition of search, and everything downstream is void until it is explained.

## Phase 4 — Groundedness and abstention · 90 min (mostly unattended)

- [x] Generate answers for the **4 ladder configs × 150** with `qwen3.5:9b`, from assembled
      context, with an explicit "if the excerpts do not answer it, say so" instruction and a
      required citation format. ~68 min; run it as one batch while Phase 5 is written.
- [x] **Then** load `qwen3.8` and judge all 600 in one pass — groundedness (is every claim
      supported by a cited excerpt) on the 115 grounded items, and abstention on all 150. Batch
      by model: the Day 4 rule, for the Day 4 reason.
- [x] Abstention as a 2×2, reported as **two** rates: false-answer on negatives (dangerous) and
      false-abstention on grounded items (useless). A single "accuracy" number hides which
      failure a system has.
- [x] Cost per query: **measure** GPU-seconds and token counts on the local path. **Compute** the
      Bedrock figure from published per-token rates against the same token counts, and label the
      column *estimated, not measured* (research 7, decision 2).

## Phase 5 — Tests · 45 min

- [x] Metric unit tests against hand-computed values, including the degenerate cases that produce
      plausible-looking wrong numbers: no gold span retrieved, all retrieved, gold at rank 1,
      fewer results than k, duplicate uids in a ranking.
- [x] A determinism test: the same config over the same items twice produces byte-identical
      rankings (research 6).
- [x] An RRF test on hand-built rankings where the fused order is worked out by hand — RRF is
      four lines and every one of them is easy to get subtly wrong.
- [x] A reranker contract test that runs without the model: a stub scorer, asserting the pipeline
      reorders by score and truncates to `top_n`. The real model is exercised once, marked `slow`,
      skipped in CI.
- [x] Context-budget test: a 127K-character clause must be truncated to the budget, and the
      truncation must be *recorded*.

## Phase 6 — Write-up · 60 min

- [x] **`results/day5/retrieval.md`** — the results table, the per-query-type winners, and the
      routing rule they imply, with every claim carrying its n.
- [x] **ADR-020** — the seven configurations as a ladder plus ablations, and why a factorial
      reading was rejected; the constants left untuned and admitted (RRF `k=60`, rerank `top_n`).
- [x] **ADR-021** — retrieval metrics on all seven configs, generation metrics on four; what an
      empty cell means; why abstention is two rates and not one.
- [x] **ADR-022** — the determinism fix, and what it invalidated: any ranking metric measured
      before it. Worth its own ADR because "our benchmark's ranking was nondeterministic" is the
      kind of thing that silently survives into a published table.
- [x] `retrieval/README.md`, root `README.md`, `initial-setup.md`; commit, push, CI green.

---

## Deliverables

`regops-retrieval` with four composable arms and a reranker · a metrics module with unit-tested
implementations · `regops-evals bench` · `results/day5/retrieval.md` carrying one table of
7 configs × 5 query types × 8 metrics, plus the 122-item sensitivity run · per-item raw rows for
every cell · 3 ADRs · green CI.

**Done when** the table supports a sentence of the prep plan's shape, with numbers attached.
On today's evidence it is likely to be about `multi_hop` and lexical matching, but the point is
that the sentence is *read off the table*, not decided now.

## Decisions I would want a steer on

1. **Generation metrics on 4 configs × 150, or 7 configs × ~75?** *Recommendation: 4 × 150.*
   Per-query-type cells are already thin (15 temporal items); halving the set makes every
   generation cell an anecdote, whereas dropping the three ablations loses only the least
   interesting comparisons. The ablations keep full retrieval metrics either way.
2. **Bedrock: real calls, or a computed estimate?** *Recommendation: computed estimate, clearly
   labelled.* It needs credentials and spend, ADR-005 already positions hosted APIs as a parity
   baseline rather than a dependency, and a per-token calculation from published rates is
   honest and free. Say "estimated from published rates" in the column header, not in a footnote.
   If real parity numbers matter for the portfolio, that is a decision to take now, because it
   needs an account before Phase 4.
3. **Does `query decomposition` get evaluated on all query types?** *Recommendation: run it on
   all 150 but report it per type.* Decomposing "what must a bank do when X" is pure overhead,
   and the expected finding — helps `multi_hop` and `comparative`, costs latency everywhere else —
   is itself a routing result. Running it only where it is expected to help would assume the
   conclusion.

## Risks

1. **The reranker underperforms and the table is boring.** Possible: the set was built so that
   entity disambiguation matters, which is reranker-shaped, but a cross-encoder trained on web
   passages may not transfer to Singaporean regulatory prose. Mitigated by the fact that a
   negative result is publishable here — *"a general-domain reranker bought nothing on regulatory
   text"* is a finding, provided the harness is trustworthy enough to support it, which is what
   Phase 5 is for.
2. **Differences fall inside the golden set's noise.** 15 temporal items means one item is 6.7
   points. Mitigated by the 122-item sensitivity run, by reporting n in every cell, and by
   refusing to narrate sub-2-point movements on the small cells.
3. **Parent-mode context blows the generator on the tail.** p90 is 46K characters. Mitigated by
   the hard budget in Phase 1 and by recording truncation as a measured quantity rather than
   letting it appear as a mysterious groundedness drop.
4. **The sweep silently redefines search and disagrees with Day 4.** Mitigated by the Phase 3
   sanity gate against the published baseline, run before any other number is believed.

**Descope order if behind:** query decomposition (C7) → the 122-item sensitivity run →
groundedness on C1/C2, keeping C3/C4. **Never cut** the determinism fix, the metric unit tests,
or the Phase 3 baseline gate: the first two are what make the numbers mean anything, and the
third is what proves they are the *same* numbers Day 4 published.

---

## Outcome

All six phases complete. 177 tests green (2 `slow`, skipped in CI), ruff clean, CI green on
`c414858`. The sweep is 7 configurations × 150 items in **8 minutes**, generation is 4 × 150 in
**21 minutes**, judging 330 answers in **17 minutes**. The Phase 3 gate passes: C1 reproduces
Day 4's published baseline to three places on all three metrics.

The day's sentence, read off the table rather than decided in advance:

> **The cross-encoder bought 32 MRR points on `temporal` (n=15) and 4 on `comparative` (n=25) —
> the same reranker, the same 400ms, an eightfold difference in what it buys. So rerank
> everything, and budget it against the query class rather than the average.**

### What the plan got right

The four problems were the right four, and three of them changed the artifact rather than just
the prose. The **ladder-plus-ablations** reading is what makes C5/C6/C7 interpretable at all; a
32-cell factorial over 115 items would have produced a table nobody could read and no ablation
anyone could trust. **Problem 4's sensitivity run earned itself outright** — the parent-child
switch reads *flat* on 150 items and *hurts* on the 122 unflagged, which is exactly the
"conclusion that belongs to the golden set rather than the retriever" the plan was written to
catch, and it is now a caveat on a recommendation instead of a confident claim. And the **Phase 3
sanity gate** did its job by passing: it is the only reason the sweep's C1 row can be quoted next
to Day 4's without hand-waving.

Research 6 deserves particular credit. *"Fix determinism first"* and *"never cut the determinism
fix"* were correct, and the day would have shipped a corrupted table without them.

**All three open decisions were taken as recommended** — generation on 4 configurations × 150
rather than 7 × 75, a labelled Bedrock estimate rather than real calls, and decomposition run
across all 150 items and reported per type. The third is the one that mattered: restricting C7 to
the types where it was expected to help would have assumed the conclusion, and the measured answer
contradicted the expectation. **Nothing was descoped** — the plan's cut list (C7, then the
sensitivity run, then groundedness on C1/C2) went unused, mostly because generation came in 3.5×
under budget.

### Where the plan was wrong, and what replaced it

- **Research 6 named the wrong fix, and the plan's own instinct is what caught it.** The
  prescription was "a deterministic secondary sort key (`ORDER BY d, section_uid`)". That was
  applied, tested, and *insufficient*: BM25 sums term contributions in a parallel reduction, so
  the same query returns scores differing in their last bit, and an exact-equality tie-break
  never fires on two scores 1 ULP apart. **10 of 40 real questions reordered their top-20
  between runs**, and three consecutive full sweeps returned C1 MRR of 0.490, 0.495 and 0.486 for
  a pure-BM25 configuration over a fixed index. Ordering on a rounded score fixes it — two
  independent sweeps now produce byte-identical rankings on all 150 items. See ADR-022.
- **The determinism test passed through all of that.** A five-clause fixture with hand-written
  orthogonal vectors has no near-ties for floating-point jitter to disturb, so the test could not
  have failed however broken the ordering was. **A determinism test over clean synthetic data
  proves nothing about determinism.** The second bug was found by running the benchmark three
  times and diffing the headline numbers — which no unit suite can do for you.
- **Phase 0's own pre-flight command was destructive.** `verify --index … --no-judge` passed its
  check (150/150 spans resolved) and then rewrote `golden.jsonl`, resetting all 28 flagged items
  to `unverified`. Its summary printed `"flagged": 0` and read like a clean bill of health. The
  122/28 split the entire day is keyed to would silently have become 150/0. Restored from git,
  fixed to merge rather than rebuild, two regression tests, ADR-023.
- **Research 4's generation cost was 3.5× pessimistic.** Budgeted at 6.76s per answer from a cold
  probe; the batch ran at **~1.9s**. Seven configurations of generation would have been ~35
  minutes, not two hours. The decision to measure four went the same way regardless — the binding
  constraint is that the three ablations answer *retrieval* questions the retrieval columns
  already answer completely — but the stated reason was the wrong one. ADR-021 records both.
- **Research 3's "the sweep is 4 minutes" was 8.** Not the reranker (75s for 150 queries, as
  predicted) — the missing item was 165s of one-off query decomposition and 260s for C7, which
  runs the reranker once per sub-question.
- **Risk 1 was inverted.** The plan hedged that *"the reranker underperforms and the table is
  boring"* and pre-committed to publishing a negative result. The cross-encoder turned out to be
  the single largest lever in the sweep (+0.106 MRR overall), and the boring row was **contextual
  retrieval** — worth +6.7 MRR on the dense arm alone, worth **+0.009** once a cross-encoder sits
  on top of it. Two mechanisms competing for the same ranking error, and the ablation is the only
  reason that is visible: research 2 measured contextual retrieval against the *dense arm* and
  would have over-credited it.
- **The predicted headline was the wrong headline.** The plan guessed *"likely to be about
  `multi_hop` and lexical matching"*. It is about **`temporal` and reranking** — `multi_hop` is
  the second-largest reranker gain, not the first. The plan's own instruction is what saved this:
  *"the point is that the sentence is read off the table, not decided now."*
- **Query decomposition was expected to be a wash, not a loss.** Decision 3 predicted "helps
  `multi_hop` and `comparative`, costs latency everywhere else". Measured: it **loses on all four
  query types**, by 13–16 MRR points, at 3.2× the p50 latency. Running it on all 150 rather than
  only where it was expected to help is the only reason that is a result instead of an assumption.

### Findings worth carrying forward

- **The routing table is the switch table, not the configuration table.** Comparing the top two
  *configurations* per query type says nothing here — C4, C5 and C6 sit within a point of each
  other, so "no configuration clears the next by one item's worth" comes out true and useless in
  every cell. What a routing rule is read off is the effect of moving **one switch**, per type.
- **Decomposition fails by dilution, not by mis-retrieval.** Over the 100 items both C4 and C7
  retrieve at all, the first gold span is **demoted on 36, unchanged on 51, promoted on 13**, with
  9 more falling out of the top 20 entirely. RRF weights every sub-query equally, so the original
  question ends up with one vote in three. The per-item rows are what made this diagnosable at
  all — an aggregate would only have shown the loss.
- **Groundedness is gameable and must never be quoted alone.** C2 has the *highest* groundedness
  (0.880) on the *fewest* answers (75): refusing the hard questions leaves an easier set to be
  grounded on. The **useful-answer rate** — grounded answers over all 115 grounded items — cannot
  be traded against caution, and it is the only generation column monotone down the ladder.
- **Part of the false-abstention column belongs to the golden set.** Every configuration refuses
  *flagged* items at up to **3.1×** the rate it refuses unflagged ones, and the gap widens as
  retrieval improves. Some are genuinely unanswerable as written — `gs-0005` asks *"when does this
  notice become effective"* with no referent for *this notice*.
- **The negative set was verified through a 700-character window.** `gs-0118` is mislabelled:
  Notice 653 *does* prescribe an NSFR Disclosure Template, the clause is 12,689 characters, and
  the requirement begins at character 3,697. Day 4's verifier had that clause at **rank 3** and
  still passed the item at confidence 1.0, because it was shown the first 700 characters. A silent
  truncation is a judge being lied to about its evidence — which is precisely why Day 5's own
  `assemble_context` records `truncated_excerpts` and `dropped_excerpts` per query. C4's
  false-answer rate is therefore **0.029 as measured, 0.000 excluding `gs-0118`**, published both
  ways. See ADR-024.
- **Reranking a pool it does not extend cannot change recall at the pool depth.** All seven
  configurations rank the same 50 candidates, so C4's `hit@20` moving by zero against C3 is
  arithmetic, not a null result. Worth stating before someone reads it as one.
- **Batch by model, again.** C7 decomposes with `qwen3.5:9b` and embeds with `nomic-embed-text`;
  interleaved, that is a 17.7 GB swap per query. Every decomposition is taken first, then every
  query vector, then the sweep touches no model that is not already warm. Third day running that
  this rule has had to be applied somewhere new.
- **Three workspace members now ship a `tests/` directory** and pytest's default import mode
  resolves test modules by basename. `ingest/tests/` and `evals/tests/` already own both spellings
  of `conftest`, so `retrieval/tests/` keeps its fixtures in `fixtures_retrieval.py` and registers
  them with `pytest_plugins`.

### Deliberately deferred

**Re-verifying the golden set with the wider excerpt window is first work on Day 6.** It will
change which items are flagged, and the 122/28 split is what the sensitivity run, the abstention
split and every `n=` in the write-up are keyed to. Re-verifying and then re-sweeping is a Day 4
change with a Day 5 cascade; doing it in the same commit as the benchmark would mean publishing a
table whose instrument moved underneath it. `gs-0118` is named, not edited — under ADR-017 a flag
comes from the checker, never from a hand edit.

### End-to-end proof

`regops-evals bench --configs all` run twice, independently, produces **byte-identical rankings on
all 150 items** for every configuration, and C1's row lands on Day 4's published `hit@5` 0.670,
`hit@20` 0.870 and `full@5` 0.417 to three decimal places — with the gate exiting non-zero if it
ever stops doing so. Every cell of `results/day5/retrieval.md` is an average over per-item rows in
`results/day5/raw/`, so any number in the table can be opened rather than argued about.
