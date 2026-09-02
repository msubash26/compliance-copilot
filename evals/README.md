# regops-evals

The golden set, and the tooling that keeps it honest.

Day 5 measures seven retrieval configurations against this. Whether that measurement can say
anything is a property of **this** artifact, not of the retriever — so the work here is mostly
about making sure the set is hard enough to separate them, and honest about what it is.

## Quickstart

```bash
uv run regops-evals select   --index index/regdocs.duckdb --out golden/v1/candidates.json
uv run regops-evals generate --candidates golden/v1/candidates.json --out golden/v1/golden.jsonl
uv run regops-evals verify   --index index/regdocs.duckdb --golden golden/v1/golden.jsonl \
                             --queue golden/v1/review_queue.md --report golden/v1/verification.json
uv run regops-evals gate     --index index/regdocs.duckdb --golden golden/v1/golden.jsonl \
                             --k 5 --out golden/v1/saturation.json
```

Run them one at a time. Ollama serialises against one loaded model, and the stages use three
different ones (`qwen3.5:9b` to generate, `qwen3.8` to verify, `nomic-embed-text` to search).
`verify` batches every embedding it needs *before* loading the judge for exactly this reason.

`select` is seeded (`--seed 0`), so `candidates.json` is reproducible and is not committed — it
is 970 KB of third-party clause text, and the same rule that keeps the corpus PDFs out of git
(ADR-012) keeps it out.

## The set

150 items, stratified in `schema.STRATIFICATION` **before** generation ran:

| type | n | grounded in |
|---|---|---|
| `factual_lookup` | 45 | one clause, split 15/15/15 across difficulty bands |
| `multi_hop` | 30 | 2 clauses, the second reached by a resolved cross-reference |
| `comparative` | 25 | 2–3 parallel entity-class notices, topically verified |
| `temporal` | 15 | amendment endnotes, `[Deleted by ...]` markers, commencement dates |
| `negative` | 35 | nothing — and that is the point |

Every item pins `doc_id`, `section_path` **and** a `span_sha256` of the gold text, carries a
`provenance` block naming the generator and parser commit, and a `verification` block saying
what was checked and by what.

## The number that matters

A naively generated set is **saturated**: 12 questions drawn from random clauses gave BM25 92%
recall@5 and dense 92%, at ceiling before any retrieval variant. Seven configurations would have
produced seven identical rows. The finished set, same retrievers:

| query type | bm25 hit@5 | dense hit@5 | bm25 full@5 | dense full@5 | n |
|---|---|---|---|---|---|
| `factual_lookup` | 0.733 | 0.733 | 0.733 | 0.733 | 45 |
| `multi_hop` | **0.800** | 0.600 | 0.167 | 0.167 | 30 |
| `comparative` | 0.560 | 0.560 | 0.160 | 0.160 | 25 |
| `temporal` | 0.400 | 0.333 | 0.400 | 0.333 | 15 |
| **overall** | **0.670** | **0.609** | **0.417** | **0.409** | 115 |

`hit@k` is any gold span retrieved; `full@k` requires all of them, which is the honest bar for a
hop — retrieving one half does not answer it. The per-type rows already diverge, and `full@5` at
0.16 on the multi-span types is the headroom Day 5 spends.

Difficulty is engineered from the corpus's own **entity-class near-duplication**, not from
deleting items a baseline answered — see ADR-019 for why that distinction is the whole design.

## What a person still has to check

Nothing in this directory has been reviewed by a human. Every item says so
(`human_reviewed: false`), and a test asserts it, so a review pass has to flip it deliberately.

- **28 of 150 items carry a failed check** — 26 verifier disagreements, 17 "not answerable from
  this span", 1 answerable without the corpus. They ship flagged, not deleted (ADR-017).
- `golden/v1/review_queue.md` sorts every item by ascending confidence with its gold span quoted
  inline, so the contested ones can be adjudicated without opening a PDF. **This is what the
  review time should be spent on**, not an even sweep over 150 items of which most are fine.
- `comparative` is the hardest type to verify (12 of 25 flagged): the questions require synthesis
  across spans, and a single-pass judge is strictest there. Worth a human eye before Day 5 draws
  conclusions from that row.

Confidence is a **ranking device, not a calibrated probability**. Calling it one would be a claim
the evidence does not support.

## Tests

```bash
uv run pytest evals/tests -q
```

No test calls a model. Every claim worth testing here — the schema rejects a malformed item, a
moved gold span reports `moved` rather than being silently rescored, the leakage regex fires on
"Notice 626" but not on "the Notice" — is decidable without a GPU, which is also what lets the
whole suite run in CI where there is none. The two tests that need the real 433 MB index skip
themselves when it is absent; the ones that check the shipped `golden.jsonl` always run, because
that file is committed.

The anti-rot test is the one to keep: Day 3 moved this corpus from 8,055 clauses to 11,171, so a
set pinning `section_path` is pinned to a *parser*. `regops-evals verify --index` re-binds every
span and reports resolved / moved / missing, and exits non-zero on either of the last two.

---

## Day 5: the sweep

The golden set above is the instrument; `regops-evals bench` is what reads it.

```bash
uv run regops-evals bench --index index/regdocs.duckdb --configs all \
                          --report results/day5/retrieval.md
uv run regops-evals generate-answers --configs ladder   # 4 x 150, ~20 min on the 3090
uv run regops-evals judge --answers results/day5/answers
```

Run them one at a time, and in that order. `bench` decomposes with `qwen3.5:9b` and embeds with
`nomic-embed-text`, so it takes **every** decomposition first and **then** every query vector —
interleaving them would swap a 17.7 GB model per query. `judge` loads `qwen3.8` only after
generation has finished with the GPU. Same rule as `verify`, for the same reason.

The retrievers come from [`regops-retrieval`](../retrieval/README.md), not from here: an eval
package must not own the thing it evaluates (ADR-020). `regops_evals.corpus` re-exports them, so
`gate`'s baseline and `bench`'s C1 row are the same code by construction — and a test asserts
that identity rather than trusting it.

### What is measured, and what is deliberately not

| | |
|---|---|
| Retrieval — `hit@5/@20`, `recall@5`, `full@5`, `nDCG@10`, MRR, p50/p95 | **all 7 configs × all 150 items**, no sampling |
| Generation — groundedness, citation validity, abstention | **4 ladder rungs × all 150 items** |
| The 3 ablations, generation columns | **not measured**, and the table says so |

Generation costs ~30× retrieval per query. Seven configurations of generation plus judging does
not fit the day; a half-sized set makes every per-type generation cell an anecdote (15 `temporal`
items means one item is 6.7 points). So the ladder is measured whole and the ablations carry an
empty cell with a reason. See ADR-021.

**Abstention is two rates.** False-answer on the 35 negatives (*dangerous*) and false-abstention
on the 115 grounded items (*useless*), never one blended accuracy — which would flatter a system
that abstains constantly and hide which failure it has.

**Every table is computed twice**, over all 150 and over the 122 unflagged items, and both are
published. A conclusion that flips between them belongs to the golden set's noise rather than to
the retriever. On the shipped run none flips: every configuration gains 2–7 MRR points on the
cleaner subset and the ordering is unchanged.

### The gate that runs first

C1 is BM25 and nothing else, so its row must reproduce `golden/v1/saturation.json` within half of
one item (0.005). It does — `hit@5` 0.670, `hit@20` 0.870, `full@5` 0.417, all to three places.
`bench` exits non-zero if it does not, because a sweep that has quietly redefined search produces
plausible numbers and nothing downstream can tell.

### Metrics

`regops_evals.metrics` is pure functions over `(ranked_uids, gold_uids)` — no index, no model —
tested against values worked out by hand, including the degenerate cases that produce
*plausible-looking* wrong numbers: nothing retrieved, everything retrieved, gold at rank 1, fewer
results than k, an empty gold set, and the same clause appearing twice in one ranking. That last
one is not hypothetical: the parent-child ablation retrieves chunks, so a ranking names a clause
more than once. A repeat neither helps nor is silently removed.

`recall@k` here is the *fraction* of gold spans retrieved; `hit@k` is Day 4's any-gold-span
metric, unchanged; `full@k` requires all of them. And nDCG is reported with a caveat stated once:
labels are binary and 45 of 115 items have a single gold span, so for those nDCG@10 is a monotone
function of the gold rank and carries the same information as MRR. It is independent evidence
only on `multi_hop` and `comparative`.
