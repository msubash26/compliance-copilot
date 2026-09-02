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

- [ ] `gh auth status` — drifts back to `99Tungsten99`
- [ ] `./scripts/stack.sh ps` — 7 services; LangFuse needed for sweep traces
- [ ] `uv run regops-evals verify --index index/regdocs.duckdb --no-judge` — 150/150 spans must
      still resolve before anything is measured against them
- [ ] Confirm `nvidia-smi` shows the 3090 idle: the reranker wants 1.33 GB alongside Ollama
- [ ] Re-read ADR-014 (clause is the parent), ADR-015 (contextual), ADR-019 (how difficulty was
      engineered — the sweep is measuring against a set that was *built* to separate these arms)

## Phase 1 — `regops-retrieval`, and one definition of search · 75 min

- [ ] Move the retrieval primitives out of `regops_evals.corpus` into `regops_retrieval`, and have
      `corpus.py` import them back. The eval package must not own the thing it evaluates, and
      Day 6's agent needs the same retrievers without importing an eval harness.
- [ ] **Fix determinism first** (research 6): deterministic tie-break on every ranked query, and
      a `QuestionVectors` cache computed once per run. Assert it in a test — a benchmark whose
      ranking is not reproducible cannot support a 2-point claim.
- [ ] `Retriever` protocol returning `list[Scored]` — `(section_uid, score, rank)` — so RRF and
      rerank compose over any arm rather than being special cases.
- [ ] `bm25`, `dense(model=...)`, `rrf(*arms, k=60)`, `rerank(bge-reranker-v2-m3, top_n)`.
      RRF's `k=60` is the published default and gets stated as an unexamined constant, not
      presented as tuned.
- [ ] `assemble_context(hits, mode="parent"|"child")` with a **hard character budget**. Research
      5 found a p90 of 46K chars and a max of 82K on the parent path; without a cap, the parent
      arm will silently blow the generator's context on the tail and score 0 for a reason that
      has nothing to do with retrieval. Truncation is recorded per query, not hidden.
- [ ] `decompose(question)` — one LLM call, cached to disk by question hash so the 150 calls are
      paid once and every config that needs them reuses the same decompositions.

## Phase 2 — The metrics, and the sweep harness · 60 min

- [ ] `regops_evals.metrics`: `recall@k` (any gold span), `full@k` (all of them), `nDCG@10`,
      `MRR`. Pure functions over `(ranked_uids, gold_uids)`, tested against hand-computed values —
      a metric bug is invisible in a results table and invalidates everything above it.
- [ ] **Record what nDCG can and cannot say here.** Gold labels are binary, and 45 of 115 items
      have exactly one gold span — for those, nDCG@10 is a monotone function of the gold rank and
      carries the same information as MRR. It is genuinely informative only on the multi-span
      types (`multi_hop`, `comparative`). Report both, say this once, and do not narrate a
      single-span nDCG movement as if it were independent evidence.
- [ ] `bench.py`: run a named config over the golden set, emit per-item rows (not just
      aggregates) to `results/day5/raw/<config>.jsonl` so any table cell can be traced back to
      the queries that produced it.
- [ ] Latency captured per query per config, p50 and p95, with the embed call inside the
      measurement — it is 78% of the dense arm's 100ms and excluding it would flatter dense.
- [ ] `regops-evals bench --configs all --golden golden/v1/golden.jsonl` and
      `--report results/day5/retrieval.md`.

## Phase 3 — Run the retrieval sweep · 30 min

- [ ] All 7 configs × 150 items. Expected ~4 minutes of compute.
- [ ] Emit the headline table: **config × query type × {recall@5, recall@20, nDCG@10, MRR, p50,
      p95}**.
- [ ] Emit the same table over the 122 unflagged items (problem 4). Diff the conclusions, not
      just the numbers.
- [ ] Sanity gate before trusting any of it: C1's row must reproduce Day 4's published baseline
      (`golden/v1/saturation.json`: bm25 hit@5 0.670, dense 0.609). A mismatch means the harness
      changed the definition of search, and everything downstream is void until it is explained.

## Phase 4 — Groundedness and abstention · 90 min (mostly unattended)

- [ ] Generate answers for the **4 ladder configs × 150** with `qwen3.5:9b`, from assembled
      context, with an explicit "if the excerpts do not answer it, say so" instruction and a
      required citation format. ~68 min; run it as one batch while Phase 5 is written.
- [ ] **Then** load `qwen3.8` and judge all 600 in one pass — groundedness (is every claim
      supported by a cited excerpt) on the 115 grounded items, and abstention on all 150. Batch
      by model: the Day 4 rule, for the Day 4 reason.
- [ ] Abstention as a 2×2, reported as **two** rates: false-answer on negatives (dangerous) and
      false-abstention on grounded items (useless). A single "accuracy" number hides which
      failure a system has.
- [ ] Cost per query: **measure** GPU-seconds and token counts on the local path. **Compute** the
      Bedrock figure from published per-token rates against the same token counts, and label the
      column *estimated, not measured* (research 7, decision 2).

## Phase 5 — Tests · 45 min

- [ ] Metric unit tests against hand-computed values, including the degenerate cases that produce
      plausible-looking wrong numbers: no gold span retrieved, all retrieved, gold at rank 1,
      fewer results than k, duplicate uids in a ranking.
- [ ] A determinism test: the same config over the same items twice produces byte-identical
      rankings (research 6).
- [ ] An RRF test on hand-built rankings where the fused order is worked out by hand — RRF is
      four lines and every one of them is easy to get subtly wrong.
- [ ] A reranker contract test that runs without the model: a stub scorer, asserting the pipeline
      reorders by score and truncates to `top_n`. The real model is exercised once, marked `slow`,
      skipped in CI.
- [ ] Context-budget test: a 127K-character clause must be truncated to the budget, and the
      truncation must be *recorded*.

## Phase 6 — Write-up · 60 min

- [ ] **`results/day5/retrieval.md`** — the results table, the per-query-type winners, and the
      routing rule they imply, with every claim carrying its n.
- [ ] **ADR-020** — the seven configurations as a ladder plus ablations, and why a factorial
      reading was rejected; the constants left untuned and admitted (RRF `k=60`, rerank `top_n`).
- [ ] **ADR-021** — retrieval metrics on all seven configs, generation metrics on four; what an
      empty cell means; why abstention is two rates and not one.
- [ ] **ADR-022** — the determinism fix, and what it invalidated: any ranking metric measured
      before it. Worth its own ADR because "our benchmark's ranking was nondeterministic" is the
      kind of thing that silently survives into a published table.
- [ ] `retrieval/README.md`, root `README.md`, `initial-setup.md`; commit, push, CI green.

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
