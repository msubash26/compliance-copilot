# Golden set v1

150 evaluation items over the MAS corpus, built 2026-09-04 against the Day 3 index
(463 documents / 11,171 clauses / 22,090 chunks / 44,180 vectors).

**Versioned by directory.** `v2` can exist beside this without rewriting history, and Day 5's
results pin the version they were measured against.

## What this is

| file | what it holds |
|---|---|
| `golden.jsonl` | the 150 items, one per line, validated by `regops_evals.schema` |
| `review_queue.md` | every item by ascending confidence, gold span quoted inline |
| `verification.json` | what each check rejected, and the span-drift tally |
| `saturation.json` | BM25 and dense recall per query type — Day 5's baseline row |

`candidates.json` is not committed: it is a reproducible intermediate
(`regops-evals select --seed 0`) carrying 970 KB of third-party clause text.

## What was and was not reviewed

**No item in this file has been reviewed by a human.** Every one carries
`verification.human_reviewed: false`, and `evals/tests/test_golden_set.py` asserts it — so a
review pass has to flip it deliberately rather than by drift.

What *was* done, mechanically and on every item:

- the gold span resolves in the index and its `span_sha256` still matches — **150/150 resolved,
  0 moved, 0 missing**;
- the question does not name its own notice, instrument code or clause number — **0 leaks**
  (generation retries on a leak, and `verify` confirms it independently);
- the answer's vocabulary appears in the span it claims to come from;
- a question in a contested neighbourhood names its entity class.

And by **`qwen3.8`, a different model from the generator `qwen3.5:9b`**:

- can this be answered from this span, and does the recorded answer agree with it;
- can it be answered with no documents at all — **0 of 115** could, once the model's own claim to
  know was replaced by a comparison against the gold answer (ADR-017);
- for every negative, does anything in the corpus in fact answer it — **0 of 35** did.

## The flags

28 of 150 items failed at least one check and ship **flagged, not deleted**:

| check | items |
|---|---|
| verifier disagrees with the recorded answer | 26 |
| verifier says the span does not answer the question | 17 |
| answerable without the corpus | 1 |

By type: `comparative` 12/25, `factual_lookup` 8/45, `multi_hop` 7/30, `temporal` 1/15,
`negative` **0/35**.

Deleting them would have been easy and would have said less. *The verifier disagreed on 26 of
150* is a quality claim; a silently filtered file is not. Start at the top of
`review_queue.md` — it is ordered so that the ~28 contested items come first.

## Known limits

- **`temporal` means stated-time, not version-diff.** 0 documents in this corpus have more than
  one version row, so "what changed between versions" questions cannot be grounded and were not
  invented (ADR-018, and `regdocs-mcp` ADR-004).
- **`multi_hop` leans on one cross-reference family.** Guidelines citing their parent notice
  supply most of the resolvable hops; explicit notice-to-notice citations supply the rest.
- **Confidence is a ranking device**, not a calibrated probability.
- The set is pinned to the parser that produced the index. If `regops-ingest` changes,
  `regops-evals verify --index` will say so.
