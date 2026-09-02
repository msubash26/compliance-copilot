# Day 5 — the retrieval benchmark

Seven configurations over the Day 4 golden set (150 items, 115 of them grounded), every arm defined once in `regops-retrieval` and every cell traceable to per-item rows in [`raw/`](raw/).

Read the ladder downwards and the ablations against C4. The question this table exists
to answer is not *which configuration is best* — it is **whether different query types
want different retrievers**, because that is the difference between one number and a
routing rule.

## The gate that runs before any of this is believed

C1 is BM25 and nothing else, so its row must reproduce the baseline Day 4 published
in `golden/v1/saturation.json`. If it does not, the sweep has quietly redefined what
search means and every row below it is void.

| metric | Day 4 published | Day 5 C1 | delta |  |
|---|---|---|---|---|
| hit@5 | 0.670 | 0.670 | -0.0004 | OK |
| hit@20 | 0.870 | 0.870 | -0.0004 | OK |
| full@5 | 0.417 | 0.417 | +0.0004 | OK |

**PASS** at a tolerance of 0.005 (half of one item, which is 0.0087).

## The seven configurations

| config |  | arms | contextual | parent-child | rerank | decomp. | role |
|---|---|---|---|---|---|---|---|
| `C1_bm25` | BM25 only | bm25 | on | on | off | off | ladder |
| `C2_dense` | Dense only (+ctx) | dense | on | on | off | off | ladder |
| `C3_hybrid_rrf` | Hybrid RRF | hybrid | on | on | off | off | ladder |
| `C4_hybrid_rerank` | Hybrid RRF + cross-encoder | hybrid | on | on | on | off | ladder |
| `C5_no_context` | C4, contextual off | hybrid | **off** | on | on | off | ablation |
| `C6_child_units` | C4, parent-child off | hybrid | on | **off** | on | off | ablation |
| `C7_decompose` | C4 + query decomposition | hybrid | on | on | on | on | ablation |

A factorial reading of the prep plan's list would be 4 × 2 × 2 × 2 = 32 rows over 115
grounded items. The ladder-plus-ablations reading is seven, and it is the only one in
which an ablation means anything, because an ablation needs a fixed reference (ADR-020).

## Overall, all 150 items

Ranking metrics over the 115 grounded items; latency over all 150, negatives included — a production p95
does not get to exclude the questions whose answer is *not in the corpus*.

| config | hit@5 | recall@5 | full@5 | hit@20 | ndcg@10 | mrr | p50_s | p95_s | n |
|---|---|---|---|---|---|---|---|---|---|
| `C1_bm25` | 0.670 | 0.536 | 0.417 | 0.870 | 0.481 | 0.486 | 0.015 | 0.019 | 115 |
| `C2_dense` | 0.661 | 0.542 | 0.417 | 0.826 | 0.518 | 0.517 | 0.093 | 0.104 | 115 |
| `C3_hybrid_rrf` | 0.730 | 0.606 | 0.487 | 0.878 | 0.564 | 0.574 | 0.110 | 0.122 | 115 |
| `C4_hybrid_rerank` | 0.835 | 0.707 | 0.574 | 0.948 | 0.661 | 0.681 | 0.518 | 0.558 | 115 |
| `C5_no_context` | 0.835 | 0.697 | 0.556 | 0.922 | 0.650 | 0.672 | 0.521 | 0.560 | 115 |
| `C6_child_units` | 0.809 | 0.670 | 0.530 | 0.896 | 0.641 | 0.676 | 0.359 | 0.405 | 115 |
| `C7_decompose` | 0.661 | 0.571 | 0.478 | 0.896 | 0.533 | 0.532 | 1.663 | 2.212 | 115 |

`hit@k` is any gold span retrieved (Day 4's metric, unchanged). `recall@k` is the
*fraction* of gold spans retrieved, which is the only one of the three that separates
one hop of two from neither. `full@k` requires all of them.

**On nDCG.** Labels are binary and 45 of the 115 grounded items have exactly one gold
span; for those, nDCG@10 is a monotone function of the gold rank and carries the same
information as MRR. It is independent evidence only on `multi_hop` and `comparative`.
Said once here, and not narrated again per row.

### mrr by query type

Where in the list the first right answer lands. The routing table.

| config | factual_lookup | multi_hop | comparative | temporal | overall |
|---|---|---|---|---|---|
| `C1_bm25` | 0.542 | 0.589 | 0.369 | 0.307 | 0.486 |
| `C2_dense` | 0.613 | 0.516 | 0.451 | 0.345 | 0.517 |
| `C3_hybrid_rrf` | 0.708 | 0.603 | 0.457 | 0.314 | 0.574 |
| `C4_hybrid_rerank` | 0.756 | 0.748 | 0.494 | 0.631 | 0.681 |
| `C5_no_context` | 0.748 | 0.737 | 0.483 | 0.631 | 0.672 |
| `C6_child_units` | 0.759 | 0.773 | 0.498 | 0.531 | 0.676 |
| `C7_decompose` | 0.592 | 0.603 | 0.358 | 0.502 | 0.532 |
| **n** | 45 | 30 | 25 | 15 | 115 |

#### What each switch bought, in MRR

One switch moved per row. **Bold** clears one item's worth of movement on that type's
n; anything unbolded is arithmetic on a difference the set cannot resolve.

| switch | factual_lookup | multi_hop | comparative | temporal | overall |
|---|---|---|---|---|---|
| lexical → dense (+ctx) | **+0.071** | **-0.073** | **+0.082** | +0.038 | +0.032 |
| + RRF fusion | **+0.095** | **+0.086** | +0.006 | -0.032 | +0.057 |
| **+ cross-encoder rerank** | **+0.048** | **+0.145** | +0.037 | **+0.318** | +0.106 |
| − contextual embeddings | -0.008 | -0.011 | -0.011 | +0.000 | -0.009 |
| − parent-child (chunks) | +0.003 | +0.025 | +0.004 | **-0.100** | -0.004 |
| + query decomposition | **-0.164** | **-0.145** | **-0.137** | **-0.130** | -0.148 |
| **n** | 45 | 30 | 25 | 15 |  |

- lexical → dense (+ctx): **helps and hurts, depending on the type** — `factual_lookup` +0.071, `comparative` +0.082 against `multi_hop` -0.073.
- + RRF fusion: real on 2 of 4 types, largest on `factual_lookup` (+0.095); below the noise floor on the rest.
- + cross-encoder rerank: real on 3 of 4 types, largest on `temporal` (+0.318); below the noise floor on the rest.
- − contextual embeddings: **no per-type movement clears one item's worth.**
- − parent-child (chunks): real on 1 of 4 types, largest on `temporal` (-0.100); below the noise floor on the rest.
- + query decomposition: real on 4 of 4 types, largest on `factual_lookup` (-0.164); uniform in sign.

That spread is the finding. A single "best configuration" number would have averaged
it away, and averaging it away is what makes a benchmark unable to justify a routing
rule.

### hit@5 by query type

Did anything right make the top 5 at all.

| config | factual_lookup | multi_hop | comparative | temporal | overall |
|---|---|---|---|---|---|
| `C1_bm25` | 0.733 | 0.800 | 0.560 | 0.400 | 0.670 |
| `C2_dense` | 0.800 | 0.733 | 0.520 | 0.333 | 0.661 |
| `C3_hybrid_rrf` | 0.800 | 0.833 | 0.640 | 0.467 | 0.730 |
| `C4_hybrid_rerank` | 0.889 | 0.867 | 0.760 | 0.733 | 0.835 |
| `C5_no_context` | 0.867 | 0.900 | 0.760 | 0.733 | 0.835 |
| `C6_child_units` | 0.867 | 0.867 | 0.760 | 0.600 | 0.809 |
| `C7_decompose` | 0.711 | 0.700 | 0.560 | 0.600 | 0.661 |
| **n** | 45 | 30 | 25 | 15 | 115 |

### full@5 by query type

Did *everything* right make the top 5 — the honest bar for a hop.

| config | factual_lookup | multi_hop | comparative | temporal | overall |
|---|---|---|---|---|---|
| `C1_bm25` | 0.733 | 0.167 | 0.160 | 0.400 | 0.417 |
| `C2_dense` | 0.800 | 0.100 | 0.160 | 0.333 | 0.417 |
| `C3_hybrid_rrf` | 0.800 | 0.200 | 0.280 | 0.467 | 0.487 |
| `C4_hybrid_rerank` | 0.889 | 0.233 | 0.320 | 0.733 | 0.574 |
| `C5_no_context` | 0.867 | 0.233 | 0.280 | 0.733 | 0.556 |
| `C6_child_units` | 0.867 | 0.200 | 0.280 | 0.600 | 0.530 |
| `C7_decompose` | 0.711 | 0.233 | 0.280 | 0.600 | 0.478 |
| **n** | 45 | 30 | 25 | 15 | 115 |

### ndcg@10 by query type

Rank quality over the top 10; informative on the multi-span types.

| config | factual_lookup | multi_hop | comparative | temporal | overall |
|---|---|---|---|---|---|
| `C1_bm25` | 0.611 | 0.469 | 0.342 | 0.343 | 0.481 |
| `C2_dense` | 0.658 | 0.430 | 0.453 | 0.378 | 0.518 |
| `C3_hybrid_rrf` | 0.739 | 0.507 | 0.431 | 0.374 | 0.564 |
| `C4_hybrid_rerank` | 0.788 | 0.579 | 0.527 | 0.665 | 0.661 |
| `C5_no_context` | 0.777 | 0.574 | 0.503 | 0.665 | 0.650 |
| `C6_child_units` | 0.785 | 0.579 | 0.509 | 0.557 | 0.641 |
| `C7_decompose` | 0.630 | 0.485 | 0.395 | 0.566 | 0.533 |
| **n** | 45 | 30 | 25 | 15 | 115 |

## Sensitivity: the same sweep over the 121 unflagged items

29 of the 150 items are machine-verified but not human-reviewed, and `comparative`
is the least-verified type. A conclusion that survives only on the full set belongs to
the golden set's noise rather than to the retriever, so both are published.

| config | mrr (150) | mrr (121) | Δ | hit@5 (150) | hit@5 (121) | Δ |
|---|---|---|---|---|---|---|
| `C1_bm25` | 0.486 | 0.526 | +0.040 | 0.670 | 0.690 | +0.020 |
| `C2_dense` | 0.517 | 0.551 | +0.033 | 0.661 | 0.701 | +0.040 |
| `C3_hybrid_rrf` | 0.574 | 0.612 | +0.038 | 0.730 | 0.747 | +0.017 |
| `C4_hybrid_rerank` | 0.681 | 0.751 | +0.070 | 0.835 | 0.874 | +0.039 |
| `C5_no_context` | 0.672 | 0.737 | +0.065 | 0.835 | 0.862 | +0.027 |
| `C6_child_units` | 0.676 | 0.703 | +0.027 | 0.809 | 0.816 | +0.007 |
| `C7_decompose` | 0.532 | 0.555 | +0.022 | 0.661 | 0.690 | +0.029 |

Every configuration gains on the cleaner subset, which is what a flagged item being a
harder item predicts. What matters is whether any **switch changes its verdict** on a
query type — helps, hurts, or too small to call — between the two runs:

- `factual_lookup` — − parent-child (chunks): **flat** on 150, **hurts** on 121
- `comparative` — − parent-child (chunks): **flat** on 150, **hurts** on 121

Those rows rest on the golden set as much as on the retriever, and are not narrated
as retrieval findings above.

## What assembly costs, and how often the budget bit

The parent-child axis is not a recall axis — research measured it changing the top-5 on
9 of 40 queries by a mean of 0.25 slots. Where it bites is context size, and a MAS
clause can run to 127,564 characters, so the hard budget in `assemble_context` is what
keeps a tail case out of the groundedness column.

| config | unit | mean context chars | queries truncated | n |
|---|---|---|---|---|
| `C1_bm25` | clause | 11,887 | 47 | 150 |
| `C2_dense` | clause | 9,076 | 46 | 150 |
| `C3_hybrid_rrf` | clause | 11,517 | 57 | 150 |
| `C4_hybrid_rerank` | clause | 10,098 | 42 | 150 |
| `C5_no_context` | clause | 10,491 | 46 | 150 |
| `C6_child_units` | chunk | 4,264 | 0 | 150 |
| `C7_decompose` | clause | 12,834 | 62 | 150 |

## Groundedness and abstention

Generation is the expensive half of this day: an answer over five assembled clauses on
`qwen3.5:9b` costs seconds where a retrieval query costs milliseconds, and judging is a
second pass with a second model on top. So the **four ladder rungs** are measured over
all 150 items and the three ablations are **not measured** here — an empty cell that
says why beats a cell filled from a subset and quoted as if it were the set (ADR-021).

Abstention is reported as **two rates, never one**. A single accuracy number flatters a
system that abstains constantly, and the two failures are not the same failure: answering
a question the corpus cannot answer is *dangerous*, and refusing one it can is *useless*.

| config | groundedness | answered n | citations valid | false-answer (35 neg) | false-abstention (115) | useful-answer rate | p50 gen |
|---|---|---|---|---|---|---|---|
| `C1_bm25` | 0.821 | 78 | 0.833 | 0.057 | 0.322 | **0.556** | 1.84s |
| `C2_dense` | 0.880 | 75 | 0.867 | 0.057 | 0.348 | **0.574** | 1.61s |
| `C3_hybrid_rrf` | 0.798 | 84 | 0.809 | 0.086 | 0.270 | **0.583** | 1.84s |
| `C4_hybrid_rerank` | 0.870 | 92 | 0.891 | 0.029 | 0.191 | **0.696** | 1.78s |
| `C5_no_context` | — | — | — | — | — | — | not measured (ablation) |
| `C6_child_units` | — | — | — | — | — | — | not measured (ablation) |
| `C7_decompose` | — | — | — | — | — | — | not measured (ablation) |

**Read the useful-answer column, not the groundedness one.** Groundedness is a rate over answers that made a claim, so abstaining more raises it. The table shows exactly that: `C2_dense` has the *highest* groundedness (0.880) on the *fewest* answers (75), because refusing the hard ones leaves an easier set to be grounded on. **Useful-answer rate** — grounded answers as a fraction of all 115 grounded items — does not move when a system trades coverage for caution, and on it `C4_hybrid_rerank` wins at 0.696.

Judged by `qwen3.8:latest`, which is not the model that wrote the answers — the Day 4
rule, for the Day 4 reason. Groundedness is the rate over answers that *made a claim*: an abstention has no claims to support, so counting it either way would be scoring silence.

**The one false answer is the golden set's, not the system's.** `C4_hybrid_rerank`'s single false answer on the 35 negatives is `gs-0118`, which asks what disclosure formats or reporting templates MAS requires. The system answered that Notice 653 prescribes the NSFR Disclosure Template in Table 1 of Annex 1, published semi-annually in the Pillar 3 report — and every one of those phrases is in the retrieved context. **The answer is right and the item is wrong.** Day 4's verifier had that clause at rank 3 and still passed the item at confidence 1.0, because `negative_excerpts` showed the judge the first 700 characters of a 12,689-character clause and the requirement begins at character 3,697 (ADR-024). So this column reads **0.029 as measured, 0.000 excluding `gs-0118`**.

The item now carries that finding itself: re-verified at a 6,000-character window, `gs-0118` fails `negative_is_answerable` and ships **flagged** at confidence 0.4. The flag came from the checker, not from a hand edit. It moved the split by exactly one item and changed no number on this page, because the flagged/unflagged sensitivity subsets are over the grounded items and this one is a negative.

### How much of the false-abstention rate belongs to the golden set

28 of the 115 grounded items are flagged — machine-verified, not human-reviewed. If the system refused those at the same rate as
the rest, the flag would be telling us nothing about answerability. It does not:

| config | false-abstention (all) | flagged items | unflagged items | ratio |
|---|---|---|---|---|
| `C1_bm25` | 0.322 | 0.464 | 0.276 | 1.7× |
| `C2_dense` | 0.348 | 0.464 | 0.310 | 1.5× |
| `C3_hybrid_rrf` | 0.270 | 0.500 | 0.195 | 2.6× |
| `C4_hybrid_rerank` | 0.191 | 0.393 | 0.126 | 3.1× |

Read across: **every configuration refuses flagged items at several times the rate it
refuses unflagged ones**, and the gap widens as retrieval improves. Some of these are
genuinely unanswerable as written — `gs-0005` asks *"when does this notice become
effective"* with no referent for *this notice*, and abstaining is the correct answer to
it. So a meaningful share of the false-abstention column is the instrument, not the
system, and the unflagged column is the fairer number to quote. Neither is hidden.

### Cost per query

The local column is **measured**: GPU seconds on the 3090 and token counts off the
Ollama response. The Bedrock column is **estimated from published per-token rates**
against those same token counts — there are no AWS credentials on this box and
ADR-005 positions hosted APIs as a parity baseline, not a dependency. The label is in
the header rather than a footnote because that is where it will be read.

| config | GPU s/query (measured) | prompt tok/query | completion tok/query | Bedrock $/1k queries (estimated) |
|---|---|---|---|---|
| `C1_bm25` | 1.79 | 2,779 | 87 | $3.21 |
| `C2_dense` | 1.61 | 2,166 | 86 | $2.60 |
| `C3_hybrid_rrf` | 1.77 | 2,677 | 87 | $3.11 |
| `C4_hybrid_rerank` | 1.70 | 2,386 | 89 | $2.83 |

Rates used: Claude Haiku 4.5 (Bedrock on-demand), $1.00/M input and $5.00/M output, applied to locally measured token counts. No AWS call was made.

## The rule this table supports

1. **Rerank everything.** It is the largest single lever in the sweep (+0.106 MRR overall) and it does not hurt any query type. It costs 408ms, which is affordable next to a generator that takes seconds.
2. **But budget it against the query class, not the average.** The same reranker is worth +0.318 MRR on `temporal` (n=15) and +0.037 on `comparative` (n=25). `temporal` questions resolve against amendment endnotes whose wording is near-identical across forty documents, which is precisely the disambiguation a cross-encoder does; a lookup whose clause already ranks first has nothing left to reorder.
3. **Prefer the lexical arm on cross-reference questions.** BM25 beats dense by +0.073 MRR on `multi_hop` (n=30) and loses by -0.071 on `factual_lookup` (n=45). A cross-reference is a citation — a literal string — and that is lexical territory; a paraphrased lookup is not.
4. **Do not decompose.** It loses on all four types, by -0.148 MRR overall, at 3.2× the p50 latency. It was run on all 150 items rather than only where it was expected to help, which is why this is a result rather than an assumption.
   *And the mechanism is visible in the rows.* Over the 100 items both C4 and C7 retrieve at all, the first gold span is **demoted on 36, unchanged on 51 and promoted on 13**, with a further 9 falling out of the top 20 entirely. Decomposition is not finding the wrong documents; it is finding the right ones and pushing them down — which is what RRF over sub-queries does, because it weights every sub-query equally and the original question ends up with one vote in three.
5. **Contextual embeddings and the cross-encoder are competing for the same ranking error.** On the dense arm alone, `+ctx` is worth several MRR points (ADR-015). With the reranker on, removing it costs only +0.009 MRR overall and +0.000 on `temporal` — no per-type movement clears one item's worth. Keeping both is defensible; claiming both are earning their keep is not.
6. **Assemble as chunks unless the whole clause is needed.** The parent-child switch costs -0.004 MRR overall — noise — while cutting mean context from 10,098 to 4,264 characters and truncated queries from 42 to 0. It belongs in the cost column, which is where research predicted it would land. The one exception is `temporal` (-0.100, n=15, so 1.5 items) — an amendment endnote is short and self-contained, and splitting it loses the sentence that dates it.

   *Caveat, and it is this switch's alone.* On the 121 unflagged items the parent-child switch stops being flat and starts hurting on `factual_lookup`, `comparative`. That verdict change is the sensitivity run doing its job: this is the one recommendation above that rests on which 29 items are flagged, so treat chunk assembly as a cost optimisation to *measure* per deployment rather than a free win.

**What would change this.** `temporal` and `comparative` carry the two thinnest cells, and every claim above that rests on them is one or two items from moving. The reranking result does not: it holds on the 121-item unflagged subset as well as on the full set.

## Cost of the measurement itself

| config | wall time, 150 queries |
|---|---|
| `C1_bm25` | 4s |
| `C2_dense` | 13s |
| `C3_hybrid_rrf` | 15s |
| `C4_hybrid_rerank` | 76s |
| `C5_no_context` | 76s |
| `C6_child_units` | 53s |
| `C7_decompose` | 266s |
| **total** | 502s |

This is why the retrieval sweep runs complete on all seven configurations and nothing is sampled. Measured here, the cheapest generation config is 1.61s per query against 0.015s for the cheapest retrieval config — 104× — which is why generation runs on four configurations and retrieval on seven (ADR-021).
